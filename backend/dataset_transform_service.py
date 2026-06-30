"""
数据集数据转换服务

把原始同步表（如飞书同步落库的 JSONB 表）通过 SQL 转换成业务视图/表，
支持手动执行、飞书同步后自动触发，并记录执行历史。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2 import sql

from bookshelf_repository import BookshelfRepository
from system_log_store import log_event


class TransformError(Exception):
    """转换执行异常"""


VALID_TARGET_TYPES = {"view", "table", "materialized_view"}


class DatasetTransformService:
    """数据集转换任务服务"""

    def __init__(self):
        self._repo = BookshelfRepository()

    def _connect(self):
        return self._repo._connect()

    @staticmethod
    def _normalize_identifier(value: str) -> str:
        """把用户输入的表名/视图名规整成安全的 PostgreSQL 标识符。"""
        raw = str(value or "").strip()
        if not raw:
            raise TransformError("目标名称不能为空")
        # 只保留字母、数字、下划线；其余替换为下划线
        normalized = re.sub(r"[^0-9A-Za-z_\u4e00-\u9fa5]", "_", raw)
        normalized = re.sub(r"_+", "_", normalized).strip("_").lower()
        if not normalized:
            raise TransformError("目标名称无效")
        if normalized[0].isdigit():
            normalized = f"t_{normalized}"
        return normalized[:63]

    @staticmethod
    def _validate_transform_sql(sql_text: str) -> str:
        """校验 transform_sql 只允许只读 SELECT 片段。"""
        text = str(sql_text or "").strip()
        if not text:
            raise TransformError("转换 SQL 不能为空")
        if ";" in text:
            raise TransformError("转换 SQL 不允许包含分号，只允许单条 SELECT 语句")
        # 去除注释后检查开头
        normalized = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
        normalized = re.sub(r"--.*?$", " ", normalized, flags=re.M)
        normalized = normalized.strip().lower()
        if not (normalized.startswith("select") or normalized.startswith("with")):
            raise TransformError("转换 SQL 必须以 SELECT 或 WITH 开头")
        return text

    def _build_ddl(self, target_type: str, target_name: str, transform_sql: str) -> List[str]:
        """根据目标类型生成完整 DDL 语句列表。"""
        target_type = str(target_type or "view").strip().lower()
        if target_type not in VALID_TARGET_TYPES:
            raise TransformError(f"不支持的目标类型: {target_type}")

        normalized_target = self._normalize_identifier(target_name)
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                target_escaped = sql.Identifier(normalized_target).as_string(cur)
        finally:
            conn.close()

        select_body = transform_sql
        if target_type == "view":
            return [
                f"DROP VIEW IF EXISTS {target_escaped} CASCADE;",
                f"CREATE OR REPLACE VIEW {target_escaped} AS\n{select_body}",
            ]
        if target_type == "table":
            return [
                f"DROP TABLE IF EXISTS {target_escaped} CASCADE;",
                f"CREATE TABLE {target_escaped} AS\n{select_body}",
            ]
        # materialized_view
        return [
            f"DROP MATERIALIZED VIEW IF EXISTS {target_escaped} CASCADE;",
            f"CREATE MATERIALIZED VIEW {target_escaped} AS\n{select_body};",
            f"REFRESH MATERIALIZED VIEW {target_escaped}",
        ]

    def _execute_statements(self, statements: List[str]) -> None:
        """在默认 PG 数据源执行一组 DDL。"""
        conn = self._connect()
        try:
            conn.autocommit = True
            with conn.cursor() as cur:
                for stmt in statements:
                    cur.execute(stmt)
        finally:
            conn.close()

    def _verify_target(self, target_name: str) -> None:
        """验证目标视图/表可查询。"""
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                target = sql.Identifier(self._normalize_identifier(target_name))
                cur.execute(
                    sql.SQL("SELECT 1 FROM {target} LIMIT 1").format(target=target)
                )
                cur.fetchone()
        finally:
            conn.close()

    def get_transforms(
        self,
        dataset_id: Optional[int] = None,
        source_table: Optional[str] = None,
        only_active: bool = False,
    ) -> List[Dict[str, Any]]:
        """查询转换任务列表。"""
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                conditions = ["1=1"]
                params: List[Any] = []
                if dataset_id is not None:
                    conditions.append("dataset_id = %s")
                    params.append(dataset_id)
                if source_table is not None:
                    conditions.append("source_table = %s")
                    params.append(source_table)
                if only_active:
                    conditions.append("is_active = TRUE")
                where_clause = " AND ".join(conditions)
                cur.execute(
                    f"""
                    SELECT id, dataset_id, name, source_table, target_type, target_name,
                           transform_sql, is_active, auto_run_on_sync, sync_dependency,
                           last_run_at, last_run_status, last_run_message,
                           created_at, updated_at
                    FROM bs_dataset_transforms
                    WHERE {where_clause}
                    ORDER BY created_at DESC
                    """,
                    params,
                )
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        finally:
            conn.close()

    def get_transform(self, transform_id: int) -> Optional[Dict[str, Any]]:
        """单条查询转换任务。"""
        transforms = self.get_transforms()
        # 简单实现：先按 id 过滤（有索引不会慢）
        # 为减少代码量，复用 get_transforms 后过滤
        for item in transforms:
            if item["id"] == transform_id:
                return item
        return None

    def create_transform(self, data: Dict[str, Any]) -> int:
        """创建转换任务，返回新任务 ID。"""
        dataset_id = int(data.get("dataset_id") or 0)
        if not dataset_id:
            raise TransformError("dataset_id 不能为空")
        name = str(data.get("name") or "").strip()
        if not name:
            raise TransformError("任务名称不能为空")
        source_table = str(data.get("source_table") or "").strip()
        if not source_table:
            raise TransformError("源表不能为空")
        target_type = str(data.get("target_type") or "view").strip().lower()
        if target_type not in VALID_TARGET_TYPES:
            raise TransformError(f"不支持的目标类型: {target_type}")
        target_name = str(data.get("target_name") or "").strip()
        if not target_name:
            raise TransformError("目标名称不能为空")
        # 规范化目标名
        self._normalize_identifier(target_name)
        transform_sql = self._validate_transform_sql(data.get("transform_sql"))

        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO bs_dataset_transforms
                        (dataset_id, name, source_table, target_type, target_name,
                         transform_sql, is_active, auto_run_on_sync, sync_dependency,
                         updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id
                    """,
                    (
                        dataset_id,
                        name,
                        source_table,
                        target_type,
                        target_name,
                        transform_sql,
                        bool(data.get("is_active", True)),
                        bool(data.get("auto_run_on_sync", False)),
                        str(data.get("sync_dependency") or ""),
                    ),
                )
                new_id = int(cur.fetchone()[0])
                conn.commit()
                return new_id
        finally:
            conn.close()

    def update_transform(self, transform_id: int, data: Dict[str, Any]) -> bool:
        """更新转换任务。"""
        transform_sql = data.get("transform_sql")
        if transform_sql is not None:
            transform_sql = self._validate_transform_sql(transform_sql)
        target_name = data.get("target_name")
        if target_name:
            self._normalize_identifier(target_name)
        target_type = data.get("target_type")
        if target_type is not None:
            target_type = str(target_type).strip().lower()
            if target_type not in VALID_TARGET_TYPES:
                raise TransformError(f"不支持的目标类型: {target_type}")

        conn = self._connect()
        try:
            with conn.cursor() as cur:
                fields = []
                params: List[Any] = []
                if "name" in data:
                    fields.append("name = %s")
                    params.append(str(data["name"]).strip())
                if "source_table" in data:
                    fields.append("source_table = %s")
                    params.append(str(data["source_table"]).strip())
                if target_type is not None:
                    fields.append("target_type = %s")
                    params.append(target_type)
                if target_name is not None:
                    fields.append("target_name = %s")
                    params.append(str(target_name).strip())
                if transform_sql is not None:
                    fields.append("transform_sql = %s")
                    params.append(transform_sql)
                if "is_active" in data:
                    fields.append("is_active = %s")
                    params.append(bool(data["is_active"]))
                if "auto_run_on_sync" in data:
                    fields.append("auto_run_on_sync = %s")
                    params.append(bool(data["auto_run_on_sync"]))
                if "sync_dependency" in data:
                    fields.append("sync_dependency = %s")
                    params.append(str(data.get("sync_dependency") or ""))
                if not fields:
                    return True
                fields.append("updated_at = NOW()")
                params.append(transform_id)
                cur.execute(
                    f"UPDATE bs_dataset_transforms SET {', '.join(fields)} WHERE id = %s",
                    params,
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()

    def delete_transform(self, transform_id: int) -> bool:
        """删除转换任务，并级联删除生成的目标对象（view/table/materialized_view）。"""
        transform = self.get_transform(transform_id)
        if transform:
            target_type = str(transform.get("target_type") or "view").strip().lower()
            target_name = str(transform.get("target_name") or "").strip()
            if target_name and target_type in VALID_TARGET_TYPES:
                try:
                    normalized = self._normalize_identifier(target_name)
                    if target_type == "view":
                        drop_sql = f"DROP VIEW IF EXISTS {normalized} CASCADE;"
                    elif target_type == "table":
                        drop_sql = f"DROP TABLE IF EXISTS {normalized} CASCADE;"
                    else:
                        drop_sql = f"DROP MATERIALIZED VIEW IF EXISTS {normalized} CASCADE;"
                    self._execute_statements([drop_sql])
                except Exception as exc:
                    # 清理目标对象失败不影响删除任务记录，只记录日志
                    log_event(
                        category="dataset_transform",
                        event_type="transform_cleanup_failed",
                        level="warning",
                        title="删除转换任务时清理目标对象失败",
                        details={"transform_id": transform_id, "target_name": target_name, "error": str(exc)},
                    )

        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM bs_dataset_transforms WHERE id = %s", (transform_id,))
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()

    def execute_transform(self, transform_id: int, triggered_by: str = "manual") -> Dict[str, Any]:
        """执行单个转换任务。"""
        transform = self.get_transform(transform_id)
        if not transform:
            raise TransformError("转换任务不存在")
        if not transform.get("is_active"):
            raise TransformError("转换任务已停用")

        target_name = transform["target_name"]
        target_type = transform["target_type"]
        source_table = transform["source_table"]
        transform_sql = str(transform["transform_sql"] or "").replace("{{source_table}}", source_table)

        started_at = datetime.now(timezone.utc)
        result = {"success": False, "message": "", "executed_at": started_at.isoformat()}

        try:
            statements = self._build_ddl(target_type, target_name, transform_sql)
            self._execute_statements(statements)
            self._verify_target(target_name)
            result["success"] = True
            result["message"] = f"{target_type} {target_name} 创建/刷新成功"
        except Exception as exc:
            result["message"] = f"转换失败: {exc}"
            self._update_run_status(transform_id, False, result["message"])
            self._log_run(transform, triggered_by, False, result["message"])
            return result

        self._update_run_status(transform_id, True, result["message"])
        self._log_run(transform, triggered_by, True, result["message"])
        return result

    def test_transform_sql(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """测试转换 SQL（不保存，创建临时目标后删除）。"""
        target_type = str(data.get("target_type") or "view").strip().lower()
        target_name = str(data.get("target_name") or "").strip()
        source_table = str(data.get("source_table") or "").strip()
        transform_sql = self._validate_transform_sql(data.get("transform_sql"))
        if source_table:
            transform_sql = transform_sql.replace("{{source_table}}", source_table)
        self._normalize_identifier(target_name)

        temp_name = f"_test_{self._normalize_identifier(target_name)}_{int(datetime.now().timestamp())}"
        try:
            statements = self._build_ddl(target_type, temp_name, transform_sql)
            self._execute_statements(statements)
            self._verify_target(temp_name)
            return {"success": True, "message": f"测试成功，临时对象 {temp_name} 已创建"}
        except Exception as exc:
            return {"success": False, "message": f"测试失败: {exc}"}
        finally:
            try:
                self._execute_statements([f"DROP VIEW IF EXISTS {temp_name} CASCADE;"])
                self._execute_statements([f"DROP TABLE IF EXISTS {temp_name} CASCADE;"])
                self._execute_statements([f"DROP MATERIALIZED VIEW IF EXISTS {temp_name} CASCADE;"])
            except Exception:
                pass

    def run_transforms_by_source_table(self, source_table: str, triggered_by: str = "sync") -> List[Dict[str, Any]]:
        """当源表数据更新后，触发所有关联且启用的转换任务。"""
        transforms = self.get_transforms(source_table=source_table, only_active=True)
        results = []
        for transform in transforms:
            if not transform.get("auto_run_on_sync"):
                continue
            result = self.execute_transform(transform["id"], triggered_by=triggered_by)
            results.append({"transform_id": transform["id"], **result})
        return results

    def _update_run_status(self, transform_id: int, success: bool, message: str) -> None:
        """更新任务最后执行状态。"""
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE bs_dataset_transforms
                    SET last_run_at = NOW(),
                        last_run_status = %s,
                        last_run_message = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    ("success" if success else "failed", str(message)[:2000], transform_id),
                )
                conn.commit()
        finally:
            conn.close()

    def _log_run(
        self,
        transform: Dict[str, Any],
        triggered_by: str,
        success: bool,
        message: str,
    ) -> None:
        """写系统事件日志。"""
        try:
            log_event(
                category="dataset_transform",
                event_type="transform_executed",
                level="info" if success else "error",
                title=f"数据集转换任务 {'成功' if success else '失败'}: {transform.get('name')}",
                details={
                    "transform_id": transform.get("id"),
                    "dataset_id": transform.get("dataset_id"),
                    "source_table": transform.get("source_table"),
                    "target_name": transform.get("target_name"),
                    "target_type": transform.get("target_type"),
                    "triggered_by": triggered_by,
                    "message": message,
                },
            )
        except Exception:
            pass


# 全局服务实例
transform_service = DatasetTransformService()

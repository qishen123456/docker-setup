"""
飞书多维表格数据同步服务
"""

import requests
import json
import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union
import threading
import schedule

from feishu_sync_manager import (
    get_feishu_configs, 
    update_sync_status, 
    read_feishu_config
)
from feishu_sync_logger import write_log
from config_manager import decode_secret, get_datasources

FEISHU_FIELD_TYPE_LABELS = {
    1: "文本",
    2: "数字",
    3: "单选",
    4: "多选",
    5: "日期",
    7: "复选框",
    11: "人员",
    13: "电话",
    15: "超链接",
    17: "附件",
    18: "单向关联",
    19: "公式",
    20: "双向关联",
    21: "地理位置",
    22: "群组",
    23: "创建时间",
    24: "最后更新时间",
    1001: "创建人",
    1002: "修改人",
    1003: "自动编号",
}

FEISHU_PERSON_FIELD_TYPE_CODES = {11, 1001, 1002}
FEISHU_PERSON_FIELD_NAME_HINTS = (
    "业务代表",
    "任务维护人",
    "创建人",
    "总任务承接人",
    "维护人",
    "承接人",
    "负责人",
    "责任人",
    "跟进人",
    "人员",
)

class FeishuSyncService:
    """飞书同步服务"""
    
    def __init__(self):
        self.sync_threads = {}
        self.running = False

    def normalize_table_name(self, value: str) -> str:
        """把目标表名规整成安全的 PostgreSQL 标识符。"""
        raw = str(value or "").strip()
        if not raw:
            return "feishu_sync_table"
        normalized = re.sub(r"[^0-9A-Za-z_]", "_", raw)
        normalized = re.sub(r"_+", "_", normalized).strip("_").lower()
        if not normalized:
            normalized = "feishu_sync_table"
        if normalized[0].isdigit():
            normalized = f"t_{normalized}"
        return normalized[:60]

    def _index_name(self, table_name: str, suffix: str) -> str:
        base = self.normalize_table_name(f"idx_{table_name}_{suffix}")
        return base[:60]

    def _extract_record_fields(self, records: List[Dict]) -> List[str]:
        fields = set()
        for record in records or []:
            record_fields = record.get("fields") or {}
            if isinstance(record_fields, dict):
                fields.update(str(key) for key in record_fields.keys() if str(key).strip())
        return sorted(fields)

    def _field_type_label(self, value) -> str:
        try:
            code = int(value)
        except Exception:
            return str(value or "未知")
        return FEISHU_FIELD_TYPE_LABELS.get(code, f"类型{code}")

    def _normalize_field_item(self, item: Dict, index: int) -> Dict:
        field_type = item.get("type")
        return {
            "sequence": index,
            "field_id": item.get("field_id") or item.get("id") or "",
            "name": item.get("field_name") or item.get("name") or "",
            "type_code": field_type,
            "type": self._field_type_label(field_type),
            "is_primary": bool(item.get("is_primary")),
        }

    def _is_person_field_name(self, field_name: str) -> bool:
        name = str(field_name or "").strip()
        if not name:
            return False
        return any(token in name for token in FEISHU_PERSON_FIELD_NAME_HINTS)

    def _person_field_names(self, field_items: Optional[List[Dict]]) -> set:
        names = set()
        for item in field_items or []:
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            try:
                type_code = int(item.get("type_code"))
            except Exception:
                type_code = None
            if type_code in FEISHU_PERSON_FIELD_TYPE_CODES or self._is_person_field_name(name):
                names.add(name)
        return names

    def _extract_person_name(self, item) -> str:
        if item is None:
            return ""
        if isinstance(item, str):
            text = item.strip()
            if not text:
                return ""
            if text[0] in "[{":
                try:
                    return self._normalize_person_value(json.loads(text))
                except Exception:
                    return text
            return text
        if isinstance(item, dict):
            for key in ("name", "zh_name", "display_name", "en_name", "nickname", "text"):
                value = item.get(key)
                if value is not None and str(value).strip():
                    return str(value).strip()
            return ""
        return str(item).strip()

    def _normalize_person_value(self, value) -> str:
        """把飞书人员字段统一转成纯人名文本。"""
        if value is None or value == "":
            return ""
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return ""
            if text[0] in "[{":
                try:
                    return self._normalize_person_value(json.loads(text))
                except Exception:
                    return text
            return text
        if isinstance(value, list):
            names = []
            for item in value:
                name = self._extract_person_name(item)
                if name:
                    names.append(name)
            return "、".join(names)
        if isinstance(value, dict):
            return self._extract_person_name(value)
        return str(value).strip()

    def _normalize_record_fields_for_storage(self, fields: Dict, person_field_names: set) -> Dict:
        if not isinstance(fields, dict):
            return {}
        normalized = {}
        for key, value in fields.items():
            field_name = str(key)
            if field_name in person_field_names or self._is_person_field_name(field_name):
                normalized[field_name] = self._normalize_person_value(value)
            else:
                normalized[field_name] = value
        return normalized

    def _normalize_records_for_storage(self, records: List[Dict], field_items: Optional[List[Dict]] = None) -> List[Dict]:
        person_field_names = self._person_field_names(field_items)
        normalized_records = []
        for record in records or []:
            if not isinstance(record, dict):
                continue
            normalized_record = dict(record)
            normalized_record["fields"] = self._normalize_record_fields_for_storage(
                record.get("fields") or {},
                person_field_names,
            )
            normalized_records.append(normalized_record)
        return normalized_records

    def _format_feishu_api_error(self, data: Dict) -> str:
        code = data.get("code", "")
        msg = data.get("msg") or data.get("message") or "未知错误"
        extra = ""
        if msg == "RolePermNotAllow":
            extra = "。当前飞书应用没有这个多维表格/视图的访问权限，请把应用或机器人添加为该 Base 的协作者，并确认应用已开通 bitable 读取权限"
        elif msg in {"WrongAppToken", "App token not found"}:
            extra = "。请检查 Base ID 是否正确，或应用是否有访问该多维表格的权限"
        elif msg in {"TableIdNotFound", "table not found"}:
            extra = "。请检查 Table ID 是否正确，或该表是否已被删除/无权限访问"
        elif msg in {"ViewIdNotFound", "view not found"}:
            extra = "。请检查 View ID 是否正确，必要时先清空 View ID 用全表视图检测"
        return f"飞书接口返回错误 code={code}, msg={msg}{extra}"
        
    def get_access_token(self, app_id: str, app_secret: str, config_id: int) -> Optional[str]:
        """获取飞书访问令牌"""
        try:
            write_log(config_id, 'INFO', f'开始获取飞书访问令牌, App ID: {app_id[:10]}...')
            
            payload = {
                "app_id": app_id,
                "app_secret": app_secret
            }
            headers = {'Content-Type': 'application/json'}
            
            response = requests.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                headers=headers, 
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == 0:
                token = data["tenant_access_token"]
                write_log(config_id, 'SUCCESS', '飞书访问令牌获取成功')
                return token
            else:
                error_msg = f"获取飞书Token失败: {data.get('msg')}"
                write_log(config_id, 'ERROR', error_msg)
                return None
                
        except Exception as e:
            error_msg = f"获取飞书Token异常: {e}"
            write_log(config_id, 'ERROR', error_msg)
            return None
    
    def get_feishu_data(self, config: Dict, access_token: str, limit: Optional[int] = None, raise_error: bool = False) -> Optional[List[Dict]]:
        """获取飞书多维表格数据"""
        try:
            write_log(config['id'], 'INFO', f'开始获取飞书数据, Base ID: {config["base_id"][:10]}..., Table ID: {config["table_id"][:10]}...')
            
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{config['base_id']}/tables/{config['table_id']}/records"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            params = {"page_size": 500}
            if limit:
                params["page_size"] = max(1, min(int(limit), 500))
            if config.get('view_id'):
                params['view_id'] = config['view_id']
            
            all_records = []
            page_token = None
            page_count = 0
            
            while True:
                page_count += 1
                current_params = params.copy()
                if page_token:
                    current_params['page_token'] = page_token
                
                response = requests.get(url, headers=headers, params=current_params, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                if data.get("code") == 0:
                    items = data.get("data", {}).get("items", [])
                    current_page_size = len(items)
                    all_records.extend(items)
                    if limit and len(all_records) >= int(limit):
                        all_records = all_records[:int(limit)]
                        break
                    
                    write_log(config['id'], 'INFO', f'获取第{page_count}页数据，{current_page_size}条记录')
                    
                    next_page_token = data.get("data", {}).get("page_token")
                    if not next_page_token:
                        break
                    page_token = next_page_token
                else:
                    error_msg = self._format_feishu_api_error(data)
                    write_log(config['id'], 'ERROR', error_msg)
                    if raise_error:
                        raise RuntimeError(error_msg)
                    return None
            
            write_log(config['id'], 'SUCCESS', f'飞书数据获取完成，共{len(all_records)}条记录，{page_count}页')
            return all_records
            
        except Exception as e:
            raw_error = str(e)
            error_msg = raw_error if raw_error.startswith("飞书接口返回错误") else f"获取飞书数据异常: {raw_error}"
            if raise_error and raw_error.startswith("飞书接口返回错误"):
                raise RuntimeError(raw_error)
            write_log(config['id'], 'ERROR', error_msg)
            if raise_error:
                raise RuntimeError(error_msg)
            return None

    def preview_feishu_data(self, config: Dict, access_token: str, limit: int = 20, raise_error: bool = False) -> Dict:
        """获取一页飞书样本，用于连通性测试；不代表全量记录数。"""
        try:
            preview_limit = max(1, min(int(limit or 20), 500))
            write_log(config['id'], 'INFO', f'开始预览飞书数据, Base ID: {config["base_id"][:10]}..., Table ID: {config["table_id"][:10]}...')

            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{config['base_id']}/tables/{config['table_id']}/records"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            params = {"page_size": preview_limit}
            if config.get('view_id'):
                params['view_id'] = config['view_id']

            response = requests.get(url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            if data.get("code") != 0:
                error_msg = self._format_feishu_api_error(data)
                write_log(config['id'], 'ERROR', error_msg)
                if raise_error:
                    raise RuntimeError(error_msg)
                return {"records": [], "sample_count": 0, "has_more": False, "total": None, "error": error_msg}

            payload = data.get("data", {}) or {}
            items = payload.get("items", []) or []
            return {
                "records": items,
                "sample_count": len(items),
                "has_more": bool(payload.get("has_more") or payload.get("page_token")),
                "total": payload.get("total"),
                "page_size": preview_limit,
                "view_id": config.get("view_id") or "",
            }
        except Exception as e:
            raw_error = str(e)
            error_msg = raw_error if raw_error.startswith("飞书接口返回错误") else f"预览飞书数据异常: {raw_error}"
            write_log(config['id'], 'ERROR', error_msg)
            if raise_error:
                raise RuntimeError(error_msg)
            return {"records": [], "sample_count": 0, "has_more": False, "total": None, "error": error_msg}

    def get_feishu_fields(self, config: Dict, access_token: str, raise_error: bool = False) -> Optional[List[Dict]]:
        """获取飞书表字段元数据。字段检测优先用它，避免空字段在记录样本里丢失。"""
        try:
            write_log(config['id'], 'INFO', f'开始获取飞书字段元数据, Table ID: {config["table_id"][:10]}...')
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{config['base_id']}/tables/{config['table_id']}/fields"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            params = {"page_size": 100}
            page_token = None
            seen_page_tokens = set()
            all_fields = []

            for _ in range(20):
                current_params = params.copy()
                if page_token:
                    current_params["page_token"] = page_token
                response = requests.get(url, headers=headers, params=current_params, timeout=15)
                response.raise_for_status()
                data = response.json()
                if data.get("code") != 0:
                    error_msg = self._format_feishu_api_error(data)
                    write_log(config['id'], 'ERROR', error_msg)
                    if raise_error:
                        raise RuntimeError(error_msg)
                    return None
                data_payload = data.get("data") or {}
                items = data_payload.get("items") or []
                all_fields.extend(items)
                next_page_token = data_payload.get("page_token")
                if not next_page_token or next_page_token in seen_page_tokens:
                    break
                seen_page_tokens.add(next_page_token)
                page_token = next_page_token
                if not page_token:
                    break
            else:
                write_log(config['id'], 'WARNING', '飞书字段元数据分页超过20页，已停止继续翻页')

            normalized = [
                self._normalize_field_item(item, index + 1)
                for index, item in enumerate(all_fields)
                if (item.get("field_name") or item.get("name"))
            ]
            write_log(config['id'], 'SUCCESS', f'飞书字段元数据获取完成，共{len(normalized)}个字段')
            return normalized
        except Exception as e:
            raw_error = str(e)
            error_msg = raw_error if raw_error.startswith("飞书接口返回错误") else f"获取飞书字段元数据异常: {raw_error}"
            if raise_error and raw_error.startswith("飞书接口返回错误"):
                raise RuntimeError(raw_error)
            write_log(config['id'], 'ERROR', error_msg)
            if raise_error:
                raise RuntimeError(error_msg)
            return None
    
    def get_postgres_connection(self, config: Dict) -> Optional[psycopg2.extensions.connection]:
        """获取PostgreSQL连接"""
        try:
            db_config = None
            for db in get_datasources():
                if db.get('type') == 'postgresql' and db.get('is_active') and db.get('is_default'):
                    db_config = db
                    break

            if not db_config:
                for db in get_datasources():
                    if db.get('type') == 'postgresql' and db.get('is_active'):
                        db_config = db
                        break
            
            if not db_config:
                print("未找到活跃的PostgreSQL数据源")
                return None

            conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database_name'],
                user=db_config['username'],
                password=decode_secret(db_config.get('password_b64', '')),
                connect_timeout=30
            )
            return conn
            
        except Exception as e:
            print(f"连接PostgreSQL失败: {e}")
            return None
    
    def ensure_schema_registry_table(self, conn: psycopg2.extensions.connection) -> None:
        """创建飞书字段快照记录表。"""
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feishu_sync_schema_registry (
                id BIGSERIAL PRIMARY KEY,
                config_id INTEGER,
                target_table TEXT NOT NULL,
                base_id TEXT,
                table_id TEXT,
                view_id TEXT,
                field_names JSONB NOT NULL DEFAULT '[]'::jsonb,
                field_count INTEGER NOT NULL DEFAULT 0,
                diff JSONB NOT NULL DEFAULT '{}'::jsonb,
                sample_record_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_feishu_schema_registry_target
            ON feishu_sync_schema_registry(target_table, updated_at DESC);
        """)
        conn.commit()

    def table_exists(self, conn: psycopg2.extensions.connection, table_name: str) -> bool:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            )
            """,
            (table_name,),
        )
        row = cursor.fetchone()
        return bool(row and row[0])

    def get_existing_field_names(self, conn: psycopg2.extensions.connection, table_name: str) -> List[str]:
        """从已落库 JSONB 数据中识别历史字段。"""
        if not self.table_exists(conn, table_name):
            return []
        cursor = conn.cursor()
        query = sql.SQL("""
            SELECT DISTINCT key
            FROM {table}, LATERAL jsonb_object_keys(fields) AS key
            WHERE fields IS NOT NULL
            ORDER BY key
        """).format(table=sql.Identifier(table_name))
        cursor.execute(query)
        return [row[0] for row in cursor.fetchall()]

    def get_latest_schema_snapshot(self, conn: psycopg2.extensions.connection, config: Dict, table_name: str) -> Dict:
        """读取最近一次字段快照。没有快照时返回空。"""
        self.ensure_schema_registry_table(conn)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT field_names, diff, updated_at
            FROM feishu_sync_schema_registry
            WHERE target_table = %s
              AND (%s = '' OR table_id = %s)
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """,
            (table_name, str(config.get("table_id") or ""), str(config.get("table_id") or "")),
        )
        row = cursor.fetchone()
        if not row:
            return {"field_names": [], "field_rows": [], "updated_at": None}
        field_names, diff, updated_at = row
        diff = diff or {}
        return {
            "field_names": field_names or [],
            "field_rows": diff.get("field_rows") or [],
            "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at,
        }

    def compare_schema(self, conn: psycopg2.extensions.connection, table_name: str, records: List[Dict], config: Optional[Dict] = None, field_items: Optional[List[Dict]] = None) -> Dict:
        """比较飞书当前字段和 PG 既有字段。"""
        config = config or {}
        target_table = self.normalize_table_name(table_name)
        current_field_rows = field_items or []
        if not current_field_rows:
            current_names = self._extract_record_fields(records)
            current_field_rows = [
                {"sequence": index + 1, "field_id": "", "name": name, "type_code": "", "type": "样本推断", "is_primary": False}
                for index, name in enumerate(current_names)
            ]
        feishu_fields = [item["name"] for item in current_field_rows if item.get("name")]
        snapshot = self.get_latest_schema_snapshot(conn, config, target_table)
        if snapshot.get("field_names"):
            database_fields = snapshot["field_names"]
            baseline_source = "schema_registry"
        else:
            database_fields = self.get_existing_field_names(conn, target_table)
            baseline_source = "pg_jsonb"
        feishu_set = set(feishu_fields)
        database_set = set(database_fields)
        table_exists = self.table_exists(conn, target_table)
        added_fields = sorted(feishu_set - database_set)
        removed_fields = sorted(database_set - feishu_set)
        common_fields = sorted(feishu_set & database_set)
        field_rows = []
        for item in current_field_rows:
            name = item.get("name")
            if not name:
                continue
            if name in added_fields:
                status = "added"
                status_text = "新增"
            elif name in common_fields:
                status = "same"
                status_text = "一致"
            else:
                status = "current"
                status_text = "当前字段"
            field_rows.append({
                **item,
                "status": status,
                "status_text": status_text,
                "in_feishu": True,
                "in_pg": name in database_set,
            })
        known_sequence = len(field_rows)
        for offset, name in enumerate(removed_fields, start=1):
            field_rows.append({
                "sequence": known_sequence + offset,
                "field_id": "",
                "name": name,
                "type_code": "",
                "type": "历史字段",
                "is_primary": False,
                "status": "removed",
                "status_text": "减少",
                "in_feishu": False,
                "in_pg": True,
            })
        return {
            "target_table": target_table,
            "table_exists": table_exists,
            "feishu_fields": feishu_fields,
            "database_fields": database_fields,
            "added_fields": added_fields,
            "removed_fields": removed_fields,
            "common_fields": common_fields,
            "field_rows": field_rows,
            "field_count": len(feishu_fields),
            "database_field_count": len(database_fields),
            "record_sample_count": len(records or []),
            "baseline_source": baseline_source,
            "baseline_updated_at": snapshot.get("updated_at"),
        }

    def save_schema_snapshot(self, conn: psycopg2.extensions.connection, config: Dict, records: List[Dict], diff: Dict) -> None:
        """保存字段快照，便于后续发现字段新增/减少。"""
        self.ensure_schema_registry_table(conn)
        target_table = self.normalize_table_name(config.get("target_table"))
        fields = diff.get("feishu_fields") or self._extract_record_fields(records)
        sample_record_id = ""
        if records:
            sample_record_id = str(records[0].get("record_id") or "")
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO feishu_sync_schema_registry
                (config_id, target_table, base_id, table_id, view_id, field_names, field_count, diff, sample_record_id, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, CURRENT_TIMESTAMP)
            """,
            (
                config.get("id"),
                target_table,
                config.get("base_id", ""),
                config.get("table_id", ""),
                config.get("view_id", ""),
                json.dumps(fields, ensure_ascii=False),
                len(fields),
                json.dumps(diff, ensure_ascii=False),
                sample_record_id,
            ),
        )
        conn.commit()

    def create_target_table(self, conn: psycopg2.extensions.connection, table_name: str) -> bool:
        """创建目标表"""
        try:
            cursor = conn.cursor()
            target_table = self.normalize_table_name(table_name)
            
            create_table_sql = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {table} (
                id BIGSERIAL PRIMARY KEY,
                record_id TEXT UNIQUE,
                fields JSONB,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS {record_idx} ON {table}(record_id);
            CREATE INDEX IF NOT EXISTS {sync_idx} ON {table}(sync_time);
            """).format(
                table=sql.Identifier(target_table),
                record_idx=sql.Identifier(self._index_name(target_table, "record_id")),
                sync_idx=sql.Identifier(self._index_name(target_table, "sync_time")),
            )
            
            cursor.execute(create_table_sql)
            conn.commit()
            print(f"成功创建/更新表: {target_table}")
            return True
            
        except Exception as e:
            print(f"创建表失败: {e}")
            return False
    
    def get_last_sync_time(self, conn: psycopg2.extensions.connection, table_name: str) -> Optional[datetime]:
        """获取最后同步时间"""
        try:
            cursor = conn.cursor()
            target_table = self.normalize_table_name(table_name)
            cursor.execute(
                sql.SQL("SELECT MAX(sync_time) FROM {table}").format(table=sql.Identifier(target_table))
            )
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
        except Exception:
            return None

    def preview_schema(self, config: Dict, sample_limit: int = 50) -> Dict:
        """获取飞书样本并对比 PG 目标表字段差异。"""
        access_token = self.get_access_token(config["app_id"], config["app_secret"], int(config.get("id") or 0))
        if not access_token:
            raise RuntimeError("获取飞书访问令牌失败")

        field_items = self.get_feishu_fields(config, access_token, raise_error=False) or []
        records = self.get_feishu_data(config, access_token, limit=sample_limit, raise_error=True)
        if records is None:
            raise RuntimeError("获取飞书样本数据失败")

        conn = self.get_postgres_connection(config)
        if not conn:
            raise RuntimeError("连接 PostgreSQL 失败")
        try:
            preview = self.compare_schema(conn, config.get("target_table", ""), records, config=config, field_items=field_items)
            preview["field_source"] = "feishu_metadata" if field_items else "record_sample"
            preview["field_source_text"] = "飞书字段元数据" if field_items else "记录样本推断"
            if not field_items:
                preview["warning"] = "未能读取飞书字段元数据，当前字段明细由记录样本推断；空字段可能无法被发现。"
            return preview
        finally:
            conn.close()
    
    def sync_data_to_postgres(self, config: Dict, records: List[Dict]) -> bool:
        """同步数据到PostgreSQL"""
        conn = self.get_postgres_connection(config)
        if not conn:
            return False
        
        try:
            table_name = self.normalize_table_name(config['target_table'])
            config['target_table'] = table_name
            
            # 创建目标表
            if not self.create_target_table(conn, table_name):
                return False

            schema_diff = self.compare_schema(conn, table_name, records, config=config, field_items=config.get("_field_items") or [])
            self.save_schema_snapshot(conn, config, records, schema_diff)
            if schema_diff.get("added_fields"):
                write_log(config["id"], "INFO", f"发现飞书新增字段: {', '.join(schema_diff['added_fields'][:20])}")
            if schema_diff.get("removed_fields"):
                write_log(config["id"], "WARNING", f"发现飞书缺失历史字段: {', '.join(schema_diff['removed_fields'][:20])}")
            
            cursor = conn.cursor()
            
            # 增量同步：按 record_id upsert，既保留幂等，也能覆盖飞书侧已修改记录。
            if config.get('sync_mode') == 'incremental':
                last_sync_time = self.get_last_sync_time(conn, table_name)
                if last_sync_time:
                    # 飞书字段和历史记录可能会变化，统一走 UPSERT，避免只插新记录导致数据陈旧。
                    records_to_sync = records
                    print(f"增量同步：共{len(records)}条记录，按record_id执行UPSERT")
                else:
                    records_to_sync = records
                    print(f"首次全量同步：{len(records)}条记录")
            else:
                # 全量同步
                records_to_sync = records
                print(f"全量同步：{len(records)}条记录")
            
            # 批量插入/更新数据
            if records_to_sync:
                sync_time = datetime.now()
                normalized_records = self._normalize_records_for_storage(
                    records_to_sync,
                    config.get("_field_items") or [],
                )

                # 全量模式下先清空目标表，确保与飞书当前视图完全一致。
                if config.get('sync_mode') == 'full':
                    print(f"全量同步：清空表 {table_name}")
                    cursor.execute(sql.SQL("TRUNCATE TABLE {table}").format(table=sql.Identifier(table_name)))
                    write_log(config['id'], 'INFO', f'全量同步：已清空表 {table_name}')

                for record in normalized_records:
                    record_id = record.get('record_id', '')
                    # 使用UPSERT操作（增量模式依赖唯一约束去重，全量模式已清空表）
                    upsert_sql = sql.SQL("""
                        INSERT INTO {table} (record_id, fields, sync_time, created_time, updated_time)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (record_id) 
                        DO UPDATE SET 
                            fields = EXCLUDED.fields,
                            sync_time = EXCLUDED.sync_time,
                            updated_time = EXCLUDED.updated_time
                    """).format(table=sql.Identifier(table_name))
                    cursor.execute(upsert_sql, (record_id, Json(record.get('fields', {})), sync_time, sync_time, sync_time))
                
                conn.commit()
                print(f"成功同步{len(normalized_records)}条记录到{table_name}")

            # 触发关联的数据集转换任务（失败不影响同步任务状态）
            try:
                from dataset_transform_service import transform_service
                triggered = transform_service.run_transforms_by_source_table(table_name)
                if triggered:
                    write_log(config['id'], 'INFO', f"已触发 {len(triggered)} 个数据集转换任务")
            except Exception as e:
                write_log(config['id'], 'ERROR', f"触发数据集转换任务失败: {e}")
            
            return True
            
        except Exception as e:
            print(f"同步数据到PostgreSQL失败: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def sync_single_config(self, config_or_id: Union[Dict, int, str]) -> bool:
        """同步单个配置。支持传入配置对象或配置 ID，
        传入 ID 时会重新读取最新配置，避免定时任务使用启动时的旧配置。"""
        if isinstance(config_or_id, dict):
            config = config_or_id
        else:
            config_id = int(config_or_id)
            configs = get_feishu_configs()
            config = next((c for c in configs if c.get('id') == config_id), None)
            if not config:
                print(f"未找到配置: {config_id}")
                return False

        try:
            print(f"\n开始同步配置: {config['name']}")
            update_sync_status(config['id'], 'running')
            
            # 获取访问令牌
            access_token = self.get_access_token(config['app_id'], config['app_secret'], config['id'])
            if not access_token:
                update_sync_status(config['id'], 'failed')
                return False

            field_items = self.get_feishu_fields(config, access_token) or []
            
            # 获取飞书数据
            records = self.get_feishu_data(config, access_token)
            if records is None:
                update_sync_status(config['id'], 'failed')
                return False
            
            # 同步到PostgreSQL
            write_log(config['id'], 'INFO', f'开始同步数据到PostgreSQL，共{len(records)}条记录')
            sync_config = dict(config)
            sync_config["_field_items"] = field_items
            success = self.sync_data_to_postgres(sync_config, records)
            if success:
                sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                write_log(config['id'], 'INFO', f'数据库同步成功，更新状态为success')
                update_sync_status(config['id'], 'success', sync_time)
                write_log(config['id'], 'SUCCESS', f'配置 {config["name"]} 同步完成')
                print(f"配置 {config['name']} 同步完成")
            else:
                write_log(config['id'], 'ERROR', f'数据库同步失败，更新状态为failed')
                update_sync_status(config['id'], 'failed')
                print(f"配置 {config['name']} 同步失败")
            
            return success
            
        except Exception as e:
            print(f"同步配置 {config['name']} 异常: {e}")
            update_sync_status(config['id'], 'failed')
            return False
    
    def sync_all_active_configs(self):
        """同步所有活跃配置"""
        configs = get_feishu_configs()
        active_configs = [c for c in configs if c.get('is_active')]
        
        if not active_configs:
            print("没有活跃的飞书同步配置")
            return
        
        print(f"开始同步{len(active_configs)}个活跃配置")
        
        for config in active_configs:
            self.sync_single_config(config)
    
    def start_scheduler(self):
        """启动定时同步"""
        print("启动飞书同步调度器...")
        
        # 配置定时任务
        configs = get_feishu_configs()
        for config in configs:
            if config.get('is_active'):
                frequency = int(config.get('sync_frequency', 30))  # 分钟
                # 传入 config_id 而不是 config 对象，确保每次执行都读取最新配置
                schedule.every(frequency).minutes.do(
                    self.sync_single_config, config['id']
                ).tag(f"feishu_sync_{config['id']}")
        
        # 立即执行一次同步
        self.sync_all_active_configs()
        
        # 启动调度器
        self.running = True
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    def stop_scheduler(self):
        """停止定时同步"""
        print("停止飞书同步调度器...")
        self.running = False
        schedule.clear()

# 全局同步服务实例
sync_service = FeishuSyncService()

def start_feishu_sync():
    """启动飞书同步服务"""
    try:
        sync_service.start_scheduler()
    except KeyboardInterrupt:
        print("飞书同步服务被用户中断")
        sync_service.stop_scheduler()
    except Exception as e:
        print(f"飞书同步服务异常: {e}")

if __name__ == "__main__":
    start_feishu_sync()

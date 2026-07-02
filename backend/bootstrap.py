"""
SmartAsk container/local one-shot bootstrap.

Order of operations (each step is best-effort and idempotent):
    1. Wait for PostgreSQL (default datasource)
    2. Apply schema migrations under backend/migrations (BEGIN/COMMIT-stripped, dollar-quote-aware)
    3. Restore runtime config bundle into config/*.json (only fills missing keys, never clobbers user edits)
    4. First boot only: import bookshelf_bundle.json + angel_group_data_bundle.json
    5. Sync idempotent built-in dataset templates that should ship with code
    6. Hand off to app.py via os.execv

Env switches:
    SMARTASK_BOOTSTRAP_SKIP_DB=1            -> skip DB step entirely, only start Flask
    SMARTASK_BOOTSTRAP_FORCE_IMPORT=1       -> import bundles even if bs_datasets is non-empty
    SMARTASK_BOOTSTRAP_FORCE_CONFIG=1       -> overwrite existing config files from runtime bundle
    SMARTASK_BOOTSTRAP_SKIP_BUILTINS=1      -> skip built-in dataset template sync
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from typing import Optional

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

BASE_DIR = os.path.dirname(CURRENT_DIR)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(BASE_DIR, ".env"), override=False)
    load_dotenv(os.path.join(BASE_DIR, ".env.local"), override=True)
except Exception:
    pass

from secret_codec import decrypt_secret_value


def _env_value(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return decrypt_secret_value(value) if value else default


MIGRATIONS = [
    "20260330_bookshelf_schema.sql",
    "20260330_bookshelf_agent1_prompt_upgrade.sql",
    "20260430_report_config.sql",
    "20260509_report_thresholds.sql",
    "20260512_system_event_logs.sql",
    "20260627_ecommerce_standard_view.sql",
    "20260630_dataset_transforms.sql",
]

IMPORTS_DIR = os.path.join(CURRENT_DIR, "imports")
BOOKSHELF_BUNDLE = os.path.join(IMPORTS_DIR, "bookshelf_bundle.json")
ANGEL_BUNDLE = os.path.join(IMPORTS_DIR, "angel_group_data_bundle.json")
RUNTIME_CONFIG_BUNDLE = os.path.join(IMPORTS_DIR, "runtime_config_bundle.json")
DEFAULT_TRANSFORMS_BUNDLE = os.path.join(IMPORTS_DIR, "default_dataset_transforms.json")


def log(msg: str) -> None:
    print(f"[bootstrap] {msg}", flush=True)


def _datasource_kwargs() -> dict:
    """Resolve PG connection params from default datasource + env fallback."""
    try:
        from config_manager import get_default_datasource

        ds = get_default_datasource() or {}
    except Exception as exc:
        log(f"无法读取默认数据源: {exc}; 仅用环境变量")
        ds = {}

    return dict(
        host=ds.get("host") or _env_value("SMARTASK_DB_HOST", "postgres"),
        port=int(ds.get("port") or _env_value("SMARTASK_DB_PORT", "5432") or 5432),
        database=ds.get("database_name") or _env_value("SMARTASK_DB_DATABASE", "postgres"),
        user=ds.get("username") or _env_value("SMARTASK_DB_USERNAME", "postgres"),
        password=ds.get("password") or _env_value("SMARTASK_DB_PASSWORD", "postgres"),
        connect_timeout=8,
    )


def _wait_for_postgres(max_wait_seconds: int = 120) -> bool:
    try:
        import psycopg2
    except Exception as exc:
        log(f"未安装 psycopg2: {exc}")
        return False

    start = time.time()
    last_error: Optional[str] = None
    while time.time() - start < max_wait_seconds:
        try:
            conn = psycopg2.connect(**_datasource_kwargs())
            conn.close()
            kw = _datasource_kwargs()
            log(f"PostgreSQL 已就绪 ({kw['host']}:{kw['port']}/{kw['database']})")
            return True
        except Exception as exc:
            last_error = str(exc)
            time.sleep(2)
    log(f"等待 PostgreSQL 超时: {last_error}")
    return False


def _strip_transaction_keywords(raw_sql: str) -> str:
    """Remove top-level BEGIN; / COMMIT; while keeping them inside dollar-quoted blocks."""
    cleaned: list[str] = []
    in_dollar_quote = False
    for line in raw_sql.splitlines():
        occurrences = line.count("$$")
        if not in_dollar_quote:
            stripped = line.strip().upper()
            if stripped in ("BEGIN;", "COMMIT;", "START TRANSACTION;"):
                if occurrences % 2 == 1:
                    in_dollar_quote = True
                continue
        if occurrences % 2 == 1:
            in_dollar_quote = not in_dollar_quote
        cleaned.append(line)
    return "\n".join(cleaned)


def _run_migration(filename: str) -> None:
    import psycopg2

    path = os.path.join(CURRENT_DIR, "migrations", filename)
    if not os.path.exists(path):
        log(f"跳过迁移（文件缺失）: {filename}")
        return

    conn = psycopg2.connect(**_datasource_kwargs())
    try:
        conn.autocommit = True
        with open(path, "r", encoding="utf-8") as fh:
            sql = _strip_transaction_keywords(fh.read())
        with conn.cursor() as cur:
            cur.execute(sql)
        log(f"迁移已应用: {filename}")
    finally:
        conn.close()


def _bs_dataset_count() -> int:
    import psycopg2

    try:
        with psycopg2.connect(**_datasource_kwargs()) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM bs_datasets;")
                row = cur.fetchone()
                return int(row[0]) if row else 0
    except Exception as exc:
        log(f"无法统计 bs_datasets 行数: {exc}")
        return -1


def _import_runtime_config() -> None:
    if not os.path.exists(RUNTIME_CONFIG_BUNDLE):
        log("未找到 runtime_config_bundle.json，跳过运行时配置恢复")
        return
    try:
        from import_runtime_config import import_bundle

        force = os.getenv("SMARTASK_BOOTSTRAP_FORCE_CONFIG", "").lower() in {"1", "true", "yes"}
        result = import_bundle(RUNTIME_CONFIG_BUNDLE, force_overwrite=force)
        log(f"运行时配置恢复: {result.get('written_files')}")
    except Exception as exc:
        log(f"运行时配置恢复失败（非致命）: {exc}")
        traceback.print_exc()


def _import_bookshelf_bundle() -> None:
    if not os.path.exists(BOOKSHELF_BUNDLE):
        log("未找到 bookshelf_bundle.json，跳过元数据导入")
        return
    try:
        from import_bookshelf_bundle import import_bundle

        result = import_bundle(BOOKSHELF_BUNDLE)
        log(f"已导入 Bookshelf 元数据: {result.get('imported_counts')}")
    except Exception as exc:
        log(f"导入 Bookshelf 元数据失败（非致命）: {exc}")
        traceback.print_exc()


def _import_angel_bundle() -> None:
    if not os.path.exists(ANGEL_BUNDLE):
        log("未找到 angel_group_data_bundle.json，跳过业务数据导入")
        return
    try:
        from import_angel_group_data import import_bundle

        result = import_bundle(ANGEL_BUNDLE)
        log(f"已导入 angel_group_data {result.get('row_count', 0)} 行")
    except Exception as exc:
        log(f"导入 angel_group_data 失败（非致命）: {exc}")
        traceback.print_exc()


ECOMMERCE_COMMON_QUESTIONS = [
    {"question_text": "电商事业部的业绩", "sort_order": 10},
    {"question_text": "电商事业部三大业务部年度目标营收对比", "sort_order": 20},
    {"question_text": "电商事业部业务部业绩排名", "sort_order": 30},
    {"question_text": "国内业务部的业绩", "sort_order": 40},
    {"question_text": "国内业务部有哪些细分业务", "sort_order": 50},
    {"question_text": "净水业务下有哪些业务经理", "sort_order": 60},
    {"question_text": "电商事业部细分业务达成率排名", "sort_order": 70},
    {"question_text": "京东直营和天猫直营对比", "sort_order": 80},
    {"question_text": "电商事业部业务承接人业绩排名", "sort_order": 90},
    {"question_text": "电商事业部负责人刘志伟的业绩", "sort_order": 100},
    {"question_text": "电商事业部达成率低于30%的细分业务有哪些", "sort_order": 110},
    {"question_text": "电商事业部前5的细分业务", "sort_order": 120},
]


def _sync_builtin_datasets() -> None:
    if os.getenv("SMARTASK_BOOTSTRAP_SKIP_BUILTINS", "").lower() in {"1", "true", "yes"}:
        log("SMARTASK_BOOTSTRAP_SKIP_BUILTINS=1，跳过内置数据集模板同步")
        return
    try:
        from create_consumer_standard_dataset import apply_payload_direct

        result = apply_payload_direct()
        log(
            "已同步内置数据集模板: "
            f"{result.get('dataset_code')} id={result.get('dataset_id')} "
            f"golden={result.get('golden_sql_count')}"
        )
    except Exception as exc:
        log(f"同步内置数据集模板失败（非致命）: {exc}")
        traceback.print_exc()


def _sync_default_dataset_transforms() -> None:
    """同步默认数据集转换任务。

    新系统部署时，只要内置数据集（如电商事业部）已通过 bundle 导入，
    就自动为其创建对应的视图/表转换任务。如果源表已有数据，立即执行一次，
    让视图在飞书同步前或同步后都能自动出现，无需手动跑脚本。
    """
    if os.getenv("SMARTASK_BOOTSTRAP_SKIP_BUILTINS", "").lower() in {"1", "true", "yes"}:
        log("SMARTASK_BOOTSTRAP_SKIP_BUILTINS=1，跳过默认转换任务同步")
        return
    if not os.path.exists(DEFAULT_TRANSFORMS_BUNDLE):
        log("未找到 default_dataset_transforms.json，跳过默认转换任务同步")
        return
    try:
        import json
        import psycopg2

        with open(DEFAULT_TRANSFORMS_BUNDLE, "r", encoding="utf-8") as fh:
            default_transforms = json.load(fh)
        if not isinstance(default_transforms, list):
            log("default_dataset_transforms.json 格式应为数组，跳过")
            return
    except Exception as exc:
        log(f"读取 default_dataset_transforms.json 失败（非致命）: {exc}")
        return

    try:
        from dataset_transform_service import transform_service
    except Exception as exc:
        log(f"导入 transform_service 失败，默认转换任务仅做预置不自动执行（非致命）: {exc}")
        transform_service = None

    inserted_count = 0
    executed_count = 0
    skipped_count = 0

    try:
        with psycopg2.connect(**_datasource_kwargs()) as conn:
            with conn.cursor() as cur:
                for item in default_transforms:
                    dataset_code = str(item.get("dataset_code") or "").strip()
                    name = str(item.get("name") or "").strip()
                    target_name = str(item.get("target_name") or "").strip()
                    source_table = str(item.get("source_table") or "").strip()
                    if not dataset_code or not name or not target_name or not source_table:
                        log(f"默认转换任务配置不完整，跳过: {item}")
                        continue

                    cur.execute(
                        "SELECT id FROM bs_datasets WHERE dataset_code = %s AND is_active = TRUE LIMIT 1;",
                        (dataset_code,),
                    )
                    row = cur.fetchone()
                    if not row:
                        log(f"未找到数据集 {dataset_code}，跳过默认转换任务: {name}")
                        skipped_count += 1
                        continue
                    dataset_id = row[0]

                    # 按目标名去重：避免重复创建同名视图/表
                    cur.execute(
                        "SELECT id FROM bs_dataset_transforms WHERE dataset_id = %s AND target_name = %s LIMIT 1;",
                        (dataset_id, target_name),
                    )
                    if cur.fetchone():
                        log(f"数据集 {dataset_code} 已存在目标为 {target_name} 的转换任务，跳过")
                        skipped_count += 1
                        continue

                    cur.execute(
                        """
                        INSERT INTO bs_dataset_transforms
                            (dataset_id, name, source_table, target_type, target_name,
                             transform_sql, is_active, auto_run_on_sync, sync_dependency,
                             updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        RETURNING id;
                        """,
                        (
                            dataset_id,
                            name,
                            source_table,
                            str(item.get("target_type") or "view").strip().lower(),
                            target_name,
                            str(item.get("transform_sql") or "").strip(),
                            bool(item.get("is_active", True)),
                            bool(item.get("auto_run_on_sync", True)),
                            str(item.get("sync_dependency") or ""),
                        ),
                    )
                    new_id = cur.fetchone()[0]
                    conn.commit()
                    inserted_count += 1
                    log(f"已预置默认转换任务: {name} (id={new_id}) -> {target_name}")

                    # 如果源表已经有数据，立即执行一次，保证视图立即可用
                    try:
                        cur.execute(
                            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s LIMIT 1;",
                            (source_table,),
                        )
                        table_exists = cur.fetchone() is not None
                        if table_exists and transform_service:
                            result = transform_service.execute_transform(int(new_id), triggered_by="bootstrap")
                            if result.get("success"):
                                executed_count += 1
                                log(f"默认转换任务已立即执行: {target_name}")
                            else:
                                log(f"默认转换任务立即执行失败（非致命）: {result.get('message')}")
                    except Exception as exc:
                        log(f"默认转换任务立即执行异常（非致命）: {exc}")
    except Exception as exc:
        log(f"同步默认转换任务失败（非致命）: {exc}")
        traceback.print_exc()
        return

    log(f"默认转换任务同步完成: 新增 {inserted_count} 个, 立即执行 {executed_count} 个, 跳过 {skipped_count} 个")


def _sync_ecommerce_common_questions() -> None:
    """同步电商数据集常用问题（该数据集由标准视图迁移创建，无 payload 模板）。"""
    if os.getenv("SMARTASK_BOOTSTRAP_SKIP_BUILTINS", "").lower() in {"1", "true", "yes"}:
        return
    try:
        import psycopg2

        with psycopg2.connect(**_datasource_kwargs()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM bs_datasets WHERE dataset_code = %s LIMIT 1;",
                    ("feishu_tbldianshang",),
                )
                row = cur.fetchone()
                if not row:
                    log("未找到电商数据集 feishu_tbldianshang，跳过常用问题同步")
                    return
                dataset_id = row[0]
                cur.execute(
                    "SELECT COUNT(*) FROM bs_common_questions WHERE dataset_id = %s;",
                    (dataset_id,),
                )
                if cur.fetchone()[0] > 0:
                    log(f"电商数据集常用问题已存在，跳过内置同步: dataset_id={dataset_id}")
                    return
                for item in ECOMMERCE_COMMON_QUESTIONS:
                    cur.execute(
                        """
                        INSERT INTO bs_common_questions(dataset_id, question_text, sort_order, is_active)
                        VALUES (%s, %s, %s, TRUE);
                        """,
                        (dataset_id, item["question_text"], item["sort_order"]),
                    )
        log(f"已同步电商数据集常用问题: dataset_id={dataset_id} 共{len(ECOMMERCE_COMMON_QUESTIONS)}条")
    except Exception as exc:
        log(f"同步电商数据集常用问题失败（非致命）: {exc}")
        traceback.print_exc()


def main() -> None:
    log("========== SmartAsk Bootstrap 开始 ==========")

    skip_db = os.getenv("SMARTASK_BOOTSTRAP_SKIP_DB", "").lower() in {"1", "true", "yes"}

    if skip_db:
        log("环境变量 SMARTASK_BOOTSTRAP_SKIP_DB=1，跳过 DB 初始化")
    elif not _wait_for_postgres():
        log("⚠️ PostgreSQL 不可达，跳过迁移与首次导入；后端仍将启动以便排错。")
    else:
        try:
            from config_manager import init_default_configs

            init_default_configs()
        except Exception as exc:
            log(f"初始化默认 JSON 配置失败（非致命）: {exc}")

        # 1) 优先恢复 runtime_config_bundle，让后续步骤用到的数据源/AI 配置已正确
        _import_runtime_config()

        for migration in MIGRATIONS:
            try:
                _run_migration(migration)
            except Exception as exc:
                log(f"迁移 {migration} 失败（非致命）: {exc}")
                traceback.print_exc()

        existing = _bs_dataset_count()
        force_import = os.getenv("SMARTASK_BOOTSTRAP_FORCE_IMPORT", "").lower() in {"1", "true", "yes"}
        if existing == 0 or force_import:
            log(f"检测到 bs_datasets={existing}，开始首次数据导入...（force={force_import}）")
            _import_bookshelf_bundle()
            _import_angel_bundle()
            # Report config migrations depend on bs_datasets rows. On a fresh
            # Docker volume those rows are created by the bundle import above,
            # so run these idempotent migrations once more after import.
            for migration in ("20260430_report_config.sql", "20260509_report_thresholds.sql"):
                try:
                    _run_migration(migration)
                except Exception as exc:
                    log(f"导入后补跑迁移 {migration} 失败（非致命）: {exc}")
                    traceback.print_exc()
        else:
            log(f"已检测到 bs_datasets={existing} 行，跳过自动导入（保留用户数据）")

        _sync_builtin_datasets()
        _sync_default_dataset_transforms()
        _sync_ecommerce_common_questions()

    log("========== Bootstrap 完成，启动 Flask ==========")
    app_path = os.path.join(CURRENT_DIR, "app.py")
    os.execv(sys.executable, [sys.executable, app_path])


if __name__ == "__main__":
    main()

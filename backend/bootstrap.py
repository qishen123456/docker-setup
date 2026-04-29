"""
SmartAsk container/local one-shot bootstrap.

Order of operations (each step is best-effort and idempotent):
    1. Wait for PostgreSQL (default datasource)
    2. Apply schema migrations under backend/migrations (BEGIN/COMMIT-stripped, dollar-quote-aware)
    3. Restore runtime config bundle into config/*.json (only fills missing keys, never clobbers user edits)
    4. First boot only: import bookshelf_bundle.json + angel_group_data_bundle.json
    5. Hand off to app.py via os.execv

Env switches:
    SMARTASK_BOOTSTRAP_SKIP_DB=1            -> skip DB step entirely, only start Flask
    SMARTASK_BOOTSTRAP_FORCE_IMPORT=1       -> import bundles even if bs_datasets is non-empty
    SMARTASK_BOOTSTRAP_FORCE_CONFIG=1       -> overwrite existing config files from runtime bundle
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


MIGRATIONS = [
    "20260330_bookshelf_schema.sql",
    "20260330_bookshelf_agent1_prompt_upgrade.sql",
]

IMPORTS_DIR = os.path.join(CURRENT_DIR, "imports")
BOOKSHELF_BUNDLE = os.path.join(IMPORTS_DIR, "bookshelf_bundle.json")
ANGEL_BUNDLE = os.path.join(IMPORTS_DIR, "angel_group_data_bundle.json")
RUNTIME_CONFIG_BUNDLE = os.path.join(IMPORTS_DIR, "runtime_config_bundle.json")


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
        host=ds.get("host") or os.getenv("SMARTASK_DB_HOST", "postgres"),
        port=int(ds.get("port") or os.getenv("SMARTASK_DB_PORT", "5432") or 5432),
        database=ds.get("database_name") or os.getenv("SMARTASK_DB_DATABASE", "postgres"),
        user=ds.get("username") or os.getenv("SMARTASK_DB_USERNAME", "postgres"),
        password=ds.get("password") or os.getenv("SMARTASK_DB_PASSWORD", "postgres"),
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
        else:
            log(f"已检测到 bs_datasets={existing} 行，跳过自动导入（保留用户数据）")

    log("========== Bootstrap 完成，启动 Flask ==========")
    app_path = os.path.join(CURRENT_DIR, "app.py")
    os.execv(sys.executable, [sys.executable, app_path])


if __name__ == "__main__":
    main()

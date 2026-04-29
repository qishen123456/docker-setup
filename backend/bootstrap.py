"""
容器/本地一键启动引导脚本。

依次完成：
1. 等待 PostgreSQL 可达
2. 应用基础 schema 迁移（bookshelf_schema.sql + agent1_prompt_upgrade.sql）
3. 首次启动时（bs_datasets 为空）自动导入 metadata bundle 与 angel_group_data 数据
4. 启动 Flask 主应用 (app.py)

设计原则：
- 幂等：可被多次重启而不破坏已有用户数据
- 容错：导入失败不阻止后端启动，便于用户在管理界面排查
- 友好日志：所有关键步骤前后都有清晰的中文日志

运行方式：
    python bootstrap.py
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

# 让 backend 内的模块可被 import
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

BOOKSHELF_BUNDLE = os.path.join(CURRENT_DIR, "imports", "bookshelf_bundle.json")
ANGEL_BUNDLE = os.path.join(CURRENT_DIR, "imports", "angel_group_data_bundle.json")


def log(msg: str) -> None:
    print(f"[bootstrap] {msg}", flush=True)


def _wait_for_postgres(max_wait_seconds: int = 90) -> bool:
    """轮询直到 PostgreSQL 可连接。"""
    try:
        from config_manager import get_default_datasource, decode_secret  # noqa: F401
        import psycopg2
    except Exception as exc:
        log(f"无法加载 psycopg2/config_manager：{exc}")
        return False

    start = time.time()
    last_error: Optional[str] = None
    while time.time() - start < max_wait_seconds:
        try:
            ds = get_default_datasource() or {}
            host = ds.get("host") or os.getenv("SMARTASK_DB_HOST", "postgres")
            port = int(ds.get("port") or os.getenv("SMARTASK_DB_PORT", "5432") or 5432)
            db = ds.get("database_name") or os.getenv("SMARTASK_DB_DATABASE", "postgres")
            user = ds.get("username") or os.getenv("SMARTASK_DB_USERNAME", "postgres")
            password = ds.get("password") or os.getenv("SMARTASK_DB_PASSWORD", "postgres")
            conn = psycopg2.connect(
                host=host, port=port, database=db, user=user, password=password,
                connect_timeout=4,
            )
            conn.close()
            log(f"PostgreSQL 已就绪 ({host}:{port}/{db})")
            return True
        except Exception as exc:
            last_error = str(exc)
            time.sleep(2)
    log(f"等待 PostgreSQL 超时：{last_error}")
    return False


def _run_migration(filename: str) -> None:
    """执行迁移文件。脚本本身使用 IF NOT EXISTS / DO 块，幂等可重复。"""
    import psycopg2

    from config_manager import get_default_datasource

    path = os.path.join(CURRENT_DIR, "migrations", filename)
    if not os.path.exists(path):
        log(f"跳过迁移（文件缺失）: {filename}")
        return

    ds = get_default_datasource() or {}
    conn = psycopg2.connect(
        host=ds.get("host") or os.getenv("SMARTASK_DB_HOST", "postgres"),
        port=int(ds.get("port") or os.getenv("SMARTASK_DB_PORT", "5432") or 5432),
        database=ds.get("database_name") or os.getenv("SMARTASK_DB_DATABASE", "postgres"),
        user=ds.get("username") or os.getenv("SMARTASK_DB_USERNAME", "postgres"),
        password=ds.get("password") or os.getenv("SMARTASK_DB_PASSWORD", "postgres"),
        connect_timeout=8,
    )
    try:
        conn.autocommit = True
        with open(path, "r", encoding="utf-8") as fh:
            raw_sql = fh.read()
        # 仅剥离迁移脚本顶层、并且不在 dollar-quoted ($$...$$) 块内的 BEGIN; / COMMIT;。
        cleaned_lines = []
        in_dollar_quote = False
        for line in raw_sql.splitlines():
            # 一行内 $$ 出现奇数次则切换状态
            occurrences = line.count("$$")
            if not in_dollar_quote:
                stripped = line.strip().upper()
                if stripped in ("BEGIN;", "COMMIT;", "START TRANSACTION;"):
                    if occurrences % 2 == 1:
                        in_dollar_quote = True
                    continue
            if occurrences % 2 == 1:
                in_dollar_quote = not in_dollar_quote
            cleaned_lines.append(line)
        sql = "\n".join(cleaned_lines)
        with conn.cursor() as cur:
            cur.execute(sql)
        log(f"迁移已应用: {filename}")
    finally:
        conn.close()


def _bs_dataset_count() -> int:
    """读取当前 bs_datasets 行数，用于判断是否首次启动。"""
    import psycopg2

    from config_manager import get_default_datasource

    ds = get_default_datasource() or {}
    try:
        with psycopg2.connect(
            host=ds.get("host") or os.getenv("SMARTASK_DB_HOST", "postgres"),
            port=int(ds.get("port") or os.getenv("SMARTASK_DB_PORT", "5432") or 5432),
            database=ds.get("database_name") or os.getenv("SMARTASK_DB_DATABASE", "postgres"),
            user=ds.get("username") or os.getenv("SMARTASK_DB_USERNAME", "postgres"),
            password=ds.get("password") or os.getenv("SMARTASK_DB_PASSWORD", "postgres"),
            connect_timeout=8,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM bs_datasets;")
                row = cur.fetchone()
                return int(row[0]) if row else 0
    except Exception as exc:
        log(f"无法统计 bs_datasets 行数：{exc}")
        return -1


def _import_bookshelf_bundle() -> None:
    if not os.path.exists(BOOKSHELF_BUNDLE):
        log("未找到 bookshelf_bundle.json，跳过自动导入")
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

    if not skip_db:
        if not _wait_for_postgres():
            log("⚠️ 跳过迁移与首次导入（PostgreSQL 不可达）。后端仍将启动。")
        else:
            try:
                from config_manager import init_default_configs

                init_default_configs()
            except Exception as exc:
                log(f"初始化默认配置失败（非致命）: {exc}")

            for migration in MIGRATIONS:
                try:
                    _run_migration(migration)
                except Exception as exc:
                    log(f"迁移 {migration} 失败（非致命）: {exc}")
                    traceback.print_exc()

            existing = _bs_dataset_count()
            force_import = os.getenv("SMARTASK_BOOTSTRAP_FORCE_IMPORT", "").lower() in {"1", "true", "yes"}
            if existing == 0 or force_import:
                log(f"检测到 bs_datasets={existing} 或强制导入={force_import}，开始首次数据导入...")
                _import_bookshelf_bundle()
                _import_angel_bundle()
            else:
                log(f"已检测到 bs_datasets={existing} 行，跳过自动导入（保留用户数据）")
    else:
        log("环境变量 SMARTASK_BOOTSTRAP_SKIP_DB=1，跳过 DB 初始化")

    log("========== Bootstrap 完成，启动 Flask ==========")

    # 直接 exec 到 app.py，避免子进程
    app_path = os.path.join(CURRENT_DIR, "app.py")
    os.execv(sys.executable, [sys.executable, app_path])


if __name__ == "__main__":
    main()

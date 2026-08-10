"""
SmartAsk one-shot database migrator.

Run as a Docker Compose ``migrate`` service (or manually) before the backend
container starts. Idempotent — safe to re-run on every deploy.

Order of operations (each step is best-effort unless marked fatal):
    1. Wait for PostgreSQL to become reachable     [fatal: exit 1]
    2. Initialise default JSON configs             [non-fatal]
       (init_default_configs only writes files that do not exist;
       existing user-edited config/*.json is preserved)
    3. Restore runtime config bundle               [non-fatal]
       (_import_runtime_config only fills missing config/*.json;
       set SMARTASK_BOOTSTRAP_FORCE_CONFIG=1 to overwrite)
    4. Apply schema migrations under backend/migrations
       Each migration is run with autocommit; the first failure aborts
       the run with a non-zero exit code.                        [fatal: exit 1]

Exits 0 on success and 1 on failure. Designed for ``depends_on:
service_completed_successfully`` wiring from the backend service.

This script deliberately does **not** touch user data:
- It never DELETEs from ``bs_datasets`` / ``bs_golden_sql_samples`` etc.
- It never auto-imports bundle fixtures (bookshelf / angel / ecommerce).
- It never re-runs ``_sync_builtin_datasets`` which would clobber
  golden sql / data dictionary / agent prompt / LLD edits.

Use ``backend/import_*.py`` or the Admin UI to migrate metadata explicitly.
"""
from __future__ import annotations

import os
import sys
import traceback
from typing import NoReturn

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

BASE_DIR = os.path.dirname(CURRENT_DIR)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(BASE_DIR, ".env"), override=False)
    load_dotenv(os.path.join(BASE_DIR, ".env.local"), override=True)
except Exception:
    # dotenv is optional; runtime config still loads via config_manager.
    pass

# Reuse shared helpers from bootstrap so behaviour stays identical to the
# legacy code path. These helpers are intentionally idempotent.
from bootstrap import (  # noqa: E402  (sys.path adjusted above)
    MIGRATIONS,
    _import_runtime_config,
    _run_migration,
    _wait_for_postgres,
)


def log(msg: str) -> None:
    print(f"[migrate] {msg}", flush=True)


# Route bootstrap helper logs through the [migrate] prefix so the entire
# migrate run is consistently tagged. bootstrap's _wait_for_postgres /
# _run_migration / _import_runtime_config call module-level log() internally,
# so reassigning bootstrap.log makes their output use [migrate] too.
import bootstrap as _bootstrap
_bootstrap.log = log


def _fail(msg: str) -> NoReturn:
    log(f"❌ {msg}")
    sys.exit(1)


def _run_default_config_init() -> None:
    """Create config/*.json defaults if missing (never overwrite)."""
    try:
        from config_manager import init_default_configs

        init_default_configs()
    except Exception as exc:
        log(f"初始化默认 JSON 配置失败（非致命）: {exc}")
        traceback.print_exc()


def _run_all_migrations() -> None:
    """Apply every migration in order; first failure aborts the run."""
    for migration in MIGRATIONS:
        try:
            _run_migration(migration)
        except Exception as exc:
            log(f"迁移 {migration} 失败: {exc}")
            traceback.print_exc()
            raise


def main() -> int:
    log("========== SmartAsk Migrate 开始 ==========")

    if not _wait_for_postgres():
        _fail("PostgreSQL 不可达，migrate 终止。请检查 postgres 服务状态与网络连通性。")

    _run_default_config_init()
    _import_runtime_config()

    try:
        _run_all_migrations()
    except Exception as exc:
        _fail(f"迁移过程出现致命错误: {exc}")

    log("========== SmartAsk Migrate 完成 ==========")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

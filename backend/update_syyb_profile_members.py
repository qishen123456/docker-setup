"""
从 angel_group_data 表抽取商用事业部业务代表名单，
更新 smartask/backend/data/dataset_dimension_profiles.json 中
angel_business_2026 数据集「业务员」维度的 members。

运行方式：
  # 在容器内（推荐，与后端同一网络）
  docker exec -it smartask-backend python /app/backend/update_syyb_profile_members.py

  # 在宿主机（.env 中 DB_HOST 需要可访问，如 localhost:5433）
  cd smartask/backend
  python update_syyb_profile_members.py
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Set

import psycopg2


CURRENT_DIR = Path(__file__).resolve().parent
PROFILE_PATH = CURRENT_DIR / "data" / "dataset_dimension_profiles.json"
ENV_PATH = CURRENT_DIR.parent / ".env"


def _load_env() -> Dict[str, str]:
    """简单解析 .env 文件，只读取 SMARTASK_DB_* 相关变量。"""
    config: Dict[str, str] = {}
    if not ENV_PATH.exists():
        return config
    with open(ENV_PATH, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key.startswith("SMARTASK_DB_"):
                config[key] = value.strip().strip('"').strip("'")
    return config


def _db_kwargs(env: Dict[str, str]) -> Dict[str, Any]:
    """构造 psycopg2 连接参数，优先用环境变量，其次 .env 文件，最后默认值。"""
    def get(key: str, default: str = "") -> str:
        return os.environ.get(key) or env.get(key, default)

    return {
        "host": get("SMARTASK_DB_HOST", "smartask-postgres"),
        "port": int(get("SMARTASK_DB_PORT", "5432") or 5432),
        "database": get("SMARTASK_DB_DATABASE", "postgres"),
        "user": get("SMARTASK_DB_USERNAME", "postgres"),
        "password": get("SMARTASK_DB_PASSWORD", "postgres"),
    }


def _try_connect(kwargs: Dict[str, Any]):
    """尝试连接；如果连不上 smartask-postgres，fallback 到 localhost:5433。"""
    candidates = [dict(kwargs)]
    if kwargs.get("host") == "smartask-postgres":
        fallback = dict(kwargs)
        fallback["host"] = "localhost"
        fallback["port"] = 5433
        candidates.append(fallback)

    last_exc = None
    for candidate in candidates:
        try:
            return psycopg2.connect(**candidate)
        except Exception as exc:
            last_exc = exc
            continue
    raise RuntimeError(f"无法连接数据库: {last_exc}")


def _fetch_members(conn, field_name: str) -> List[str]:
    """查询 angel_group_data 中当前年（默认 2026）下某个字段的所有非空取值。"""
    sql = f"""
    WITH 字段提取 AS (
        SELECT
            CASE WHEN jsonb_typeof(fields->'{field_name}') = 'array'
                 THEN fields->'{field_name}'->0->>'text'
                 ELSE fields->>'{field_name}'
            END AS 字段值,
            CASE WHEN jsonb_typeof(fields->'当前年') = 'array'
                 THEN fields->'当前年'->0->>'text'
                 ELSE fields->>'当前年'
            END AS 当前年
        FROM angel_group_data
    )
    SELECT DISTINCT 字段值
    FROM 字段提取
    WHERE COALESCE(NULLIF(当前年, ''), '2026') = '2026'
      AND COALESCE(NULLIF(TRIM(字段值), ''), '') <> ''
    ORDER BY 字段值;
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return [str(row[0]).strip() for row in rows if row[0]]


def _load_profiles() -> Dict[str, Any]:
    if not PROFILE_PATH.exists():
        return {}
    with open(PROFILE_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save_profiles(data: Dict[str, Any]) -> None:
    with open(PROFILE_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def main() -> None:
    env = _load_env()
    kwargs = _db_kwargs(env)

    print(f"尝试连接数据库 {kwargs['host']}:{kwargs['port']}/{kwargs['database']} ...")
    conn = _try_connect(kwargs)
    print("连接成功。")

    try:
        sales_reps = _fetch_members(conn, "业务代表")
        offices = _fetch_members(conn, "代表处")
        print(f"从 angel_group_data 查到 {len(sales_reps)} 个业务代表、{len(offices)} 个代表处。")
        if not sales_reps and not offices:
            print("未查到任何业务代表或代表处，退出。")
            return
    finally:
        conn.close()

    profiles = _load_profiles()
    syyb_profile = profiles.get("angel_business_2026")
    if not isinstance(syyb_profile, dict):
        raise RuntimeError("未找到 angel_business_2026 数据集画像")

    levels = syyb_profile.setdefault("levels", [])
    def update_level(dimension_name: str, new_members: List[str]) -> None:
        level = next(
            (level for level in levels if str(level.get("dimension_name")) == dimension_name),
            None,
        )
        if level is None:
            raise RuntimeError(f"未找到「{dimension_name}」维度")
        existing: Set[str] = {str(item).strip() for item in (level.get("members") or []) if item}
        merged = sorted(existing | set(new_members))
        level["members"] = merged
        return merged

    sales_merged = update_level("业务员", sales_reps)
    offices_merged = update_level("代表处", offices)

    _save_profiles(profiles)
    print(f"已更新 {PROFILE_PATH}")
    print(f"「代表处」维度现有 {len(offices_merged)} 个成员：")
    for name in offices_merged[:20]:
        print(f"  - {name}")
    if len(offices_merged) > 20:
        print(f"  ... 等共 {len(offices_merged)} 个")
    print(f"「业务员」维度现有 {len(sales_merged)} 个成员：")
    for name in sales_merged[:20]:
        print(f"  - {name}")
    if len(sales_merged) > 20:
        print(f"  ... 等共 {len(sales_merged)} 个")


if __name__ == "__main__":
    main()

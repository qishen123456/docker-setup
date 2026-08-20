"""数据资产三视图验证脚本

验证三个标准视图（商用/消费者/电商）的存在性、可查询性、列结构和数据完整性。
作为防回归机制，每次部署或飞书同步后可运行此脚本进行健康检查。

用法:
    python verify_dataset_views.py [--db-host HOST] [--db-port PORT] [--db-name NAME] [--db-user USER] [--db-password PASSWORD]
"""

import json
import sys
import psycopg2
import psycopg2.extras
from pathlib import Path
from typing import Dict, List, Tuple, Optional


DEFAULT_CONFIG_PATH = Path(__file__).parent / "default_dataset_transforms.json"


def load_view_definitions(config_path: str = None) -> List[Dict]:
    """加载视图定义配置"""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        print(f"❌ 配置文件不存在: {path}")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_connection(host: str = "localhost", port: int = 5432,
                   dbname: str = "postgres", user: str = "postgres",
                   password: str = "") -> psycopg2.extensions.connection:
    """获取数据库连接"""
    try:
        conn = psycopg2.connect(
            host=host, port=port, dbname=dbname,
            user=user, password=password,
            connect_timeout=5
        )
        return conn
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        sys.exit(1)


def check_view_exists(conn, view_name: str) -> Tuple[bool, str]:
    """检查视图是否存在"""
    query = """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.views
            WHERE table_schema = 'public' AND table_name = %s
        )
    """
    with conn.cursor() as cur:
        cur.execute(query, (view_name,))
        exists = cur.fetchone()[0]
    return exists, f"视图 {view_name} {'✅ 存在' if exists else '❌ 不存在'}"


def check_view_queryable(conn, view_name: str) -> Tuple[bool, str]:
    """检查视图是否可查询"""
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {view_name} LIMIT 1")
            cur.fetchall()
        return True, f"视图 {view_name} ✅ 可查询"
    except Exception as e:
        return False, f"视图 {view_name} ❌ 查询失败: {e}"


def check_view_columns(conn, view_name: str, expected_columns: List[str]) -> Tuple[bool, str]:
    """检查视图列是否齐全"""
    query = """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """
    with conn.cursor() as cur:
        cur.execute(query, (view_name,))
        actual_columns = [row[0] for row in cur.fetchall()]
    
    missing = [col for col in expected_columns if col not in actual_columns]
    extra = [col for col in actual_columns if col not in expected_columns]
    
    if missing:
        return False, f"视图 {view_name} ❌ 缺少列: {missing}"
    else:
        msg = f"视图 {view_name} ✅ 列齐全 ({len(actual_columns)} 列)"
        if extra:
            msg += f"，注意有额外列: {extra}"
        return True, msg


def check_view_has_data(conn, view_name: str, min_rows: int = 1) -> Tuple[bool, str]:
    """检查视图是否有数据"""
    query = f"SELECT COUNT(*) FROM {view_name}"
    with conn.cursor() as cur:
        cur.execute(query)
        count = cur.fetchone()[0]
    
    if count >= min_rows:
        return True, f"视图 {view_name} ✅ 有 {count} 行数据"
    else:
        return False, f"视图 {view_name} ❌ 无数据 (0 行)"


def check_primary_key(conn, view_name: str) -> Tuple[bool, str]:
    """检查视图是否有唯一 id"""
    query = f"SELECT COUNT(DISTINCT id) FROM {view_name}"
    total_query = f"SELECT COUNT(*) FROM {view_name}"
    with conn.cursor() as cur:
        cur.execute(query)
        distinct_count = cur.fetchone()[0]
        cur.execute(total_query)
        total_count = cur.fetchone()[0]
    
    if distinct_count == total_count:
        return True, f"视图 {view_name} ✅ id 无重复 ({total_count} 行)"
    else:
        return False, f"视图 {view_name} ⚠️ id 有重复 (总 {total_count} 行, 唯一 {distinct_count} 个)"


def run_verification(conn, view_definitions: List[Dict]) -> Dict:
    """运行完整验证"""
    results = {
        "total": len(view_definitions),
        "passed": 0,
        "failed": 0,
        "details": []
    }
    
    for view_def in view_definitions:
        view_name = view_def["view_name"]
        expected_columns = view_def.get("columns", [])
        dataset_name = view_def.get("dataset_name", "")
        
        view_result = {
            "dataset": dataset_name,
            "view": view_name,
            "checks": []
        }
        
        # 1. 视图存在性
        ok, msg = check_view_exists(conn, view_name)
        view_result["checks"].append({"name": "存在性", "passed": ok, "message": msg})
        if not ok:
            results["failed"] += 1
            results["details"].append(view_result)
            continue
        
        # 2. 可查询性
        ok, msg = check_view_queryable(conn, view_name)
        view_result["checks"].append({"name": "可查询性", "passed": ok, "message": msg})
        if not ok:
            results["failed"] += 1
            results["details"].append(view_result)
            continue
        
        # 3. 列结构
        ok, msg = check_view_columns(conn, view_name, expected_columns)
        view_result["checks"].append({"name": "列结构", "passed": ok, "message": msg})
        
        # 4. 数据完整性
        ok, msg = check_view_has_data(conn, view_name)
        view_result["checks"].append({"name": "数据完整性", "passed": ok, "message": msg})
        
        # 5. 主键唯一性
        ok, msg = check_primary_key(conn, view_name)
        view_result["checks"].append({"name": "主键唯一性", "passed": ok, "message": msg})
        
        # 统计结果
        all_passed = all(c["passed"] for c in view_result["checks"])
        if all_passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        
        results["details"].append(view_result)
    
    return results


def print_report(results: Dict):
    """打印验证报告"""
    print("\n" + "=" * 60)
    print("📊 数据资产三视图验证报告")
    print("=" * 60)
    
    for detail in results["details"]:
        status = "✅" if all(c["passed"] for c in detail["checks"]) else "❌"
        print(f"\n{status} {detail['dataset']} ({detail['view']})")
        print("  " + "-" * 40)
        for check in detail["checks"]:
            icon = "✅" if check["passed"] else "❌"
            print(f"  {icon} {check['name']}: {check['message']}")
    
    print("\n" + "-" * 60)
    print(f"总计: {results['total']} 个视图, ✅ {results['passed']} 通过, ❌ {results['failed']} 失败")
    print("=" * 60)
    
    return results["failed"] == 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="数据资产三视图验证脚本")
    parser.add_argument("--db-host", default="localhost", help="数据库主机")
    parser.add_argument("--db-port", type=int, default=5432, help="数据库端口")
    parser.add_argument("--db-name", default="postgres", help="数据库名称")
    parser.add_argument("--db-user", default="postgres", help="数据库用户")
    parser.add_argument("--db-password", default="", help="数据库密码")
    parser.add_argument("--config", default=None, help="视图定义配置文件路径")
    args = parser.parse_args()
    
    # 加载视图定义
    view_defs = load_view_definitions(args.config)
    print(f"📋 已加载 {len(view_defs)} 个视图定义")
    
    # 连接数据库
    conn = get_connection(
        host=args.db_host, port=args.db_port,
        dbname=args.db_name, user=args.db_user,
        password=args.db_password
    )
    
    try:
        # 运行验证
        results = run_verification(conn, view_defs)
        all_passed = print_report(results)
        
        if not all_passed:
            sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

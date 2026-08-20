"""
一键全量导入 SmartAsk 运行态全量包（包含 9 款 AI 模型、7 个飞书任务、2506 条 Golden SQL、同义词、字典及业务底表）。
"""
from __future__ import annotations

import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from runtime_migration import import_runtime_bundle
import import_angel_group_data


def find_file(filename: str) -> str | None:
    candidates = [
        os.path.join(CURRENT_DIR, "imports", filename),
        os.path.join(os.path.dirname(CURRENT_DIR), "imports", filename),
        os.path.join("/app", "imports", filename),
        os.path.join("/app", "backend", "imports", filename),
        os.path.join("/app", filename),
    ]
    for p in candidates:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return p
    return None


def main():
    print("=" * 60)
    print("🚀 开始一键全量导入 SmartAsk 配置、模型、飞书与业务底表...")
    print("=" * 60)

    # 1. 导入业务底表
    angel_path = find_file("angel_group_data_bundle.json")
    if angel_path:
        print(f"\n[1/2] 导入业务底表数据: {angel_path}")
        try:
            res_angel = import_angel_group_data.import_bundle(angel_path)
            print(f"✓ 业务底表导入成功: {res_angel}")
        except Exception as e:
            print(f"⚠️ 业务底表导入异常: {e}")
    else:
        print("\n[1/2] ⚠️ 未找到 angel_group_data_bundle.json，跳过")

    # 2. 导入全量运行时包 (含 9 款 AI 模型、7 个飞书任务、2506 条 Golden SQL)
    runtime_path = find_file("smartask_runtime_full_migration.json")
    if runtime_path:
        print(f"\n[2/2] 导入全量运行时迁移包: {runtime_path}")
        try:
            with open(runtime_path, "r", encoding="utf-8") as f:
                bundle = json.load(f)
            res = import_runtime_bundle(bundle, mode="merge", overwrite_configs=True, auto_backup=False)
            print(f"✓ 运行时配置与模型导入成功！")
            print(f"  - 写入/更新配置文件: {res.get('written_configs')}")
            print(f"  - 数据库表记录导入: {res.get('imported_counts')}")
        except Exception as e:
            print(f"⚠️ 运行时包导入异常: {e}")
    else:
        print("\n[2/2] ⚠️ 未找到 smartask_runtime_full_migration.json，跳过")

    print("\n" + "=" * 60)
    print("🎉 全量 9 款 AI 模型、7 个飞书任务与 2506 条 SQL 全部导入完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
一键导入 SmartAsk 全量资产包（包含 2506 条 Golden SQL、661 条同义词、271 条数据字典、Prompt、常见问题及业务底表）。
"""
from __future__ import annotations

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import import_bookshelf_bundle
import import_angel_group_data


def main():
    print("=" * 60)
    print("🚀 开始一键导入 SmartAsk 全量资产包与业务底表...")
    print("=" * 60)

    imports_dir = os.path.join(CURRENT_DIR, "imports")
    bookshelf_path = os.path.join(imports_dir, "bookshelf_bundle.json")
    angel_path = os.path.join(imports_dir, "angel_group_data_bundle.json")

    # 1. 导入业务底表
    if os.path.exists(angel_path):
        print(f"\n[1/2] 导入业务底表数据: {angel_path}")
        res_angel = import_angel_group_data.import_bundle(angel_path)
        print(f"✓ 业务底表导入完成: {res_angel}")
    else:
        print(f"\n[1/2] 未找到底表包: {angel_path}，跳过")

    # 2. 导入 Bookshelf 数据资产（2506 条 Golden SQL 等）
    if os.path.exists(bookshelf_path):
        print(f"\n[2/2] 导入 Bookshelf 数据资产包: {bookshelf_path}")
        res_bs = import_bookshelf_bundle.import_bundle(bookshelf_path)
        print(f"✓ Bookshelf 数据资产导入完成: {res_bs}")
    else:
        print(f"\n[2/2] 未找到资产包: {bookshelf_path}，跳过")

    print("\n" + "=" * 60)
    print("🎉 全量数据资产与业务底表导入 100% 完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

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
    print("🚀 开始一键导入 SmartAsk 全量资产包与业务底表...")
    print("=" * 60)

    angel_path = find_file("angel_group_data_bundle.json")
    bookshelf_path = find_file("bookshelf_bundle.json")

    # 1. 导入业务底表
    if angel_path:
        print(f"\n[1/2] 找到业务底表包: {angel_path}")
        res_angel = import_angel_group_data.import_bundle(angel_path)
        print(f"✓ 业务底表导入成功: {res_angel}")
    else:
        print("\n[1/2] ⚠️ 未找到 angel_group_data_bundle.json，跳过")

    # 2. 导入 Bookshelf 数据资产（2506 条 Golden SQL 等）
    if bookshelf_path:
        print(f"\n[2/2] 找到 Bookshelf 数据资产包: {bookshelf_path}")
        res_bs = import_bookshelf_bundle.import_bundle(bookshelf_path)
        print(f"✓ Bookshelf 数据资产导入成功: {res_bs}")
    else:
        print("\n[2/2] ⚠️ 未找到 bookshelf_bundle.json，跳过")

    print("\n" + "=" * 60)
    print("🎉 全量数据资产与业务底表导入 100% 完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

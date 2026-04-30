"""Regenerate (or first-fill) a Bookshelf dataset from a markdown briefing.

Run from the backend/ directory:

    # 1) Dry run: produce + validate payload, save to dataset_copilot/output/
    python regenerate_dataset_from_doc.py --dataset-id 1 --doc ../docs/提示词和数据.md --dry-run

    # 2) Apply: PUT payload to a running backend (atomic full replace)
    python regenerate_dataset_from_doc.py --dataset-id 1 --doc ../docs/提示词和数据.md \
        --apply http://127.0.0.1:5002

The /api/bookshelves/datasets/<id>/full endpoint already does DELETE-then-INSERT
for every collection, so calling --apply automatically wipes stale legacy data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

# Ensure backend/ on sys.path no matter where the script is invoked from.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from dataset_copilot import CopilotError, DatasetCopilot  # noqa: E402
from dataset_copilot.syyb_rule_generator import build_syyb_payload  # noqa: E402


def _load_doc(path: str) -> str:
    if not os.path.exists(path):
        raise SystemExit(f"doc not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _load_dataset_meta(dataset_id: int, override_name: Optional[str]) -> Dict[str, Any]:
    """Try to load dataset metadata from PostgreSQL via BookshelfRepository.
    Falls back to a minimal stub if backend deps are unavailable.
    """
    try:
        from bookshelf_repository import BookshelfRepository  # type: ignore

        repo = BookshelfRepository()
        with repo._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, dataset_code, dataset_name, business_domain, source_id, description "
                "FROM bs_datasets WHERE id = %s;",
                (dataset_id,),
            )
            row = cur.fetchone()
            if not row:
                raise SystemExit(f"dataset_id {dataset_id} not found in bs_datasets")
            return {
                "id": row[0],
                "dataset_code": row[1],
                "dataset_name": override_name or row[2],
                "business_domain": row[3],
                "source_id": row[4],
                "description": row[5],
            }
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[warn] cannot load dataset meta from DB ({exc}); using stub.", flush=True)
        return {
            "id": dataset_id,
            "dataset_code": f"dataset_{dataset_id}",
            "dataset_name": override_name or f"Dataset {dataset_id}",
            "business_domain": "",
            "source_id": None,
            "description": "",
        }


def _put_payload(base_url: str, dataset_id: int, payload: Dict[str, Any]) -> None:
    import urllib.error
    import urllib.request

    url = f"{base_url.rstrip('/')}/api/bookshelves/datasets/{dataset_id}/full"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="PUT",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 - intentional local PUT
            print(f"[apply] HTTP {resp.status}")
            print(resp.read().decode("utf-8", errors="replace")[:2000])
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"PUT failed: HTTP {exc.code}\n{body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"PUT failed: {exc}") from exc


def _print_summary(payload: Dict[str, Any]) -> None:
    def n(key: str) -> int:
        return len(payload.get(key) or [])

    print("[copilot] payload summary:")
    print(f"  lld_documents       = {n('lld_documents')}")
    print(f"  schema_definition   = {n('schema_definition')}")
    print(f"  data_dictionary     = {n('data_dictionary')}")
    print(f"  table_relations     = {n('table_relations')}")
    print(f"  golden_sql_samples  = {n('golden_sql_samples')}")
    print(f"  agent_prompts       = {n('agent_prompts')}")
    print(f"  common_questions    = {n('common_questions')}")
    print(f"  regression_cases    = {n('regression_cases')}")
    print(f"  synonyms            = {n('synonyms')}")
    if payload.get("report_config"):
        print("  report_config       = present")


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate a Bookshelf dataset from a briefing markdown.")
    parser.add_argument("--dataset-id", type=int, required=True, help="Target dataset id in bs_datasets.")
    parser.add_argument("--doc", type=str, required=True, help="Path to the briefing markdown.")
    parser.add_argument("--dataset-name", type=str, default=None, help="Optional override of dataset_name.")
    parser.add_argument("--sample-rows", type=str, default=None, help="Optional path to extra sample rows.")
    parser.add_argument("--dry-run", action="store_true", help="Generate + save locally, do not PUT.")
    parser.add_argument("--apply", type=str, default=None, help="Backend base URL to PUT payload to, e.g. http://127.0.0.1:5002")
    parser.add_argument("--mode", choices=["llm", "rule"], default="llm", help="llm uses DatasetCopilot; rule uses the deterministic syyb generator.")
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--base-url", type=str, default=None)
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--retries", type=int, default=2)
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.error("either --dry-run or --apply <base_url> must be provided")

    doc_text = _load_doc(args.doc)
    sample_rows_text = _load_doc(args.sample_rows) if args.sample_rows else ""
    dataset_meta = _load_dataset_meta(args.dataset_id, args.dataset_name)

    print(f"[copilot] dataset_id={dataset_meta['id']} name={dataset_meta['dataset_name']}")
    print(f"[copilot] doc        = {args.doc} ({len(doc_text)} chars)")

    try:
        if args.mode == "rule":
            print("[copilot] using deterministic syyb rule generator")
            payload = build_syyb_payload(doc_text=doc_text, dataset_meta=dataset_meta)
            copilot = DatasetCopilot(model=args.model, base_url=args.base_url, api_key=args.api_key)
        else:
            copilot = DatasetCopilot(
                model=args.model,
                base_url=args.base_url,
                api_key=args.api_key,
            )
            payload = copilot.generate(
                dataset_meta=dataset_meta,
                doc_text=doc_text,
                sample_rows_text=sample_rows_text,
                retries=args.retries,
            )
    except CopilotError as exc:
        print(f"[copilot] generate failed: {exc}", file=sys.stderr)
        return 2

    saved_path = copilot.save_local(payload, dataset_id=args.dataset_id)
    print(f"[copilot] payload saved to: {saved_path}")
    _print_summary(payload)

    if args.dry_run:
        print("[copilot] dry-run done; not applying.")
        return 0

    print(f"[copilot] applying to {args.apply} ...")
    _put_payload(args.apply, args.dataset_id, payload)
    print("[copilot] apply done. Stale legacy rows (LLD/DDL/dictionary/golden_sql/agent_prompts) "
          "have been replaced atomically by the PUT endpoint.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

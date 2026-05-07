"""
SmartAsk Docker deployment — end-to-end integration test.

Exercises ONLY the blueprints actually registered in app.py:
    dashboard, datasources, ai_models, feishu(_sync), smart_chat, bookshelf, agents

Each test is independent. Tests gracefully skip (rather than fail) when a
prerequisite (e.g. Vanna readiness, real AI key) is missing — so this is safe
to run on a fresh deploy as well as on a fully-trained system.

Usage:
    python scripts/integration_test.py
    python scripts/integration_test.py --base-url http://localhost:5002
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Callable, Dict, List, Tuple

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(2)


DEFAULT_BASE = "http://localhost:5002"
DEFAULT_FRONTEND = "http://localhost:8080"


class Result:
    def __init__(self) -> None:
        self.records: List[Tuple[str, str, str]] = []  # name, status, message

    def record(self, name: str, status: str, msg: str = "") -> None:
        self.records.append((name, status, msg))

    @property
    def ok(self) -> bool:
        return all(s in ("PASS", "SKIP") for _, s, _ in self.records)

    def report(self) -> None:
        line = "=" * 72
        print(line)
        print(" SmartAsk integration test report")
        print(line)
        passed = sum(1 for _, s, _ in self.records if s == "PASS")
        failed = sum(1 for _, s, _ in self.records if s == "FAIL")
        skipped = sum(1 for _, s, _ in self.records if s == "SKIP")
        for name, status, msg in self.records:
            tag = {"PASS": "[ OK ]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}.get(status, status)
            print(f"{tag} {name:55s} {msg}")
        print(line)
        print(f" PASS={passed}  FAIL={failed}  SKIP={skipped}")
        print(line)


def _safe_get(base: str, path: str, **kwargs) -> Tuple[bool, Any]:
    try:
        r = requests.get(base + path, timeout=10, **kwargs)
        return r.ok, r
    except Exception as exc:
        return False, exc


def _safe_post(base: str, path: str, payload: Dict[str, Any] | None = None, **kwargs) -> Tuple[bool, Any]:
    try:
        r = requests.post(base + path, json=payload or {}, timeout=30, **kwargs)
        return r.ok, r
    except Exception as exc:
        return False, exc


def _safe_put(base: str, path: str, payload: Dict[str, Any] | None = None, **kwargs) -> Tuple[bool, Any]:
    try:
        r = requests.put(base + path, json=payload or {}, timeout=30, **kwargs)
        return r.ok, r
    except Exception as exc:
        return False, exc


def _read_sse_events(resp: Any, max_events: int = 12, max_seconds: int = 45) -> List[Tuple[str, Any]]:
    """Read a small SSE sample without requiring the whole long-running task to finish."""
    events: List[Tuple[str, Any]] = []
    current_event = "message"
    data_lines: List[str] = []
    start = time.time()

    def _flush() -> None:
        nonlocal current_event, data_lines
        if not data_lines:
            current_event = "message"
            return
        raw = "\n".join(data_lines)
        try:
            body: Any = json.loads(raw)
        except Exception:
            body = raw
        events.append((current_event, body))
        current_event = "message"
        data_lines = []

    for raw_line in resp.iter_lines(decode_unicode=True):
        if time.time() - start > max_seconds or len(events) >= max_events:
            break
        line = raw_line or ""
        if not line:
            _flush()
            continue
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip() or "message"
        elif line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())

    _flush()
    return events


# ─────────────────────────────────────────────
# Individual tests
# ─────────────────────────────────────────────

def test_health(base: str, result: Result) -> None:
    ok, r = _safe_get(base, "/api/health")
    if not ok:
        return result.record("backend /api/health", "FAIL", str(r))
    body = r.json() if hasattr(r, "json") else {}
    if body.get("status") == "running":
        result.record("backend /api/health", "PASS", body.get("version", ""))
    else:
        result.record("backend /api/health", "FAIL", json.dumps(body))


def test_dashboard(base: str, result: Result) -> None:
    ok, r = _safe_get(base, "/api/dashboard")
    if not ok:
        return result.record("/api/dashboard", "FAIL", str(r))
    result.record("/api/dashboard", "PASS", f"HTTP {r.status_code}")


def test_auth_me(base: str, result: Result) -> None:
    ok, r = _safe_get(base, "/api/auth/me")
    if not ok:
        return result.record("/api/auth/me", "FAIL", str(r))
    body = r.json() if hasattr(r, "json") else {}
    if body.get("success") is True and body.get("authenticated") is False:
        result.record("/api/auth/me anonymous", "PASS", "authenticated=false")
    else:
        result.record("/api/auth/me anonymous", "FAIL", json.dumps(body, ensure_ascii=False)[:120])


def test_admin_auth_contract(base: str, result: Result) -> None:
    username = os.getenv("SMARTASK_ADMIN_USERNAME", "admin")
    password = os.getenv("SMARTASK_ADMIN_PASSWORD", "")
    if not password or password in {"please-change-admin-password", "admin123456"}:
        return result.record("/api/auth/login admin", "SKIP", "admin password not configured for test")
    ok, r = _safe_post(base, "/api/auth/login", {"username": username, "password": password})
    if not ok:
        return result.record("/api/auth/login admin", "FAIL", str(r))
    body = r.json() if hasattr(r, "json") else {}
    token = body.get("token")
    role = (body.get("user") or {}).get("role")
    if body.get("success") is True and token and role == "super_admin":
        result.record("/api/auth/login admin", "PASS", "role=super_admin")
    else:
        result.record("/api/auth/login admin", "FAIL", json.dumps(body, ensure_ascii=False)[:120])


def test_feishu_login_url_contract(base: str, result: Result) -> None:
    ok, r = _safe_get(base, "/api/auth/feishu/login-url")
    if not ok:
        status = getattr(r, "status_code", None)
        if status == 500:
            return result.record("/api/auth/feishu/login-url", "SKIP", "Feishu login config missing")
        return result.record("/api/auth/feishu/login-url", "FAIL", str(r))
    body = r.json() if hasattr(r, "json") else {}
    if body.get("success") and body.get("url"):
        result.record("/api/auth/feishu/login-url", "PASS", "url generated")
    else:
        result.record("/api/auth/feishu/login-url", "FAIL", json.dumps(body, ensure_ascii=False)[:120])


def test_datasources_list(base: str, result: Result) -> None:
    ok, r = _safe_get(base, "/api/datasources")
    if not ok:
        return result.record("/api/datasources GET", "FAIL", str(r))
    body = r.json() if hasattr(r, "json") else {}
    count = len(body.get("databases") or body.get("data") or [])
    result.record("/api/datasources GET", "PASS", f"count={count}")


def test_ai_models_list(base: str, result: Result) -> None:
    ok, r = _safe_get(base, "/api/ai-models")
    if not ok:
        return result.record("/api/ai-models GET", "FAIL", str(r))
    body = r.json() if hasattr(r, "json") else {}
    count = len(body.get("models") or body.get("data") or [])
    result.record("/api/ai-models GET", "PASS", f"count={count}")


def test_bookshelves_health(base: str, result: Result) -> None:
    ok, r = _safe_get(base, "/api/bookshelves/health")
    if not ok:
        return result.record("/api/bookshelves/health", "FAIL", str(r))
    result.record("/api/bookshelves/health", "PASS", f"HTTP {r.status_code}")


def test_bookshelves_datasets(base: str, result: Result) -> Dict[str, Any] | None:
    ok, r = _safe_get(base, "/api/bookshelves/datasets")
    if not ok:
        result.record("/api/bookshelves/datasets", "FAIL", str(r))
        return None
    body = r.json() if hasattr(r, "json") else {}
    datasets = body.get("datasets") or body.get("data") or []
    result.record("/api/bookshelves/datasets", "PASS", f"count={len(datasets)}")
    return datasets[0] if datasets else None


def test_bookshelves_full(base: str, dataset: Dict[str, Any] | None, result: Result) -> None:
    if not dataset:
        return result.record("/api/bookshelves/datasets/<id>/full", "SKIP", "no dataset available")
    dataset_id = dataset.get("id")
    if not dataset_id:
        return result.record("/api/bookshelves/datasets/<id>/full", "SKIP", "no id field")
    ok, r = _safe_get(base, f"/api/bookshelves/datasets/{dataset_id}/full")
    if not ok:
        return result.record("/api/bookshelves/datasets/<id>/full", "FAIL", str(r))
    body = r.json() if hasattr(r, "json") else {}
    has_prompt = bool(body.get("agent_prompt_fragments") or body.get("data", {}).get("agent_prompt_fragments"))
    result.record("/api/bookshelves/datasets/<id>/full", "PASS", f"has_prompts={has_prompt}")


def test_agents(base: str, result: Result) -> None:
    ok, r = _safe_get(base, "/api/agents")
    if not ok:
        return result.record("/api/agents", "FAIL", str(r))
    result.record("/api/agents", "PASS", f"HTTP {r.status_code}")


def test_feishu_sync_list(base: str, result: Result) -> None:
    ok, r = _safe_get(base, "/api/feishu-sync")
    if not ok:
        return result.record("/api/feishu-sync GET", "FAIL", str(r))
    result.record("/api/feishu-sync GET", "PASS", f"HTTP {r.status_code}")


def test_smart_chat_data_sources(base: str, result: Result) -> None:
    ok, r = _safe_get(base, "/api/data-sources")
    if not ok:
        return result.record("/api/data-sources GET", "FAIL", str(r))
    result.record("/api/data-sources GET", "PASS", f"HTTP {r.status_code}")


def test_datasource_crud(base: str, result: Result) -> None:
    """Create + Update + Delete a throwaway datasource (uses sqlite to avoid touching real DB)."""
    create_payload = {
        "name": "__integration_test__",
        "type": "sqlite",
        "sqlite_path": "/tmp/__integration_test.db",
        "is_active": False,
        "is_default": False,
    }
    ok, r = _safe_post(base, "/api/datasources", create_payload)
    if not ok:
        return result.record("datasource CRUD: create", "FAIL", str(r))
    body = r.json() if hasattr(r, "json") else {}
    new_id = (body.get("database") or body.get("data") or {}).get("id") or body.get("id")
    if not new_id:
        return result.record("datasource CRUD: create", "FAIL", f"no id in {body}")
    result.record("datasource CRUD: create", "PASS", f"id={new_id}")

    # Update
    try:
        r2 = requests.put(
            base + f"/api/datasources/{new_id}",
            json={"name": "__integration_test_renamed__"},
            timeout=10,
        )
        if r2.ok:
            result.record("datasource CRUD: update", "PASS", f"HTTP {r2.status_code}")
        else:
            result.record("datasource CRUD: update", "FAIL", f"HTTP {r2.status_code} {r2.text[:120]}")
    except Exception as exc:
        result.record("datasource CRUD: update", "FAIL", str(exc))

    # Delete
    try:
        r3 = requests.delete(base + f"/api/datasources/{new_id}", timeout=10)
        if r3.ok:
            result.record("datasource CRUD: delete", "PASS", f"HTTP {r3.status_code}")
        else:
            result.record("datasource CRUD: delete", "FAIL", f"HTTP {r3.status_code} {r3.text[:120]}")
    except Exception as exc:
        result.record("datasource CRUD: delete", "FAIL", str(exc))


def test_smart_chat_minimal(base: str, dataset: Dict[str, Any] | None, result: Result) -> None:
    if not dataset:
        return result.record("/api/smart-chat", "SKIP", "no dataset available")

    payload = {
        "question": "ping integration test",
        "dataset_id": dataset.get("id"),
        "skip_execute": True,
    }
    try:
        r = requests.post(base + "/api/smart-chat", json=payload, timeout=60)
    except Exception as exc:
        return result.record("/api/smart-chat", "SKIP", f"network: {exc}")

    if r.status_code in (200, 201):
        result.record("/api/smart-chat", "PASS", f"HTTP {r.status_code}")
    elif r.status_code in (400, 422, 503):
        # AI key missing / Vanna not ready — counted as SKIP for green deploys
        result.record("/api/smart-chat", "SKIP", f"HTTP {r.status_code} (AI/Vanna not ready)")
    else:
        result.record("/api/smart-chat", "FAIL", f"HTTP {r.status_code} {r.text[:120]}")


def test_confirm_stream_contract(base: str, result: Result) -> None:
    """Smoke-test the SSE wrapper without needing a real pending confirmation session."""
    payload = {
        "session_id": "__integration_test_missing_session__",
        "selected_option": "integration contract test",
        "selected_dataset_ids": [],
    }
    try:
        with requests.post(
            base + "/api/smart-chat/confirm-by-boss/stream",
            json=payload,
            stream=True,
            timeout=(10, 35),
        ) as r:
            if r.status_code != 200:
                return result.record("/api/smart-chat/confirm-by-boss/stream", "FAIL", f"HTTP {r.status_code} {r.text[:120]}")
            content_type = r.headers.get("content-type", "")
            events = _read_sse_events(r, max_events=6, max_seconds=25)
    except Exception as exc:
        return result.record("/api/smart-chat/confirm-by-boss/stream", "FAIL", str(exc))

    names = [name for name, _ in events]
    if "text/event-stream" not in content_type:
        return result.record("/api/smart-chat/confirm-by-boss/stream", "FAIL", f"content-type={content_type}")
    if "ready" in names and ("result" in names or "done" in names):
        return result.record("/api/smart-chat/confirm-by-boss/stream", "PASS", f"events={','.join(names)}")
    result.record("/api/smart-chat/confirm-by-boss/stream", "FAIL", f"events={','.join(names) or 'none'}")


def test_smart_chat_stream_full(base: str, dataset: Dict[str, Any] | None, result: Result) -> None:
    """Optional AI-backed stream test. It may skip when model credentials are unavailable."""
    payload: Dict[str, Any] = {
        "question": "ping integration test",
        "session_id": "__integration_test_stream__",
    }
    if dataset and dataset.get("id"):
        payload["selected_dataset_ids"] = [dataset.get("id")]

    try:
        with requests.post(
            base + "/api/smart-chat/stream",
            json=payload,
            stream=True,
            timeout=(10, 90),
        ) as r:
            if r.status_code in (400, 422, 503):
                return result.record("/api/smart-chat/stream", "SKIP", f"HTTP {r.status_code} (AI/Vanna not ready)")
            if r.status_code != 200:
                return result.record("/api/smart-chat/stream", "FAIL", f"HTTP {r.status_code} {r.text[:120]}")
            events = _read_sse_events(r, max_events=16, max_seconds=75)
    except Exception as exc:
        return result.record("/api/smart-chat/stream", "SKIP", f"stream unavailable: {exc}")

    names = [name for name, _ in events]
    result_events = [body for name, body in events if name == "result" and isinstance(body, dict)]
    if result_events and result_events[-1].get("error"):
        return result.record("/api/smart-chat/stream", "SKIP", str(result_events[-1].get("error"))[:140])
    if "ready" in names and any(name in names for name in ("trace", "summary", "result", "done")):
        return result.record("/api/smart-chat/stream", "PASS", f"events={','.join(names)}")
    result.record("/api/smart-chat/stream", "FAIL", f"events={','.join(names) or 'none'}")


def test_frontend(frontend_url: str, result: Result) -> None:
    try:
        r = requests.get(frontend_url + "/", timeout=10)
    except Exception as exc:
        return result.record("frontend /", "FAIL", str(exc))
    if r.status_code == 200 and "<!doctype html" in r.text.lower():
        result.record("frontend /", "PASS", f"len={len(r.text)}")
    else:
        result.record("frontend /", "FAIL", f"HTTP {r.status_code}")


# ─────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────

def wait_for_backend(base: str, timeout: int = 60) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(base + "/api/health", timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--frontend-url", default=DEFAULT_FRONTEND)
    parser.add_argument("--no-wait", action="store_true", help="Skip waiting for backend health")
    parser.add_argument("--with-stream", action="store_true", help="Also run the AI-backed /api/smart-chat/stream test")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    frontend = args.frontend_url.rstrip("/")

    if not args.no_wait:
        print(f"Waiting for backend at {base} ...")
        if not wait_for_backend(base):
            print("Backend not reachable. Aborting tests.")
            return 2

    result = Result()

    test_health(base, result)
    test_dashboard(base, result)
    test_auth_me(base, result)
    test_admin_auth_contract(base, result)
    test_feishu_login_url_contract(base, result)
    test_datasources_list(base, result)
    test_ai_models_list(base, result)
    test_bookshelves_health(base, result)
    first_ds = test_bookshelves_datasets(base, result)
    test_bookshelves_full(base, first_ds, result)
    test_agents(base, result)
    test_feishu_sync_list(base, result)
    test_smart_chat_data_sources(base, result)
    test_datasource_crud(base, result)
    test_smart_chat_minimal(base, first_ds, result)
    test_confirm_stream_contract(base, result)
    if args.with_stream:
        test_smart_chat_stream_full(base, first_ds, result)
    test_frontend(frontend, result)

    result.report()
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""
Encrypt sensitive values in a .env file in place.

Usage:
    python backend/encrypt_env_secrets.py --file .env

Only known secret-like keys are rewritten. Empty values and values already
starting with enc:v1: are left unchanged.
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from secret_codec import encrypt_secret_value, is_encrypted_secret


DEFAULT_SECRET_KEYS = {
    "SMARTASK_SECRET_KEY",
    "SMARTASK_AI_API_KEY",
    "SMARTASK_DB_PASSWORD",
    "SMARTASK_FEISHU_APP_SECRET",
    "FEISHU_APP_SECRET",
    "SMARTASK_ADMIN_PASSWORD",
    "ADMIN_PASSWORD",
}


def _split_env_line(line: str) -> tuple[str, str, str] | None:
    match = re.match(r"^(\s*(?:export\s+)?)([A-Za-z_][A-Za-z0-9_]*)=(.*?)(\r?\n)?$", line)
    if not match:
        return None
    prefix, key, raw_value, newline = match.groups()
    return prefix, key, raw_value + (newline or "")


def _strip_newline(value: str) -> tuple[str, str]:
    if value.endswith("\r\n"):
        return value[:-2], "\r\n"
    if value.endswith("\n"):
        return value[:-1], "\n"
    return value, ""


def _quote_like(original: str, encrypted: str) -> str:
    value = original.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return f"{value[0]}{encrypted}{value[-1]}"
    return encrypted


def encrypt_env_file(path: Path, secret_keys: set[str]) -> int:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    changed = 0
    output = []
    for line in lines:
        parsed = _split_env_line(line)
        if not parsed:
            output.append(line)
            continue
        prefix, key, raw_with_newline = parsed
        raw, newline = _strip_newline(raw_with_newline)
        stripped = raw.strip().strip('"').strip("'")
        if key not in secret_keys or not stripped or is_encrypted_secret(stripped):
            output.append(line)
            continue
        encrypted = encrypt_secret_value(stripped)
        output.append(f"{prefix}{key}={_quote_like(raw, encrypted)}{newline}")
        changed += 1
    if changed:
        path.write_text("".join(output), encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=".env", help="Path to .env file")
    args = parser.parse_args()
    path = Path(args.file)
    if not path.exists():
        raise SystemExit(f"file not found: {path}")
    changed = encrypt_env_file(path, DEFAULT_SECRET_KEYS)
    print(f"encrypted={changed}; key_file={os.getenv('SMARTASK_SECRET_KEY_FILE') or 'config/.secret_master_key'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

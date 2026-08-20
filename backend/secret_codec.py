"""
Small encrypted-secret helper for local/runtime configuration.

Values with the ``enc:v1:`` prefix are decrypted at read time. Plain values are
returned unchanged so existing .env files and legacy base64 JSON configs keep
working during rollout.
"""
from __future__ import annotations

import base64
import getpass
import hashlib
import hmac
import os
import secrets
import sys
from pathlib import Path


SECRET_PREFIX = "enc:v1:"
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent
DEFAULT_KEY_FILE = BASE_DIR / "config" / ".secret_master_key"


def is_encrypted_secret(value: str | None) -> bool:
    return str(value or "").strip().startswith(SECRET_PREFIX)


def _key_file_path() -> Path:
    custom = os.getenv("SMARTASK_SECRET_KEY_FILE")
    if custom:
        return Path(custom)
    # 统一收敛：优先查找 config 目录下的主密钥文件
    candidates = [
        BASE_DIR / "config" / ".secret_master_key",
        BASE_DIR / "config" / "secret_master_key",
        BASE_DIR / ".secret_master_key",
        BASE_DIR / "secret_master_key",
    ]
    for p in candidates:
        if p.exists() and p.read_text(encoding="utf-8").strip():
            return p
    return candidates[0]


def _read_master_key(*, create: bool = False) -> str:
    env_key = os.getenv("SMARTASK_SECRET_MASTER_KEY")
    if env_key:
        return env_key.strip()

    key_path = _key_file_path()
    if key_path.exists() and key_path.read_text(encoding="utf-8").strip():
        return key_path.read_text(encoding="utf-8").strip()

    if not create:
        raise RuntimeError(
            "缺少密钥文件，无法解密 enc:v1 密文。请设置 SMARTASK_SECRET_MASTER_KEY "
            f"或创建 {key_path}"
        )

    key_path.parent.mkdir(parents=True, exist_ok=True)
    key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")
    key_path.write_text(key + "\n", encoding="utf-8")
    return key


def _master_bytes(*, create: bool = False) -> bytes:
    return hashlib.sha256(_read_master_key(create=create).encode("utf-8")).digest()


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64_decode(value: str) -> bytes:
    text = str(value or "").strip()
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + padding).encode("ascii"))


def _keystream(key: bytes, salt: bytes, length: int) -> bytes:
    blocks = []
    counter = 0
    while sum(len(block) for block in blocks) < length:
        blocks.append(hmac.new(key, salt + counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    return b"".join(blocks)[:length]


def encrypt_secret_value(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    if is_encrypted_secret(text):
        return text
    key = _master_bytes(create=True)
    salt = secrets.token_bytes(16)
    plain = text.encode("utf-8")
    stream = _keystream(key, salt, len(plain))
    cipher = bytes(left ^ right for left, right in zip(plain, stream))
    tag = hmac.new(key, salt + cipher, hashlib.sha256).digest()[:16]
    return SECRET_PREFIX + _b64_encode(salt + tag + cipher)


def decrypt_secret_value(value: str) -> str:
    text = str(value or "").strip()
    if not text or not is_encrypted_secret(text):
        return text
    key = _master_bytes(create=False)
    payload = _b64_decode(text[len(SECRET_PREFIX):])
    if len(payload) < 32:
        raise ValueError("密文格式不正确")
    salt, tag, cipher = payload[:16], payload[16:32], payload[32:]
    expected = hmac.new(key, salt + cipher, hashlib.sha256).digest()[:16]
    if not hmac.compare_digest(tag, expected):
        raise ValueError("密文校验失败，可能使用了错误的主密钥")
    stream = _keystream(key, salt, len(cipher))
    plain = bytes(left ^ right for left, right in zip(cipher, stream))
    return plain.decode("utf-8")


def main() -> int:
    action = (sys.argv[1] if len(sys.argv) > 1 else "encrypt").strip().lower()
    if action not in {"encrypt", "decrypt"}:
        print("Usage: python backend/secret_codec.py [encrypt|decrypt] [value]", file=sys.stderr)
        return 2
    value = sys.argv[2] if len(sys.argv) > 2 else getpass.getpass("Secret: ")
    if action == "encrypt":
        print(encrypt_secret_value(value))
    else:
        print(decrypt_secret_value(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

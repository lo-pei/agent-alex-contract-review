"""本地密文盒：第三方 API Key 的静态保护（ADR-013）。

角色：账号体系允许用户自带模型 Key；Key 只能以密文落盘，任何接口都不回传明文。
依赖：标准库（`hmac` / `hashlib` / `secrets` / `base64`），不引入新的加密依赖。
约束：
- 不是 KMS：主密钥保存在本机 `.data/secret.key`，只适合单机/单租户演示；
- 构造：HMAC-SHA256 计数器模式生成密钥流（XOR 加密）+ HMAC-SHA256 完整性标签；
- 密文格式 `v1:<base64url(nonce | tag | ciphertext)>`，任何字段不完整都视为解密失败；
- 解密失败（主密钥更换/密文被篡改）返回异常，由调用方按“未配置 Key”降级，绝不静默使用。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from pathlib import Path

VERSION = "v1"
NONCE_BYTES = 16
TAG_BYTES = 32
MASTER_KEY_BYTES = 32

_ENC_LABEL = b"agent-alex-secretbox-enc-v1"
_MAC_LABEL = b"agent-alex-secretbox-mac-v1"


class SecretBoxError(RuntimeError):
    """主密钥缺失/损坏，或密文无法解密。"""


def load_or_create_master_key(path: str | Path) -> bytes:
    """读取主密钥；不存在时生成 32 字节随机密钥并以 0600 写入。"""
    target = Path(path)
    if target.exists():
        raw = target.read_bytes()
        if len(raw) != MASTER_KEY_BYTES:
            raise SecretBoxError(
                f"主密钥长度异常（{len(raw)} 字节，应为 {MASTER_KEY_BYTES}）；"
                "删除该文件会使用户已保存的 API Key 失效。"
            )
        return raw

    target.parent.mkdir(parents=True, exist_ok=True)
    raw = secrets.token_bytes(MASTER_KEY_BYTES)
    tmp = target.with_name(target.name + ".tmp")
    descriptor = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(raw)
    os.replace(tmp, target)
    try:  # Windows 上 chmod 只影响只读位；POSIX 上确保 0600
        target.chmod(0o600)
    except OSError:  # pragma: no cover - 权限设置失败不阻塞启动
        pass
    return raw


def _split_keys(master_key: bytes) -> tuple[bytes, bytes]:
    if len(master_key) != MASTER_KEY_BYTES:
        raise SecretBoxError("主密钥长度必须是 32 字节")
    enc_key = hmac.new(master_key, _ENC_LABEL, hashlib.sha256).digest()
    mac_key = hmac.new(master_key, _MAC_LABEL, hashlib.sha256).digest()
    return enc_key, mac_key


def _keystream(enc_key: bytes, nonce: bytes, length: int) -> bytes:
    chunks = bytearray()
    counter = 0
    while len(chunks) < length:
        block = hmac.new(enc_key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        chunks.extend(block)
        counter += 1
    return bytes(chunks[:length])


def encrypt(plaintext: str, master_key: bytes) -> str:
    """加密 UTF-8 字符串，返回可入库的 ASCII 密文。"""
    data = plaintext.encode("utf-8")
    nonce = secrets.token_bytes(NONCE_BYTES)
    enc_key, mac_key = _split_keys(master_key)
    stream = _keystream(enc_key, nonce, len(data))
    ciphertext = bytes(left ^ right for left, right in zip(data, stream, strict=True))
    tag = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    payload = base64.urlsafe_b64encode(nonce + tag + ciphertext).decode("ascii")
    return f"{VERSION}:{payload}"


def decrypt(token: str, master_key: bytes) -> str:
    """解密；版本/长度/标签任一不符都抛 `SecretBoxError`。"""
    try:
        version, payload = token.split(":", 1)
    except ValueError as exc:
        raise SecretBoxError("密文格式不正确") from exc
    if version != VERSION:
        raise SecretBoxError(f"不支持的密文版本：{version}")

    try:
        raw = base64.urlsafe_b64decode(payload.encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise SecretBoxError("密文不是合法的 base64url") from exc
    if len(raw) < NONCE_BYTES + TAG_BYTES:
        raise SecretBoxError("密文长度不足")

    nonce = raw[:NONCE_BYTES]
    tag = raw[NONCE_BYTES : NONCE_BYTES + TAG_BYTES]
    ciphertext = raw[NONCE_BYTES + TAG_BYTES :]
    enc_key, mac_key = _split_keys(master_key)
    expected = hmac.new(mac_key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise SecretBoxError("密文校验失败（主密钥已更换或被篡改）")

    stream = _keystream(enc_key, nonce, len(ciphertext))
    plaintext = bytes(left ^ right for left, right in zip(ciphertext, stream, strict=True))
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:  # pragma: no cover - 只有篡改才可能触发
        raise SecretBoxError("密文不是合法的 UTF-8") from exc

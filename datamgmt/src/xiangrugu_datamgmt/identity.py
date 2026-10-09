"""Versioned SHA-256 identities over unambiguous UTF-8 canonical inputs."""
import hashlib
import json
import re


def canonical_relative_path(value: str) -> str:
    if not value or "\x00" in value or "\\" in value or value.startswith("/"):
        raise ValueError("A canonical POSIX relative path is required")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("Noncanonical or escaping path")
    return value


def valid_digest(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("A lowercase SHA-256 digest is required")
    return value


def hash_identity(parts: list) -> str:
    encoded = json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def member_id(*, release_id: str, relative_path: str, archive_chain: tuple[str, ...] | list[str], sha256: str) -> str:
    if not release_id or "\x00" in release_id:
        raise ValueError("A source release is required")
    path = canonical_relative_path(relative_path)
    chain = [canonical_relative_path(member) for member in archive_chain]
    return hash_identity(["xiangrugu.source-member.v1", release_id, path, chain, valid_digest(sha256)])


def source_object_id(*, relative_path: str, archive_chain: tuple[str, ...] | list[str], object_name: str, carrier: str) -> str:
    if not carrier or "\x00" in carrier or "\x00" in object_name:
        raise ValueError("An object name and carrier without NUL are required")
    path = canonical_relative_path(relative_path)
    chain = [canonical_relative_path(member) for member in archive_chain]
    return hash_identity(["xiangrugu.source-object.v1", path, chain, object_name, carrier])

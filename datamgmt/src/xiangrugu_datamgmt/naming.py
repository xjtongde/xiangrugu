"""Deterministic PostgreSQL names, with immutable original-name mappings."""
from collections import Counter
from dataclasses import dataclass
import unicodedata

from .identity import hash_identity, valid_digest


@dataclass(frozen=True)
class NameInput:
    dataset: str
    original: str
    identity: str


@dataclass(frozen=True)
class NameMap:
    dataset: str
    original: str
    identity: str
    target: str
    ordinal: int | None = None


def slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    result = "".join(char.lower() if char.isascii() and char.isalnum() else f"_u{ord(char):x}_" for char in normalized)
    if not result or not ("a" <= result[0] <= "z"):
        result = "t_" + result
    return result


def limited(base: str, identity: str, *, force_hash: bool = False, suffix: str = "") -> str:
    valid_digest(identity)
    if force_hash or len(base + suffix) > 63:
        tail = "__" + identity[:8] + suffix
        return base[:63 - len(tail)] + tail
    return base + suffix


def allocate_tables(entries: list[NameInput]) -> tuple[NameMap, ...]:
    bases = [slug(entry.dataset) + "__" + slug(entry.original) for entry in entries]
    counts = Counter(bases)
    result = tuple(NameMap(entry.dataset, entry.original, entry.identity, limited(base, entry.identity, force_hash=counts[base] > 1)) for entry, base in zip(entries, bases))
    if len({item.identity for item in result}) != len(result):
        raise ValueError("Duplicate source object identity")
    if len({item.target for item in result}) != len(result):
        raise ValueError("Naming hash collision; explicit contract disposition required")
    return result


def allocate_columns(originals: list[str], *, object_id: str) -> tuple[NameMap, ...]:
    valid_digest(object_id)
    bases = [slug(original) for original in originals]
    counts = Counter(bases)
    result = []
    for ordinal, (original, base) in enumerate(zip(originals, bases), start=1):
        identity = hash_identity(["xiangrugu.column.v1", object_id, ordinal, original])
        suffix = f"__c{ordinal}" if counts[base] > 1 else ""
        result.append(NameMap("", original, identity, limited(base, identity, suffix=suffix), ordinal))
    if len({item.target for item in result}) != len(result):
        raise ValueError("Column naming collision; explicit contract disposition required")
    return tuple(result)


def quote_identifier(value: str) -> str:
    if not value or "\x00" in value or len(value.encode("utf-8")) > 63:
        raise ValueError("Invalid PostgreSQL identifier")
    return '"' + value.replace('"', '""') + '"'


def validate_schema(value: str) -> str:
    if value not in {"cbdb", "chgis", "harv", "audit"}:
        raise ValueError("Schema must be selected explicitly from the contract")
    return value

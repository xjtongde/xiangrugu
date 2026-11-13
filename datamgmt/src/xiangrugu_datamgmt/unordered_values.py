"""Strict scalar bytes for an independent, unordered format; no readers."""
from dataclasses import dataclass, fields
import hashlib
import json
import math
import re
import struct


def valid_digest(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


class UnorderedValueError(ValueError):
    def __init__(self, code, *, side=None, scan_index=None, column_key=None):
        self.code, self.side = code, side
        self.scan_index, self.column_key = scan_index, column_key
        super().__init__(code)


@dataclass(frozen=True)
class UnorderedColumn:
    source_ordinal: int
    column_key: str
    pg_type: str
    allow_null_value: bool

    def __post_init__(self):
        if (type(self.source_ordinal) is not int or self.source_ordinal < 0
                or not valid_digest(self.column_key)
                or type(self.allow_null_value) is not bool):
            raise UnorderedValueError("structure")
        if type(self.pg_type) is not str or self.pg_type not in ("text", "bigint", "double precision"):
            raise UnorderedValueError("unsupported_type")


@dataclass(frozen=True)
class UnorderedSchema:
    source_object_id: str
    columns: tuple[UnorderedColumn, ...]
    format_version: int = 1

    def __post_init__(self):
        if (not valid_digest(self.source_object_id) or type(self.format_version) is not int
                or self.format_version != 1 or type(self.columns) is not tuple
                or not self.columns or any(type(c) is not UnorderedColumn for c in self.columns)
                or tuple(c.source_ordinal for c in self.columns) != tuple(range(len(self.columns)))
                or len({c.column_key for c in self.columns}) != len(self.columns)):
            raise UnorderedValueError("structure")


@dataclass(frozen=True)
class UnorderedLimits:
    max_rows: int = 100000
    max_columns: int = 512
    max_field_bytes: int = 1048576
    max_row_bytes: int = 8388608
    max_stream_bytes: int = 268435456
    chunk_bytes: int = 33554432
    chunk_rows: int = 4096
    merge_fan_in: int = 16
    max_temp_bytes: int = 2147483648
    max_temp_files: int = 1024
    max_differences: int = 100
    max_seconds: int = 120
    workers: int = 1

    def __post_init__(self):
        for f in fields(self):
            v = getattr(self, f.name)
            if type(v) is not int or v < (0 if f.name == "max_differences" else 1):
                raise UnorderedValueError("budget")
        if (self.workers != 1 or self.merge_fan_in < 2
                or self.chunk_bytes < self.max_row_bytes + 13):
            raise UnorderedValueError("budget")


def _cell(column, value, limits, remaining):
    if type(column) is not UnorderedColumn or type(limits) is not UnorderedLimits:
        raise UnorderedValueError("structure")
    if value is None:
        if not column.allow_null_value:
            raise UnorderedValueError("unsupported_type", column_key=column.column_key)
        if remaining < 1:
            raise UnorderedValueError("budget", column_key=column.column_key)
        return b"\x00"
    if column.pg_type == "bigint":
        if type(value) is not int or not -(2**63) <= value < 2**63:
            raise UnorderedValueError("unsupported_type", column_key=column.column_key)
        payload, tag = struct.pack(">q", value), b"\x02"
    elif column.pg_type == "double precision":
        if type(value) is not float or not math.isfinite(value):
            raise UnorderedValueError("unsupported_type", column_key=column.column_key)
        payload, tag = struct.pack(">d", value), b"\x03"
    else:
        if type(value) is not str:
            raise UnorderedValueError("unsupported_type", column_key=column.column_key)
        cap = min(limits.max_field_bytes, remaining - 9)
        if len(value) > cap:
            raise UnorderedValueError("budget", column_key=column.column_key)
        size = 0
        for ch in value:
            n = ord(ch)
            if 0xD800 <= n <= 0xDFFF:
                raise UnorderedValueError("unsupported_type", column_key=column.column_key)
            size += 1 if n < 128 else 2 if n < 2048 else 3 if n < 65536 else 4
            if size > cap:
                raise UnorderedValueError("budget", column_key=column.column_key)
        return b"\x01" + struct.pack(">Q", size) + value.encode("utf-8", "strict")
    if remaining < 9:
        raise UnorderedValueError("budget", column_key=column.column_key)
    return tag + payload


def encode_unordered_cell(column: UnorderedColumn, value: object, *, limits: UnorderedLimits) -> bytes:
    return _cell(column, value, limits, limits.max_row_bytes)


def schema_bytes(schema: UnorderedSchema) -> bytes:
    if type(schema) is not UnorderedSchema:
        raise UnorderedValueError("structure")
    return json.dumps([[c.source_ordinal, c.column_key, c.pg_type, c.allow_null_value]
                       for c in schema.columns], ensure_ascii=True,
                      allow_nan=False, separators=(",", ":")).encode("ascii")


def header_bytes(schema: UnorderedSchema) -> bytes:
    return b"XRGSET\x00\x01" + bytes.fromhex(schema.source_object_id) + hashlib.sha256(schema_bytes(schema)).digest()


def trailer_bytes(count: int) -> bytes:
    if type(count) is not int or not 0 <= count < 2**64:
        raise UnorderedValueError("count")
    return b"\x45" + struct.pack(">Q", count)


def encode_unordered_row(schema: UnorderedSchema, values: tuple[object, ...], *, limits: UnorderedLimits) -> bytes:
    if (type(schema) is not UnorderedSchema or type(values) is not tuple
            or len(values) != len(schema.columns)):
        raise UnorderedValueError("structure")
    if len(schema.columns) > limits.max_columns:
        raise UnorderedValueError("budget")
    cells, size = [], 0
    for c, v in zip(schema.columns, values, strict=True):
        cell = _cell(c, v, limits, limits.max_row_bytes - size)
        size += len(cell)
        cells.append(cell)
    return b"\x52" + struct.pack(">IQ", len(cells), size) + b"".join(cells)


def validate_unordered_frame(schema: UnorderedSchema, frame: bytes, *, limits: UnorderedLimits) -> None:
    if type(frame) is not bytes or len(frame) < 13 or frame[0] != 0x52:
        raise UnorderedValueError("temp_corrupt")
    width, size = struct.unpack(">IQ", frame[1:13])
    if width != len(schema.columns) or size != len(frame)-13:
        raise UnorderedValueError("temp_corrupt")
    if width > limits.max_columns or size > limits.max_row_bytes:
        raise UnorderedValueError("budget")
    p = 13
    for c in schema.columns:
        if p >= len(frame):
            raise UnorderedValueError("temp_corrupt")
        tag, p = frame[p], p+1
        if tag == 0:
            if not c.allow_null_value:
                raise UnorderedValueError("temp_corrupt")
            continue
        want = {"text": 1, "bigint": 2, "double precision": 3}[c.pg_type]
        if tag != want or p+8 > len(frame):
            raise UnorderedValueError("temp_corrupt")
        if tag == 1:
            n = struct.unpack(">Q", frame[p:p+8])[0]
            p += 8
            if n > limits.max_field_bytes or p+n > len(frame):
                raise UnorderedValueError("temp_corrupt")
            try:
                frame[p:p+n].decode("utf-8", "strict")
            except UnicodeError:
                raise UnorderedValueError("temp_corrupt") from None
            p += n
        else:
            if tag == 3 and not math.isfinite(struct.unpack(">d", frame[p:p+8])[0]):
                raise UnorderedValueError("temp_corrupt")
            p += 8
    if p != len(frame):
        raise UnorderedValueError("temp_corrupt")

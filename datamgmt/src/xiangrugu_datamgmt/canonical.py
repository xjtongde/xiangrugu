"""Lossless, versioned text/bigint bytes; no readers or database operations."""
from dataclasses import dataclass, fields, replace
import hashlib
import json
import re
import struct
from collections.abc import Callable, Iterator

from .naming import quote_identifier

ROW_KEY = "derived:__src_rownum"
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class ValueContractError(ValueError):
    def __init__(self, code: str, *, rownum: int | None = None,
                 column_key: str | None = None):
        self.code = code
        self.rownum = rownum
        self.column_key = column_key
        super().__init__(code)


def valid_digest(value):
    return type(value) is str and _DIGEST.fullmatch(value) is not None


@dataclass(frozen=True)
class ValueColumn:
    column_key: str
    target_name: str
    pg_type: str
    nullable: bool

    def __post_init__(self):
        if not (valid_digest(self.column_key) or self.column_key == ROW_KEY):
            raise ValueContractError("structure")
        if type(self.target_name) is not str or type(self.nullable) is not bool:
            raise ValueContractError("structure")
        try:
            quote_identifier(self.target_name)
        except (ValueError, UnicodeError):
            raise ValueContractError("structure") from None
        if type(self.pg_type) is not str or self.pg_type not in ("text", "bigint"):
            raise ValueContractError("unsupported_type")


@dataclass(frozen=True)
class ValueSchema:
    source_object_id: str
    columns: tuple[ValueColumn, ...]
    format_version: int = 1

    def __post_init__(self):
        if not valid_digest(self.source_object_id):
            raise ValueContractError("structure")
        if type(self.format_version) is not int or self.format_version != 1:
            raise ValueContractError("unsupported_type")
        if type(self.columns) is not tuple or not self.columns:
            raise ValueContractError("structure")
        if any(type(c) is not ValueColumn for c in self.columns):
            raise ValueContractError("structure")
        if len({c.column_key for c in self.columns}) != len(self.columns):
            raise ValueContractError("structure")
        if len({c.target_name for c in self.columns}) != len(self.columns):
            raise ValueContractError("structure")
        last = self.columns[-1]
        if (last.column_key, last.target_name, last.pg_type, last.nullable) != (
                ROW_KEY, "__src_rownum", "bigint", False):
            raise ValueContractError("structure")
        if any(c.column_key == ROW_KEY or c.target_name == "__src_rownum"
               for c in self.columns[:-1]):
            raise ValueContractError("structure")


@dataclass(frozen=True)
class ValueLimits:
    max_rows: int = 100000
    max_columns: int = 512
    max_field_bytes: int = 1048576
    max_row_bytes: int = 8388608
    max_stream_bytes: int = 268435456
    max_differences: int = 100

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            minimum = 0 if field.name == "max_differences" else 1
            if type(value) is not int or value < minimum:
                raise ValueContractError("budget")


def encode_cell(column: ValueColumn, value: object, *, limits: ValueLimits,
                max_encoded_bytes: int | None = None) -> bytes:
    remaining = limits.max_row_bytes if max_encoded_bytes is None else max_encoded_bytes
    if value is None:
        if column.nullable:
            if remaining < 1:
                raise ValueContractError("budget", column_key=column.column_key)
            return b"\x00"
        raise ValueContractError("unsupported_type", column_key=column.column_key)
    if column.pg_type == "bigint":
        if type(value) is not int or not -(2**63) <= value < 2**63:
            raise ValueContractError("unsupported_type", column_key=column.column_key)
        if remaining < 9:
            raise ValueContractError("budget", column_key=column.column_key)
        return b"\x02" + struct.pack(">q", value)
    if type(value) is not str:
        raise ValueContractError("unsupported_type", column_key=column.column_key)
    payload_limit = min(limits.max_field_bytes, remaining - 9)
    if len(value) > payload_limit:
        raise ValueContractError("budget", column_key=column.column_key)
    # Count strict UTF-8 bytes without allocating a payload beyond the remaining budget.
    byte_count = 0
    for char in value:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            raise ValueContractError("unsupported_type", column_key=column.column_key)
        byte_count += 1 if code < 0x80 else 2 if code < 0x800 else 3 if code < 0x10000 else 4
        if byte_count > payload_limit:
            raise ValueContractError("budget", column_key=column.column_key)
    try:
        payload = value.encode("utf-8", errors="strict")
    except UnicodeError:
        raise ValueContractError("unsupported_type", column_key=column.column_key) from None
    if len(payload) > limits.max_field_bytes:
        raise ValueContractError("budget", column_key=column.column_key)
    return b"\x01" + struct.pack(">Q", len(payload)) + payload


def schema_bytes(schema: ValueSchema) -> bytes:
    return json.dumps(
        [[c.column_key, c.target_name, c.pg_type, c.nullable] for c in schema.columns],
        ensure_ascii=True, allow_nan=False, separators=(",", ":"),
    ).encode("ascii")


def header_bytes(schema: ValueSchema) -> bytes:
    return (b"XRGVALUE\x00\x01" + bytes.fromhex(schema.source_object_id)
            + hashlib.sha256(schema_bytes(schema)).digest())


def trailer_bytes(count: int) -> bytes:
    if type(count) is not int or not 0 <= count < 2**64:
        raise ValueContractError("count")
    return b"\x45" + struct.pack(">Q", count)


@dataclass(frozen=True)
class EncodedRow:
    frame: bytes
    cells: tuple[bytes, ...]
    rownum: int


def encode_row(schema: ValueSchema, values: tuple[object, ...], *,
               expected_rownum: int, limits: ValueLimits) -> EncodedRow:
    if len(schema.columns) > limits.max_columns:
        raise ValueContractError("budget")
    if type(values) is not tuple or len(values) != len(schema.columns):
        raise ValueContractError("structure", rownum=expected_rownum)
    if (type(expected_rownum) is not int or not 1 <= expected_rownum < 2**63
            or type(values[-1]) is not int or values[-1] != expected_rownum):
        raise ValueContractError("rownum", rownum=expected_rownum, column_key=ROW_KEY)
    cells = []
    size = 0
    for column, value in zip(schema.columns, values, strict=True):
        try:
            encoded = encode_cell(column, value, limits=limits,
                                  max_encoded_bytes=limits.max_row_bytes - size)
        except ValueContractError as error:
            raise ValueContractError(error.code, rownum=expected_rownum,
                                     column_key=column.column_key) from None
        size += len(encoded)
        if size > limits.max_row_bytes:
            raise ValueContractError("budget", rownum=expected_rownum)
        cells.append(encoded)
    frame = b"\x52" + struct.pack(">IQ", len(cells), size) + b"".join(cells)
    return EncodedRow(frame, tuple(cells), expected_rownum)


@dataclass(frozen=True)
class StreamSummary:
    row_count: int
    field_count: int
    stream_bytes: int
    sha256: str


class ValueStreamState:
    """Single-use incremental stream; only normal EOF permits finish."""
    def __init__(self, schema: ValueSchema, limits: ValueLimits):
        self.schema = schema
        self.limits = limits
        self.closed = False
        self.row_count = 0
        self.field_count = 0
        if (len(schema.columns) > limits.max_columns
                or 83 > limits.max_stream_bytes):
            raise ValueContractError("budget")
        header = header_bytes(schema)
        self.stream_bytes = len(header)
        self._hash = hashlib.sha256(header)

    def accept(self, values: tuple[object, ...]) -> EncodedRow:
        if self.closed:
            raise ValueContractError("input_error")
        try:
            if self.row_count >= self.limits.max_rows:
                raise ValueContractError("budget")
            remaining = self.limits.max_stream_bytes - self.stream_bytes - 13 - 9
            if remaining < 1:
                raise ValueContractError("budget", rownum=self.row_count + 1)
            row_limits = replace(self.limits,
                                 max_row_bytes=min(self.limits.max_row_bytes, remaining))
            row = encode_row(self.schema, values, expected_rownum=self.row_count + 1,
                             limits=row_limits)
            if self.stream_bytes + len(row.frame) + 9 > self.limits.max_stream_bytes:
                raise ValueContractError("budget", rownum=row.rownum)
        except ValueContractError:
            self.closed = True
            raise
        self._hash.update(row.frame)
        self.stream_bytes += len(row.frame)
        self.row_count += 1
        self.field_count += len(row.cells)
        return row

    def finish(self) -> StreamSummary:
        if self.closed:
            raise ValueContractError("input_error")
        self.closed = True
        self._hash.update(trailer_bytes(self.row_count))
        self.stream_bytes += 9
        return StreamSummary(self.row_count, self.field_count, self.stream_bytes,
                             self._hash.hexdigest())


def check_cancelled(cancelled: Callable[[], bool] | None):
    if cancelled is None:
        return
    try:
        result = cancelled()
    except Exception:
        raise ValueContractError("input_error") from None
    if type(result) is not bool:
        raise ValueContractError("input_error")
    if result:
        raise ValueContractError("cancelled")


def next_row(rows: Iterator[tuple[object, ...]]):
    try:
        return next(rows)
    except StopIteration:
        raise
    except Exception:
        raise ValueContractError("input_error") from None


def summarize_rows(schema: ValueSchema, rows: Iterator[tuple[object, ...]], *,
                   limits: ValueLimits,
                   cancelled: Callable[[], bool] | None = None) -> StreamSummary:
    state = ValueStreamState(schema, limits)
    while True:
        check_cancelled(cancelled)
        try:
            values = next_row(rows)
        except StopIteration:
            break
        state.accept(values)
    check_cancelled(cancelled)
    return state.finish()

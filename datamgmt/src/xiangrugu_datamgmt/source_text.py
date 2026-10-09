"""Bounded, source-only UTF-8 TSV reader independent of csv and importer code.

Only LF records are supported. Policies are explicit, not guessed. All records,
including the header, retain source order and strings; no padding or cleaning.
This is a contract-preparation reader, not a database verifier or import gate.
"""
from dataclasses import dataclass


class TextReadError(ValueError):
    def __init__(self, code, byte_offset, record_ordinal=None, column_ordinal=None):
        self.code = code
        self.byte_offset = byte_offset
        self.record_ordinal = record_ordinal
        self.column_ordinal = column_ordinal
        super().__init__(f"{code} at source byte {byte_offset}")


@dataclass(frozen=True)
class TextReadLimits:
    max_bytes: int = 16 * 1024 * 1024
    max_records: int = 100_000
    max_columns: int = 512
    max_field_bytes: int = 1024 * 1024

    def __post_init__(self):
        for value in (self.max_bytes, self.max_records, self.max_columns, self.max_field_bytes):
            if type(value) is not int or value <= 0:
                raise ValueError("Text limits must be positive integers")


def read_utf8_tsv(raw: bytes, *, bom_as_signature: bool, backslash_escape: bool,
                  limits: TextReadLimits = TextReadLimits()) -> tuple[tuple[str, ...], ...]:
    """Return only after full strict decode, syntax, width and budget checks.

Error offsets are zero-based in original bytes, including any BOM. Record and
column ordinals are one-based when known. No file I/O or shared CSV parsing.
"""
    if type(raw) is not bytes or type(bom_as_signature) is not bool or type(backslash_escape) is not bool:
        raise TypeError("Raw bytes and explicit boolean policies are required")
    if len(raw) > limits.max_bytes:
        raise TextReadError("byte_limit", limits.max_bytes)
    for byte, code in ((0, "nul_byte"), (13, "unsupported_cr")):
        offset = raw.find(bytes((byte,)))
        if offset >= 0:
            raise TextReadError(code, offset)
    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise TextReadError("invalid_utf8", error.start) from None

    records, row = [], []
    field = bytearray()
    state = "start"
    index = 3 if bom_as_signature and raw.startswith(b"\xef\xbb\xbf") else 0

    def fail(code, offset):
        raise TextReadError(code, offset, len(records) + 1, len(row) + 1)

    def append(byte, offset):
        if len(field) >= limits.max_field_bytes:
            fail("field_byte_limit", offset)
        field.append(byte)

    def finish_field(offset):
        if len(row) >= limits.max_columns:
            fail("column_limit", offset)
        row.append(field.decode("utf-8", errors="strict"))
        field.clear()

    def finish_record(offset):
        if len(records) >= limits.max_records:
            fail("record_limit", offset)
        if not records and not row:
            fail("missing_header", offset)
        if records and len(row) != len(records[0]):
            raise TextReadError("record_width", offset, len(records) + 1, len(row))
        records.append(tuple(row))
        row.clear()

    while index < len(raw):
        byte = raw[index]
        if state == "closed" and byte not in (9, 10):
            fail("after_quote", index)
        if backslash_escape and byte == 92:
            if index + 1 == len(raw):
                fail("dangling_escape", index)
            append(raw[index + 1], index + 1)
            if state == "start":
                state = "unquoted"
            index += 2
            continue
        if state == "quoted":
            if byte == 34:
                if index + 1 < len(raw) and raw[index + 1] == 34:
                    append(34, index)
                    index += 2
                    continue
                state = "closed"
            else:
                append(byte, index)
        elif state == "start" and byte == 34:
            state = "quoted"
        elif byte in (9, 10):
            # A genuinely blank physical record is not a one-field empty value.
            if byte == 9 or row or field or state != "start":
                finish_field(index)
            if byte == 10:
                finish_record(index)
            state = "start"
        else:
            append(byte, index)
            state = "unquoted"
        index += 1
    if state == "quoted":
        fail("unclosed_quote", len(raw))
    if row or field or state != "start":
        finish_field(len(raw))
        finish_record(len(raw))
    if not records:
        fail("missing_header", len(raw))
    return tuple(records)

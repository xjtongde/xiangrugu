"""Bounded SQLite API storage-type diagnostics; never import or emit raw text."""
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import sqlite3
import time

from .sqlite_diagnostic import (
    SQLiteDiagnosticError, _checked_stat, _hash, _identity, _metadata_connection,
)


@dataclass(frozen=True)
class ProfileLimits:
    max_file_bytes: int = 1024**3
    max_tables: int = 3
    max_columns: int = 64
    max_rows: int = 500000
    max_cells: int = 8000000
    max_cell_bytes: int = 2 * 1024**2
    max_total_value_bytes: int = 128 * 1024**2
    max_output_bytes: int = 1024**2
    max_vm_steps: int = 20000000
    max_seconds: int = 180

    def __post_init__(self):
        if any(type(value) is not int or value <= 0 for value in vars(self).values()):
            raise ValueError("Profile budgets must be positive integers")


def scope_authorizer(tables):
    """Only selected columns and typeof; denies schema, views, functions, writes."""
    def authorize(action, first, second, database, origin):
        if origin is not None:
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            return (sqlite3.SQLITE_OK if database == "main" and first in tables
                    and second in tables[first] else sqlite3.SQLITE_DENY)
        if action == sqlite3.SQLITE_FUNCTION and second == "typeof":
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    return authorize


def quoted(name):
    return '"' + name.replace('"', '""') + '"'


def _range(target, minimum, maximum, value):
    target[minimum] = value if target[minimum] is None else min(target[minimum], value)
    target[maximum] = value if target[maximum] is None else max(target[maximum], value)


def _column(name):
    return dict(name=name, storage_counts=dict(null=0, integer=0, real=0, text=0, blob=0),
        integer_range=dict(min=None, max=None), real_range=dict(min=None, max=None),
        real_nonfinite_count=0,
        text_lengths=dict(min_codepoints=None, max_codepoints=None,
                          min_sqlite_api_utf8_bytes=None, max_sqlite_api_utf8_bytes=None),
        invalid_utf8_text_count=0, text_embedded_nul_count=0,
        blob_lengths=dict(min_bytes=None, max_bytes=None))


def profile_sqlite(path, *, expected_size, expected_sha256, tables,
                   limits=ProfileLimits(), cancelled=lambda: False):
    """Read all selected ordinary-table columns once, streaming, no sorting/dedup."""
    path = Path(path)
    if (type(expected_size) is not int or expected_size < 0 or
            not isinstance(expected_sha256, str) or
            not re.fullmatch("[0-9a-f]{64}", expected_sha256)):
        raise SQLiteDiagnosticError("invalid_identity")
    if (not isinstance(tables, dict) or not tables or
            any(not isinstance(name, str) or not name or "\0" in name
                or not isinstance(cols, (tuple, list)) or not cols
                or any(not isinstance(col, str) or not col or "\0" in col for col in cols)
                or len(set(cols)) != len(cols) for name, cols in tables.items())):
        raise SQLiteDiagnosticError("invalid_scope")
    if len(tables) > limits.max_tables or sum(map(len, tables.values())) > limits.max_columns:
        raise SQLiteDiagnosticError("scope_limit")
    start = time.monotonic()
    def guard():
        if cancelled():
            raise SQLiteDiagnosticError("cancelled")
        if time.monotonic() - start > limits.max_seconds:
            raise SQLiteDiagnosticError("time_limit")
    guard()
    before = _checked_stat(path)
    if before.st_size > limits.max_file_bytes:
        raise SQLiteDiagnosticError("file_limit")
    if before.st_size != expected_size:
        raise SQLiteDiagnosticError("identity_mismatch")
    sha_before = _hash(path, guard)
    if sha_before != expected_sha256:
        raise SQLiteDiagnosticError("identity_mismatch")
    if _identity(before) != _identity(_checked_stat(path)):
        raise SQLiteDiagnosticError("source_changed")
    rows_read = cells_read = total_value_bytes = vm_steps = 0
    progress_error = None
    progress_interval = min(1000, limits.max_vm_steps)
    def progress():
        nonlocal vm_steps, progress_error
        vm_steps += progress_interval
        try:
            guard()
            # SQLite reports approximate instruction intervals, not exact counts.
            # Reserve one interval and interrupt at the boundary, never after it.
            if vm_steps + progress_interval >= limits.max_vm_steps:
                raise SQLiteDiagnosticError("vm_limit")
            return 0
        except SQLiteDiagnosticError as exc:
            progress_error = exc
            return 1
    results = []
    try:
        with _metadata_connection(path) as db:
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, limits.max_cell_bytes)
            db.set_progress_handler(progress, progress_interval)
            # Validate BEFORE querying. This also prevents SQLite DQS from silently
            # treating an absent double-quoted column as a string constant.
            for name, columns in tables.items():
                obj = db.execute("SELECT type,sql FROM main.sqlite_schema WHERE name=?",
                                 (name,)).fetchone()
                if not obj or obj[0] != "table" or re.match(
                        r"\s*CREATE\s+VIRTUAL\s+TABLE\b", obj[1] or "", re.I):
                    raise SQLiteDiagnosticError("unsupported_object")
                metadata = db.execute("PRAGMA main.table_xinfo('" +
                                      name.replace("'", "''") + "')").fetchall()
                if tuple(row[1] for row in metadata) != tuple(columns) or \
                        any(row[6] != 0 for row in metadata):
                    raise SQLiteDiagnosticError("column_scope_mismatch")
            db.text_factory = bytes  # Never silently decode/replace invalid TEXT.
            db.set_authorizer(scope_authorizer(tables))
            for name, columns in tables.items():
                guard()
                stats = [_column(col) for col in columns]
                expressions = ",".join(f"typeof({quoted(col)}),{quoted(col)}" for col in columns)
                count = 0
                for row in db.execute(f"SELECT {expressions} FROM main.{quoted(name)}"):
                    guard()
                    count += 1
                    rows_read += 1
                    cells_read += len(columns)
                    if rows_read > limits.max_rows or cells_read > limits.max_cells:
                        raise SQLiteDiagnosticError("row_or_cell_limit")
                    for ordinal, col in enumerate(stats):
                        kind, value = row[ordinal*2:ordinal*2+2]
                        kind = kind.decode("ascii")
                        if kind not in col["storage_counts"]:
                            raise SQLiteDiagnosticError("unknown_storage_class")
                        col["storage_counts"][kind] += 1
                        length = len(value) if kind in ("text", "blob") else (0 if kind == "null" else 8)
                        total_value_bytes += length
                        if length > limits.max_cell_bytes or total_value_bytes > limits.max_total_value_bytes:
                            raise SQLiteDiagnosticError("value_byte_limit")
                        if kind == "integer":
                            _range(col["integer_range"], "min", "max", value)
                        elif kind == "real":
                            if math.isfinite(value):
                                _range(col["real_range"], "min", "max", value)
                            else:
                                col["real_nonfinite_count"] += 1
                        elif kind == "text":
                            _range(col["text_lengths"], "min_sqlite_api_utf8_bytes",
                                   "max_sqlite_api_utf8_bytes", length)
                            col["text_embedded_nul_count"] += int(b"\0" in value)
                            try:
                                decoded = value.decode("utf-8", errors="strict")
                            except UnicodeError:
                                col["invalid_utf8_text_count"] += 1
                            else:
                                _range(col["text_lengths"], "min_codepoints", "max_codepoints", len(decoded))
                        elif kind == "blob":
                            _range(col["blob_lengths"], "min_bytes", "max_bytes", length)
                for col in stats:
                    # JSON consumers cannot all represent signed 64-bit integers;
                    # decimal strings/float hex preserve exact numeric extrema.
                    col["integer_range"] = {key: None if val is None else str(val)
                                            for key, val in col["integer_range"].items()}
                    col["real_range"] = {key+"_hex": None if val is None else val.hex()
                                         for key, val in col["real_range"].items()}
                results.append(dict(name=name, row_count=count, columns=stats, complete=True))
    except sqlite3.DatabaseError as exc:
        if progress_error is not None:
            raise progress_error from None
        if getattr(exc, "sqlite_errorcode", None) == sqlite3.SQLITE_TOOBIG:
            raise SQLiteDiagnosticError("cell_byte_limit") from None
        raise SQLiteDiagnosticError("sqlite_error") from None
    after = _checked_stat(path)
    sha_after = _hash(path, guard)
    if _identity(before) != _identity(after) or \
            _identity(before) != _identity(_checked_stat(path)) or sha_after != sha_before:
        raise SQLiteDiagnosticError("source_changed")
    result = dict(format="xiangrugu.sqlite-api-type-profile.v1",
        status="SELECTED_TABLES_PROFILED", complete_for_selected_tables=True,
        tables=results, rows_read=rows_read, cells_read=cells_read,
        scanned_value_bytes=total_value_bytes, source_sha256_before=sha_before,
        source_sha256_after=sha_after, source_size=before.st_size, sqlite_version=sqlite3.sqlite_version,
        text_byte_length_basis="SQLite API UTF-8 bytes; NOT original on-disk text encoding",
        vm_budget_basis="approximate SQLite progress intervals; one interval reserved; not an exact instruction counter",
        integer_range_encoding="decimal strings", real_range_encoding="Python float.hex binary64",
        lossless_text_decoding_confirmed=not any(c["invalid_utf8_text_count"] for t in results for c in t["columns"]),
        duplicates_retained=True, ordered_values_verified=False, primary_key_uniqueness_verified=False,
        raw_text_or_blob_emitted=False, source_sqlite_connected=True, postgresql_connected=False,
        value_contract_approved=False, type_mapping_approved=False, ready_for_import=False)
    if len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")) > limits.max_output_bytes:
        raise SQLiteDiagnosticError("output_limit")
    return result

"""Independent, bounded native values from a stationary read-only SQLite file.

No importer, profile answers, PostgreSQL, source DDL execution or file writes.
Caller must enforce a read-only stationary snapshot and own the iterator lifetime.
Completion requires exhaustion, connection close and a second full source digest.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import math
from pathlib import Path
import re
import sqlite3
import time

from .identity import source_object_id
from .naming import allocate_columns
from .read_cache import require_read_cache
from .sqlite_diagnostic import (SQLiteDiagnosticError, _checked_stat, _hash,
                                _identity, _metadata_connection)
from .unordered_validate import UnorderedEvidence
from .unordered_values import UnorderedSchema, valid_digest


class SQLiteValueReadError(ValueError):
    def __init__(self, code, *, scan_index=None, column_key=None):
        self.code, self.scan_index, self.column_key = code, scan_index, column_key
        super().__init__(code)


@dataclass(frozen=True)
class SQLiteValueLimits:
    max_file_bytes: int = 1024**3
    max_columns: int = 512
    max_rows: int = 100000
    max_cells: int = 8000000
    max_cell_bytes: int = 1024**2
    max_value_bytes: int = 256 * 1024**2
    max_vm_steps: int = 20000000
    max_seconds: int = 120

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in vars(self).values()):
            raise ValueError("Read budgets must be positive integers")


def _quoted(name):
    return '"' + name.replace('"', '""') + '"'


def _value_authorizer(table, columns):
    def authorize(action, first, second, database, origin):
        if origin is not None:
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            return (sqlite3.SQLITE_OK if database == "main" and first == table
                    and second in columns else sqlite3.SQLITE_DENY)
        if action == sqlite3.SQLITE_FUNCTION and second == "typeof":
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    return authorize


class _ValueRows:
    def __init__(self, path, expected_size, expected_sha256, table, columns,
                 schema, limits, cancelled, *, batch=None):
        self.path, self.expected_size, self.expected_sha256 = path, expected_size, expected_sha256
        self.table, self.columns, self.schema = table, columns, schema
        self.limits, self.cancelled = limits, cancelled
        self._batch = batch
        self.evidence = UnorderedEvidence("source", schema.source_object_id, expected_sha256)
        self._summary = dict(complete=False, rows_read=0, cells_read=0, value_bytes=0,
                            source_sha256_before=None, source_sha256_after=None,
                            error_code=None, postgresql_connected=False)
        self._rows = self._read()

    @property
    def summary(self):
        return self._summary.copy()

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._rows)

    def close(self):
        self._rows.close()

    def _read(self):
        start = time.monotonic()
        limits = self.limits

        def guard():
            if self._batch is not None:
                self._batch.guard()
            try:
                stop = self.cancelled()
            except Exception as error:
                raise SQLiteValueReadError("input_error") from error
            if type(stop) is not bool:
                raise SQLiteValueReadError("input_error")
            if stop:
                raise SQLiteValueReadError("cancelled")
            if time.monotonic() - start > limits.max_seconds:
                raise SQLiteValueReadError("time_limit")

        vm_steps, progress_error = 0, None
        interval = min(1000, limits.max_vm_steps)

        def progress():
            nonlocal vm_steps, progress_error
            vm_steps += interval
            try:
                guard()
                if vm_steps + interval >= limits.max_vm_steps:
                    raise SQLiteValueReadError("vm_limit")
                return 0
            except SQLiteValueReadError as exc:
                progress_error = exc
                return 1

        try:
            guard()
            before = _checked_stat(self.path)
            if before.st_size > limits.max_file_bytes:
                raise SQLiteValueReadError("file_limit")
            if before.st_size != self.expected_size:
                raise SQLiteValueReadError("identity_mismatch")
            if self._batch is None:
                if _hash(self.path, guard) != self.expected_sha256:
                    raise SQLiteValueReadError("identity_mismatch")
            elif _identity(before) != self._batch.identity:
                raise SQLiteValueReadError("source_changed")
            if _identity(before) != _identity(_checked_stat(self.path)):
                raise SQLiteValueReadError("source_changed")
            if self._batch is None:
                self._summary["source_sha256_before"] = self.expected_sha256
            with _metadata_connection(self.path) as db:
                # SQLite LENGTH limits both individual values and encoded records.
                db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, limits.max_cell_bytes)
                db.set_progress_handler(progress, interval)
                obj = db.execute("SELECT type,sql FROM main.sqlite_schema WHERE name=?",
                                 (self.table,)).fetchone()
                if not obj or obj[0] != "table" or re.match(
                        r"\s*CREATE\s+VIRTUAL\s+TABLE\b", obj[1] or "", re.I):
                    raise SQLiteValueReadError("unsupported_object")
                literal = "'" + self.table.replace("'", "''") + "'"
                metadata = db.execute("PRAGMA main.table_xinfo(" + literal + ")").fetchall()
                if (tuple(row[1] for row in metadata) != self.columns
                        or tuple(row[0] for row in metadata) != tuple(range(len(self.columns)))
                        or any(row[6] != 0 for row in metadata)):
                    raise SQLiteValueReadError("column_scope_mismatch")
                if any(c.allow_null_value != (not bool(row[3]))
                       for c, row in zip(self.schema.columns, metadata, strict=True)):
                    raise SQLiteValueReadError("nullability_mismatch")
                db.text_factory = bytes
                db.set_authorizer(_value_authorizer(self.table, self.columns))
                query = ",".join(f"typeof({_quoted(c)}),{_quoted(c)}" for c in self.columns)
                cursor = db.execute(f"SELECT {query} FROM main.{_quoted(self.table)}")
                try:
                    for row in cursor:
                        guard()
                        scan = self._summary["rows_read"] + 1
                        if scan > limits.max_rows or self._summary["cells_read"] + len(self.columns) > limits.max_cells:
                            raise SQLiteValueReadError("row_or_cell_limit", scan_index=scan)
                        values = []
                        for i, col in enumerate(self.schema.columns):
                            kind, value = row[2*i:2*i+2]
                            expected = {"bigint": b"integer", "double precision": b"real", "text": b"text"}[col.pg_type]
                            if kind == b"null":
                                if value is not None or not col.allow_null_value:
                                    raise SQLiteValueReadError("null_not_allowed", scan_index=scan, column_key=col.column_key)
                                size = 0
                            elif kind != expected:
                                raise SQLiteValueReadError("storage_type_mismatch", scan_index=scan, column_key=col.column_key)
                            elif kind == b"text":
                                size = len(value)
                                try:
                                    value = value.decode("utf-8", errors="strict")
                                except UnicodeError:
                                    raise SQLiteValueReadError("invalid_utf8", scan_index=scan, column_key=col.column_key) from None
                            else:
                                size = 8
                                if (col.pg_type == "bigint" and (type(value) is not int or not -(2**63) <= value < 2**63)
                                        or col.pg_type == "double precision" and (type(value) is not float or not math.isfinite(value))):
                                    raise SQLiteValueReadError("storage_type_mismatch", scan_index=scan, column_key=col.column_key)
                            self._summary["value_bytes"] += size
                            if size > limits.max_cell_bytes or self._summary["value_bytes"] > limits.max_value_bytes:
                                raise SQLiteValueReadError("value_byte_limit", scan_index=scan, column_key=col.column_key)
                            values.append(value)
                        self._summary["rows_read"] = scan
                        self._summary["cells_read"] += len(values)
                        yield tuple(values)
                finally:
                    cursor.close()
            # Exhaustion alone is insufficient: the connection is now closed and
            # the caller's stationary file must still match its original identity.
            guard()
            after = _checked_stat(self.path)
            if _identity(before) != _identity(after):
                raise SQLiteValueReadError("source_changed")
            if self._batch is None:
                final_hash = _hash(self.path, guard)
                if final_hash != self.expected_sha256 or _identity(before) != _identity(_checked_stat(self.path)):
                    raise SQLiteValueReadError("source_changed")
                guard()
                self._summary.update(complete=True, source_sha256_after=final_hash)
            else:
                if _identity(after) != self._batch.identity:
                    raise SQLiteValueReadError("source_changed")
                guard()
                # Exhausted values are provisional, NOT standalone digest proof.
                self._summary.update(values_complete=True, digest_scope="batch_pending")
        except SQLiteDiagnosticError as exc:
            self._summary["error_code"] = exc.code
            raise SQLiteValueReadError(exc.code) from None
        except sqlite3.DatabaseError as exc:
            code = progress_error.code if progress_error else (
                "cell_byte_limit" if getattr(exc, "sqlite_errorcode", None) == sqlite3.SQLITE_TOOBIG else "sqlite_error")
            self._summary["error_code"] = code
            raise SQLiteValueReadError(code) from None
        except SQLiteValueReadError as exc:
            self._summary["error_code"] = exc.code
            raise
        except OSError:
            self._summary["error_code"] = "source_io_error"
            raise SQLiteValueReadError("source_io_error") from None


def _validate_scope(*, expected_size, expected_sha256, relative_path, table,
                    source_columns, schema, limits, cancelled):
    if (type(expected_size) is not int or expected_size < 0 or not valid_digest(expected_sha256)
            or type(limits) is not SQLiteValueLimits or not callable(cancelled)):
        raise SQLiteValueReadError("invalid_identity")
    try:
        if (type(table) is not str or not table or "\0" in table
                or type(source_columns) is not tuple or not source_columns
                or any(type(c) is not str or not c or "\0" in c for c in source_columns)
                or len(set(source_columns)) != len(source_columns)
                or type(schema) is not UnorderedSchema or len(schema.columns) != len(source_columns)):
            raise ValueError()
        object_id = source_object_id(relative_path=relative_path, archive_chain=[], object_name=table, carrier="sqlite")
        maps = allocate_columns(list(source_columns), object_id=object_id)
        if schema.source_object_id != object_id or any(c.column_key != m.identity for c, m in zip(schema.columns, maps, strict=True)):
            raise ValueError()
    except (TypeError, ValueError):
        raise SQLiteValueReadError("invalid_scope") from None
    if len(source_columns) > limits.max_columns:
        raise SQLiteValueReadError("column_limit")


@contextmanager
def open_sqlite_values(path, *, expected_size, expected_sha256, relative_path,
                       table, source_columns, schema, limits=SQLiteValueLimits(),
                       cancelled=lambda: False):
    """Yield a closeable native-value iterator; no completion on early abandonment."""
    _validate_scope(expected_size=expected_size, expected_sha256=expected_sha256,
        relative_path=relative_path, table=table, source_columns=source_columns,
        schema=schema, limits=limits, cancelled=cancelled)
    stream = _ValueRows(Path(path), expected_size, expected_sha256, table, source_columns, schema, limits, cancelled)
    try:
        yield stream
    finally:
        stream.close()


class _BatchSource:
    """Private lifetime owner; only the batch bridge consumes provisional rows.

    No free skip-hash option on the public reader. A context exit verifies the
    entire stationary file, and a failed/abandoned batch returns no answer.
    """
    def __init__(self, path, expected_size, expected_sha256, cancelled, max_seconds, *, read_cache=None):
        require_read_cache(read_cache)
        self.read_cache = read_cache
        self.path = Path(path)
        self.expected_size, self.expected_sha256 = expected_size, expected_sha256
        self.cancelled, self.max_seconds = cancelled, max_seconds
        self.active = self.complete = False
        self._open_stream = None

    def guard(self):
        if not self.active:
            raise SQLiteValueReadError("batch_closed")
        self._check_cancel_and_time()

    def _check_cancel_and_time(self):
        try:
            stopped = self.cancelled()
        except Exception as error:
            raise SQLiteValueReadError("input_error") from error
        if type(stopped) is not bool:
            raise SQLiteValueReadError("input_error")
        if stopped:
            raise SQLiteValueReadError("cancelled")
        if time.monotonic() - self._start >= self.max_seconds:
            raise SQLiteValueReadError("time_limit")

    def check_finished(self):
        if not self.complete or self.active:
            raise SQLiteValueReadError("batch_incomplete")
        self._check_cancel_and_time()

    def _verify(self):
        self.guard()
        if _identity(_checked_stat(self.path)) != self.identity:
            raise SQLiteValueReadError("source_changed")
        result = (_hash(self.path, self.guard) if self.read_cache is None else
                  self.read_cache.hash_file(self.path, guard=self.guard))
        if result != self.expected_sha256 or _identity(_checked_stat(self.path)) != self.identity:
            raise SQLiteValueReadError("source_changed")
        self.guard()
        return result

    def __enter__(self):
        self._start = time.monotonic()
        self.active = True
        try:
            self.guard()
            before = _checked_stat(self.path)
            if before.st_size != self.expected_size:
                raise SQLiteValueReadError("identity_mismatch")
            self.identity = _identity(before)
            self.before_hash = self._verify()
            return self
        except BaseException:
            self.active = False
            raise

    @contextmanager
    def open(self, *, table, source_columns, schema, limits):
        self.guard()
        if self._open_stream is not None:
            raise SQLiteValueReadError("batch_concurrency")
        stream = _ValueRows(self.path, self.expected_size, self.expected_sha256,
            table, source_columns, schema, limits, self.cancelled, batch=self)
        self._open_stream = stream
        try:
            yield stream
            if not stream.summary.get("values_complete", False):
                raise SQLiteValueReadError("batch_incomplete")
        finally:
            stream.close()
            self._open_stream = None

    def __exit__(self, kind, value, traceback):
        try:
            if kind is None:
                if self._open_stream is not None:
                    raise SQLiteValueReadError("batch_incomplete")
                self.after_hash = self._verify()
                self.complete = True
        finally:
            self.active = False

"""Bounded schema-only observation of an identity-bound, stationary snapshot.

This is NOT a value reader, integrity checker, importer or approved contract.
Original DDL is evidence, never executed. Views/virtual tables remain pending.
The caller must supply a read-only snapshot mount and prevent concurrent writers.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import stat
import time


class SQLiteDiagnosticError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class SQLiteLimits:
    max_file_bytes: int = 1024 * 1024 * 1024
    max_objects: int = 10000
    max_metadata_rows: int = 200000
    max_output_bytes: int = 16 * 1024 * 1024
    max_vm_steps: int = 2000000
    max_seconds: int = 120

    def __post_init__(self):
        if any(type(value) is not int or value <= 0 for value in vars(self).values()):
            raise ValueError("SQLite budgets must be positive integers")


def _checked_stat(path):
    try:
        if not path.is_absolute() or any(part.is_symlink() for part in (path, *path.parents)):
            raise SQLiteDiagnosticError("unsafe_path")
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise SQLiteDiagnosticError("unsafe_path")
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = path.with_name(path.name + suffix)
            if sidecar.exists() or sidecar.is_symlink():
                raise SQLiteDiagnosticError("sidecar_present")
        return info
    except OSError:
        raise SQLiteDiagnosticError("unsafe_path") from None


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _hash(path, guard):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            guard()
            digest.update(chunk)
    return digest.hexdigest()


_READ_PRAGMAS = frozenset((
    "query_only", "trusted_schema", "table_xinfo", "index_list", "index_xinfo",
    "foreign_key_list",
))


def _authorize(action, first, second, database, origin):
    if origin is not None:  # Never execute a source view/trigger.
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        return (sqlite3.SQLITE_OK if database == "main" and first in
                ("sqlite_master", "sqlite_schema") else sqlite3.SQLITE_DENY)
    if action == sqlite3.SQLITE_PRAGMA:
        return (sqlite3.SQLITE_OK if first in _READ_PRAGMAS and
                (first not in ("query_only", "trusted_schema") or second is None)
                else sqlite3.SQLITE_DENY)
    return sqlite3.SQLITE_DENY


@contextmanager
def _metadata_connection(path):
    # immutable disables journal/lock handling, appropriate ONLY for the caller's
    # stationary read-only snapshot; identity/hash checks do not create atomicity.
    db = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True, timeout=1)
    try:
        db.enable_load_extension(False)
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        if db.execute("PRAGMA query_only").fetchone() != (1,) or \
                db.execute("PRAGMA trusted_schema").fetchone() != (0,):
            raise SQLiteDiagnosticError("readonly_settings_unavailable")
        db.set_authorizer(_authorize)
        yield db
    finally:
        db.close()


def inspect_sqlite_structure(path, *, expected_size, expected_sha256,
                             limits=SQLiteLimits(), cancelled=lambda: False):
    """Preserve every sqlite_schema entry; no business SELECT/count/view execution."""
    path = Path(path)
    if type(expected_size) is not int or expected_size < 0 or not isinstance(
            expected_sha256, str) or not re.fullmatch("[0-9a-f]{64}", expected_sha256):
        raise SQLiteDiagnosticError("invalid_identity")
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
    metadata_rows = 0
    output_bytes = 0
    vm_steps = 0
    progress_error = None

    def progress():
        nonlocal vm_steps, progress_error
        vm_steps += 1
        try:
            guard()
            if vm_steps > limits.max_vm_steps:
                raise SQLiteDiagnosticError("vm_limit")
            return 0
        except SQLiteDiagnosticError as exc:
            progress_error = exc
            return 1

    def rows(db, sql):
        nonlocal metadata_rows, output_bytes
        cursor = db.execute(sql)
        names = [col[0] for col in cursor.description]
        result = []
        for values in cursor:
            guard()
            metadata_rows += 1
            output_bytes += len(json.dumps(values, ensure_ascii=False).encode("utf-8"))
            if metadata_rows > limits.max_metadata_rows:
                raise SQLiteDiagnosticError("metadata_limit")
            if output_bytes > limits.max_output_bytes:
                raise SQLiteDiagnosticError("output_limit")
            result.append(dict(zip(names, values)))
        return result

    def pragma(db, name, object_name):
        # SQL string quoting, not identifier interpolation; schema fixed to main.
        literal = "'" + object_name.replace("'", "''") + "'"
        return rows(db, f"PRAGMA main.{name}({literal})")

    try:
        with _metadata_connection(path) as db:
            db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, limits.max_output_bytes)
            db.set_progress_handler(progress, 1)
            objects = rows(db, "SELECT type,name,tbl_name,rootpage,sql "
                           "FROM main.sqlite_schema ORDER BY type,name COLLATE BINARY")
            if len(objects) > limits.max_objects:
                raise SQLiteDiagnosticError("object_limit")
            for obj in objects:
                obj.update(columns=None, indexes=None, foreign_keys=None)
                if obj["type"] == "view":
                    obj["detail_status"] = "PENDING_VIEW_METADATA"
                elif obj["type"] == "table" and re.match(
                        r"\s*CREATE\s+VIRTUAL\s+TABLE\b", obj["sql"] or "", re.I):
                    obj["detail_status"] = "PENDING_VIRTUAL_TABLE"
                elif obj["type"] == "table":
                    obj["detail_status"] = "TABLE_METADATA_OBSERVED"
                    obj["columns"] = pragma(db, "table_xinfo", obj["name"])
                    obj["foreign_keys"] = pragma(db, "foreign_key_list", obj["name"])
                    obj["indexes"] = pragma(db, "index_list", obj["name"])
                    for idx in obj["indexes"]:
                        idx["columns"] = pragma(db, "index_xinfo", idx["name"])
                else:
                    obj["detail_status"] = "DDL_ONLY"
    except sqlite3.DatabaseError as exc:
        if progress_error is not None:
            raise progress_error from None
        if getattr(exc, "sqlite_errorcode", None) == sqlite3.SQLITE_TOOBIG:
            raise SQLiteDiagnosticError("output_limit") from None
        raise SQLiteDiagnosticError("sqlite_error") from None
    after = _checked_stat(path)
    sha_after = _hash(path, guard)
    if _identity(before) != _identity(after) or \
            _identity(before) != _identity(_checked_stat(path)) or sha_after != sha_before:
        raise SQLiteDiagnosticError("source_changed")
    result = {
        "format": "xiangrugu.sqlite-structure-observation.v1",
        "status": "STRUCTURE_OBSERVED", "catalog_complete": True,
        "table_metadata_complete": all(obj["detail_status"] != "PENDING_VIRTUAL_TABLE"
                                       for obj in objects),
        "all_object_details_complete": not any(obj["detail_status"].startswith("PENDING")
                                              for obj in objects),
        "business_rows_read": 0, "values_verified": False, "import_approved": False,
        "source_size": before.st_size, "source_sha256_before": sha_before,
        "source_sha256_after": sha_after, "sqlite_version": sqlite3.sqlite_version,
        "objects": objects,
        "limitations": [
            "Views/virtual tables: DDL only; field/value interpretation remains pending.",
            "Constraints retain original DDL, foreign keys and indexes; no execution.",
            "Declared types are not storage-type/value contracts or integrity checks.",
            "Requires a stationary read-only snapshot; pre/post hashes are not atomicity.",
        ],
    }
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > limits.max_output_bytes:
        raise SQLiteDiagnosticError("output_limit")
    return result

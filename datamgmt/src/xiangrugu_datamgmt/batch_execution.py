"""Synthetic-only batch wrapper. This is not a real-source authorization gate."""
from dataclasses import fields
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from .config import load_config
from .snapshots import digest, verify_snapshot, write_json_exclusive
from .sqlite_expectations import summarize_sqlite_batch
from .sqlite_values import SQLiteValueLimits, _validate_scope
from .unordered_values import UnorderedColumn, UnorderedSchema, UnorderedLimits


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


@lru_cache(maxsize=32)
def _metadata_path_chain(path):
    # Path objects contain lexical names only; filesystem state is never cached.
    return (path, *path.parents)


def read_metadata(path):
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in _metadata_path_chain(path)):
        raise ValueError("metadata_path_or_budget")
    current = path.stat()
    if not stat.S_ISREG(current.st_mode) or current.st_size > 1024**2:
        raise ValueError("metadata_path_or_budget")
    with path.open("rb") as stream:
        raw = stream.read(1024**2+1)
    if len(raw) > 1024**2:
        raise ValueError("metadata_budget")
    return raw


def _json(raw):
    return json.loads(raw, object_pairs_hook=_unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))


def _check_cancel(cancelled):
    if cancelled():
        raise ValueError("cancelled")


def execute_batch(request, *, cancelled=lambda: False):
    """Verify a private artificial snapshot, return an fsynced incomplete path.

    All input paths must be under the explicitly declared synthetic root; the
    configured authority is a never-read artificial path under the same root.
    The supervisor owns final publication, so failed monitoring cannot approve
    a result even if the worker has already completed its source hashes.
    """
    keys = {"roots", "snapshot_id", "relative_path", "expected_size", "expected_sha256",
        "certificate", "certificate_sha256", "manifest_sha256", "output", "image_id",
        "git_revision", "rule_id", "scope_file", "scope_sha256", "scratch_parent",
        "synthetic_root", "synthetic_only", "roots_sha256", "budget_file", "budget_sha256"}
    if type(request) is not dict or request.keys() != keys or request["synthetic_only"] is not True:
        raise ValueError("synthetic_request")
    root = Path(request["synthetic_root"])
    if not root.is_absolute() or root.resolve(strict=True) != root:
        raise ValueError("synthetic_root")
    paths = {key: Path(request[key]) for key in
        ("roots", "certificate", "scope_file", "budget_file", "output", "scratch_parent")}
    for path in paths.values():
        if (not path.is_absolute() or root not in path.parents
                or any(p.is_symlink() for p in (path, *path.parents))):
            raise ValueError("synthetic_path")
    if len(set(paths.values())) != len(paths):
        raise ValueError("path_alias")
    output = paths["output"]
    stage = output.with_name("." + output.name + ".incomplete")
    if output.exists() or stage.exists():
        raise FileExistsError("output_exists")
    if output.parent.resolve(strict=True) != output.parent:
        raise ValueError("output_path")
    inputs = {}
    for key, hash_key in (("roots", "roots_sha256"), ("certificate", "certificate_sha256"),
                          ("scope_file", "scope_sha256"), ("budget_file", "budget_sha256")):
        raw = read_metadata(paths[key])
        if hashlib.sha256(raw).hexdigest() != request[hash_key]:
            raise ValueError("input_identity")
        inputs[key] = raw
    config = load_config(paths["roots"], environ={})
    if (config.source.path != root / "authority-never-read"
            or root not in config.snapshot_root.parents):
        raise ValueError("synthetic_config")
    snapshot_id = request["snapshot_id"]
    relative = request["relative_path"]
    if (type(snapshot_id) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", snapshot_id)
            or type(relative) is not str or not relative or "\\" in relative
            or any(p in ("", ".", "..") for p in relative.split("/"))):
        raise ValueError("source_identity")
    snapshot = config.snapshot_root / snapshot_id
    if any(snapshot == p or snapshot in p.parents for p in (output, paths["scratch_parent"])):
        raise ValueError("output_path")
    if (not re.fullmatch(r"sha256:[0-9a-f]{64}", request["image_id"])
            or not re.fullmatch(r"[0-9a-f]{40}", request["git_revision"])):
        raise ValueError("runtime_identity")
    selected = dict(path=relative, kind="file", size=request["expected_size"], sha256=request["expected_sha256"])
    certificate = _json(inputs["certificate"])
    if (certificate["version"] != 1 or certificate["status"] != "VERIFIED"
            or certificate["snapshot_id"] != snapshot_id
            or certificate["source_path"] != str(config.source.path)
            or digest(certificate["members"]) != request["manifest_sha256"]
            or certificate["manifest_sha256"] != request["manifest_sha256"]
            or [m for m in certificate["members"] if m["path"] == relative] != [selected]):
        raise ValueError("certificate_scope")
    scope = _json(inputs["scope_file"])
    if (scope.keys() != {"version", "source_read_authorized", "synthetic_data_authorized", "snapshot_id",
            "source", "rule_id", "postgresql_authorized", "ready_for_import", "bindings", "objects"}
            or type(scope["version"]) is not int or scope["version"] != 1
            or scope["source_read_authorized"] is not False or scope["synthetic_data_authorized"] is not True
            or scope["postgresql_authorized"] is not False or scope["ready_for_import"] is not False
            or scope["snapshot_id"] != snapshot_id or scope["rule_id"] != request["rule_id"]
            or scope["source"] != selected or type(scope["objects"]) is not list
            or not 1 <= len(scope["objects"]) <= 75):
        raise ValueError("scope_authority")
    budget = _json(inputs["budget_file"])
    if (budget.keys() != {"version", "synthetic_only", "max_seconds", "read_limits", "sort_limits"}
            or type(budget["version"]) is not int or budget["version"] != 1
            or budget["synthetic_only"] is not True or type(budget["max_seconds"]) is not int
            or not 1 <= budget["max_seconds"] <= 300
            or budget["read_limits"].keys() != {f.name for f in fields(SQLiteValueLimits)}
            or budget["sort_limits"].keys() != {f.name for f in fields(UnorderedLimits)}):
        raise ValueError("budget")
    read_limits = SQLiteValueLimits(**budget["read_limits"])
    sort_limits = UnorderedLimits(**budget["sort_limits"])
    if (read_limits.max_file_bytes > 1024**2 or read_limits.max_rows > 100000
            or read_limits.max_value_bytes > 256*1024**2 or read_limits.max_seconds > 300
            or sort_limits.max_temp_bytes > 64*1024**2 or sort_limits.chunk_bytes > 32*1024**2
            or sort_limits.max_stream_bytes > 256*1024**2 or sort_limits.max_seconds > 300):
        raise ValueError("synthetic_budget")
    objects, names, identities = [], set(), set()
    for obj in scope["objects"]:
        if (type(obj) is not dict or obj.keys() != {"source_object_id", "source_object_name", "source_columns", "columns"}
                or obj["source_object_name"] in names or obj["source_object_id"] in identities
                or type(obj["source_columns"]) is not list):
            raise ValueError("scope_object")
        names.add(obj["source_object_name"])
        identities.add(obj["source_object_id"])
        schema = UnorderedSchema(obj["source_object_id"], tuple(UnorderedColumn(**c) for c in obj["columns"]))
        _validate_scope(expected_size=request["expected_size"], expected_sha256=request["expected_sha256"],
            relative_path=relative, table=obj["source_object_name"], source_columns=tuple(obj["source_columns"]),
            schema=schema, limits=read_limits, cancelled=cancelled)
        if request["expected_size"] > read_limits.max_file_bytes or len(schema.columns) > sort_limits.max_columns:
            raise ValueError("synthetic_budget")
        objects.append(dict(table=obj["source_object_name"], source_columns=tuple(obj["source_columns"]),
                            schema=schema, read_limits=read_limits, sort_limits=sort_limits))
    _check_cancel(cancelled)
    verify_snapshot(snapshot, paths["certificate"], expected_source=config.source.path)
    _check_cancel(cancelled)
    result = summarize_sqlite_batch(snapshot / relative, expected_size=request["expected_size"],
        expected_sha256=request["expected_sha256"], relative_path=relative, objects=tuple(objects),
        scratch_parent=paths["scratch_parent"], cancelled=cancelled, max_seconds=budget["max_seconds"])
    if any(read_metadata(paths[k]) != raw for k, raw in inputs.items()):
        raise ValueError("metadata_changed")
    _check_cancel(cancelled)
    result.update(synthetic_only=True, full_snapshot_verified_this_run=True,
        scope_sha256=request["scope_sha256"], budget_sha256=request["budget_sha256"],
        roots_sha256=request["roots_sha256"], certificate_sha256=request["certificate_sha256"],
        manifest_sha256=request["manifest_sha256"], git_revision=request["git_revision"],
        image_id=request["image_id"], source_status="dirty", raw_values_emitted=False)
    write_json_exclusive(stage, result)
    _check_cancel(cancelled)
    return stage


def _publication_selection(authorized_source_mode, expected_request_sha256):
    if (authorized_source_mode not in ('artificial', 'project_snapshot')
            or (authorized_source_mode == 'artificial' and expected_request_sha256 is not None)
            or (authorized_source_mode == 'project_snapshot'
                and (type(expected_request_sha256) is not str
                     or re.fullmatch(r'[0-9a-f]{64}', expected_request_sha256) is None))):
        raise ValueError('controller_source_mode')


def publish_batch(staged, final, *, cancelled=lambda: False,
                  authorized_source_mode='artificial', expected_request_sha256=None):
    """No-clobber publication; leave incomplete evidence on any pre-link failure."""
    staged, final = Path(staged), Path(final)
    _publication_selection(authorized_source_mode, expected_request_sha256)
    raw = read_metadata(staged)
    result = _json(raw)
    mode_valid = (result.get('synthetic_only') is True
                  and result.get('source_mode', 'artificial') == 'artificial')
    if authorized_source_mode == 'project_snapshot':
        mode_valid = (result.get('synthetic_only') is False
                      and result.get('source_mode') == 'project_snapshot'
                      and result.get('execution_kind') == 'approved-readonly-batch-v1'
                      and result.get('controller_request_sha256') == expected_request_sha256)
    if (staged != final.with_name("." + final.name + ".incomplete")
            or final.parent.resolve(strict=True) != final.parent or final.is_symlink()
            or result.get("complete") is not True or not mode_valid
            or result.get("ready_for_import") is not False or result.get("postgresql_connected") is not False):
        raise ValueError("invalid_staging")
    with staged.open("rb") as stream:
        os.fsync(stream.fileno())
    # Persist the staging directory entry before linking the final name.
    fd = os.open(final.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    _check_cancel(cancelled)
    os.link(staged, final, follow_symlinks=False)
    # No fallible operation follows publication. The incomplete link is retained
    # deliberately. Final-name durability across power loss is not promised.

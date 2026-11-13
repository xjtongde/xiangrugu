"""Source-only draft fingerprints, never database equality or import approval."""
from dataclasses import asdict
import hashlib

from .sqlite_values import (SQLiteValueLimits, SQLiteValueReadError, open_sqlite_values,
                            _BatchSource, _validate_scope)
from .unordered_values import (UnorderedLimits, UnorderedValueError, header_bytes,
                               schema_bytes, trailer_bytes)
from .value_sort import SortWorkspace, sort_rows
from .read_cache import require_read_cache


def _summarize_rows(source, schema, workspace):
    ordered = sort_rows(schema, source, workspace=workspace, side="source")
    digest = hashlib.sha256(header_bytes(schema))
    for frame in ordered.iter_frames():
        workspace.check()
        digest.update(frame)
    digest.update(trailer_bytes(ordered.row_count))
    workspace.check()
    source_read = source.summary
    if (not (source_read["complete"] or source_read.get("values_complete", False))
            or not workspace.progress["source"].sort_complete):
        raise UnorderedValueError("input_error")
    return dict(expected_count=ordered.row_count, expected_sha256=digest.hexdigest(),
        field_count=ordered.field_count, stream_bytes=ordered.stream_bytes,
        source_read=source_read, schema_hash=hashlib.sha256(schema_bytes(schema)).hexdigest(),
        source_object_id=schema.source_object_id)


def summarize_sqlite(path, *, expected_size, expected_sha256, relative_path,
                     table, source_columns, schema, scratch_parent,
                     read_limits=SQLiteValueLimits(), sort_limits=UnorderedLimits(),
                     cancelled=lambda: False):
    """Return only after source exhaustion, global sorting and owned-file cleanup.

    Hash is an order-independent reproducibility reference, not a substitute
    for the eventual source/target comparison of actual bytes and multiplicity.
    The caller enforces a stationary read-only snapshot and batch resource caps.
    """
    with SortWorkspace(scratch_parent, sort_limits, cancelled=cancelled) as workspace:
        with open_sqlite_values(path, expected_size=expected_size,
                expected_sha256=expected_sha256, relative_path=relative_path,
                table=table, source_columns=source_columns, schema=schema,
                limits=read_limits, cancelled=cancelled) as source:
            result = _summarize_rows(source, schema, workspace)
    if not workspace.cleanup_complete:
        raise UnorderedValueError("cleanup_error")
    workspace.check()
    return dict(version=1, status="DRAFT_SOURCE_EXPECTATION",
        format="sqlite-unordered-values-v1", source_object_id=schema.source_object_id,
        **{key: value for key, value in result.items() if key != "source_object_id"},
        cleanup_complete=True,
        sort_stats=asdict(workspace.stats), read_limits=asdict(read_limits),
        sort_limits=asdict(sort_limits), postgresql_connected=False,
        ready_for_import=False, contract_frozen=False)


def summarize_sqlite_batch(path, *, expected_size, expected_sha256, relative_path,
                           objects, scratch_parent, cancelled=lambda: False,
                           max_seconds=7200, read_cache=None, progress=None):
    """Return an all-or-nothing source-only batch with two full file hashes.

    This API is not an authorization/CLI entry point. The caller must first
    verify the complete snapshot and approved scope/budget/input digests and
    enforce host monitoring plus a stationary read-only source window.
    """
    if progress is not None:
        progress('batch_preflight')
    require_read_cache(read_cache)
    if (type(objects) is not tuple or not 1 <= len(objects) <= 75
            or type(max_seconds) is not int or max_seconds <= 0):
        raise SQLiteValueReadError("invalid_scope")
    descriptions, names, identities = [], set(), set()
    # Validate EVERY description before hashing, querying, or creating scratch.
    for obj in objects:
        if (type(obj) is not dict or not {"table", "source_columns", "schema"} <= obj.keys()
                or obj.keys() - {"table", "source_columns", "schema", "read_limits", "sort_limits"}):
            raise SQLiteValueReadError("invalid_scope")
        read_limits = obj.get("read_limits", SQLiteValueLimits())
        sort_limits = obj.get("sort_limits", UnorderedLimits())
        _validate_scope(expected_size=expected_size, expected_sha256=expected_sha256,
            relative_path=relative_path, table=obj["table"], source_columns=obj["source_columns"],
            schema=obj["schema"], limits=read_limits, cancelled=cancelled)
        if expected_size > read_limits.max_file_bytes:
            raise SQLiteValueReadError("file_limit")
        if (type(sort_limits) is not UnorderedLimits
                or len(obj["source_columns"]) > sort_limits.max_columns
                or obj["table"] in names or obj["schema"].source_object_id in identities):
            raise SQLiteValueReadError("invalid_scope")
        names.add(obj["table"])
        identities.add(obj["schema"].source_object_id)
        descriptions.append((dict(obj), read_limits, sort_limits))
    results = []
    if progress is not None:
        progress('batch_digest_before')
    with _BatchSource(path, expected_size, expected_sha256, cancelled, max_seconds,
                      read_cache=read_cache) as batch:
        def sorting_guard():
            batch.guard()
            return False
        for index, (obj, read_limits, sort_limits) in enumerate(descriptions, 1):
            if progress is not None:
                progress('object_read_sort', object_index=index, completed_objects=len(results))
            batch.guard()
            with SortWorkspace(scratch_parent, sort_limits, cancelled=sorting_guard) as workspace:
                with batch.open(table=obj["table"], source_columns=obj["source_columns"],
                                schema=obj["schema"], limits=read_limits) as source:
                    result = _summarize_rows(source, obj["schema"], workspace)
            if not workspace.cleanup_complete:
                raise UnorderedValueError("cleanup_error")
            workspace.check()
            result.update(source_object_name=obj["table"], cleanup_complete=True,
                sort_stats=asdict(workspace.stats), read_limits=asdict(read_limits),
                sort_limits=asdict(sort_limits))
            results.append(result)
        if progress is not None:
            progress('batch_digest_after', completed_objects=len(results))
        batch.guard()
    # No partial results escape; object reads do NOT become standalone verified.
    for result in results:
        result["source_read"]["digest_scope"] = "verified_by_completed_batch"
    batch.check_finished()
    return dict(version=1, status="DRAFT_BATCH_SOURCE_EXPECTATIONS",
        complete=batch.complete, source_sha256_before=batch.before_hash,
        source_sha256_after=batch.after_hash, file_digest_passes=2,
        objects=results, postgresql_connected=False, ready_for_import=False,
        contract_frozen=False)

"""Approved source-only SQLite canary; no database access or raw values output."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal

from xiangrugu_datamgmt.config import load_config
from xiangrugu_datamgmt.snapshots import verify_snapshot, write_json_exclusive
from xiangrugu_datamgmt.sqlite_expectations import summarize_sqlite
from xiangrugu_datamgmt.sqlite_values import SQLiteValueLimits
from xiangrugu_datamgmt.unordered_values import UnorderedColumn, UnorderedSchema, UnorderedLimits

helpers = runpy.run_path(str(Path(__file__).with_name("inspect-sqlite-structure.py")))
read_metadata = helpers["read_metadata"]


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("scope_duplicate_key")
        result[key] = value
    return result


def prepare(args, *, cancelled=lambda: False):
    inputs = helpers["validate_probe_inputs"](args)
    scope_path = Path(args.scope_file)
    scope_raw = read_metadata(scope_path)
    if scope_path == inputs["output"]:
        raise ValueError("output_path")
    if hashlib.sha256(scope_raw).hexdigest() != args.scope_sha256:
        raise ValueError("scope_identity")
    scope = json.loads(scope_raw, object_pairs_hook=unique_keys)
    objects = scope["objects"]
    if (type(scope["version"]) is not int or scope["version"] != 1
            or scope["source_read_authorized"] is not True
            or scope["postgresql_authorized"] is not False
            or scope["ready_for_import"] is not False
            or scope["snapshot_id"] != args.snapshot_id or scope["rule_id"] != args.rule_id
            or scope["source"] != inputs["selected"] or not 1 <= len(objects) <= 3
            or len({o["source_object_id"] for o in objects}) != len(objects)
            or len({o["source_object_name"] for o in objects}) != len(objects)):
        raise ValueError("scope_authority")
    read_limits = SQLiteValueLimits(max_columns=19, max_rows=4000, max_cells=50000,
        max_cell_bytes=1024**2, max_value_bytes=8*1024**2, max_seconds=300)
    sort_limits = UnorderedLimits(max_rows=4000, max_columns=19,
        max_row_bytes=1024**2, max_stream_bytes=8*1024**2, chunk_bytes=2*1024**2,
        max_temp_bytes=64*1024**2, max_seconds=300)
    descriptions = [(o, UnorderedSchema(o["source_object_id"],
        tuple(UnorderedColumn(**c) for c in o["columns"]))) for o in objects]
    if sum(len(schema.columns) for _, schema in descriptions) > 19:
        raise ValueError("scope_column_budget")
    config = load_config(inputs["roots"], environ={})
    if cancelled():
        raise ValueError("cancelled")
    # Only the project snapshot is read: authority path is an identity string.
    verify_snapshot(inputs["snapshot"], inputs["certificate_path"], expected_source=config.source.path)
    results = []
    for obj, schema in descriptions:
        if cancelled():
            raise ValueError("cancelled")
        result = summarize_sqlite(inputs["snapshot"] / args.relative_path,
            expected_size=args.expected_size, expected_sha256=args.expected_sha256,
            relative_path=args.relative_path, table=obj["source_object_name"],
            source_columns=tuple(obj["source_columns"]), schema=schema,
            scratch_parent=Path(args.scratch_parent), read_limits=read_limits,
            sort_limits=sort_limits, cancelled=cancelled)
        result["source_object_name"] = obj["source_object_name"]
        results.append(result)
    if (cancelled() or read_metadata(inputs["roots"]) != inputs["roots_raw"]
            or read_metadata(inputs["certificate_path"]) != inputs["certificate_raw"]
            or read_metadata(scope_path) != scope_raw):
        raise ValueError("metadata_changed_or_cancelled")
    result = dict(version=1, status="DRAFT_SELECTED_SOURCE_EXPECTATIONS",
        generated_at=datetime.now(timezone.utc).isoformat(),
        git_revision=args.git_revision, image_id=args.image_id, source_status="dirty",
        snapshot_id=args.snapshot_id, rule_id=args.rule_id, source=inputs["selected"],
        snapshot_certificate_sha256=args.certificate_sha256,
        snapshot_manifest_sha256=args.manifest_sha256,
        scope_sha256=args.scope_sha256, bindings=scope["bindings"],
        roots_sha256=hashlib.sha256(inputs["roots_raw"]).hexdigest(),
        full_snapshot_verified_this_run=True, objects=results,
        business_rows_read=sum(o["expected_count"] for o in results),
        business_cells_read=sum(o["field_count"] for o in results),
        postgresql_connected=False, ready_for_import=False, contract_frozen=False,
        raw_values_emitted=False, disposition_retained="BLOCKED")
    # Persist a non-authoritative staged artifact first. Publish with an atomic
    # no-clobber link only after fsync succeeds. Keep the staging name for
    # recovery evidence: no fallible cleanup occurs after final publication.
    staging = inputs["output"].with_name("." + inputs["output"].name + ".incomplete")
    write_json_exclusive(staging, result)
    os.link(staging, inputs["output"], follow_symlinks=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("roots", "snapshot-id", "relative-path", "expected-sha256",
                 "certificate", "certificate-sha256", "manifest-sha256", "output",
                 "image-id", "git-revision", "rule-id", "scope-file", "scope-sha256",
                 "scratch-parent"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--expected-size", type=int, required=True)
    args = parser.parse_args()
    stopped = False
    def stop(signum, frame):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        result = prepare(args, cancelled=lambda: stopped)
        print(json.dumps({key: result[key] for key in
            ("status", "business_rows_read", "business_cells_read", "ready_for_import")}))
        return 0
    except Exception:
        # Do not emit source values, parser inputs or uncontrolled exception text.
        print(json.dumps(dict(status="SOURCE_EXPECTATION_FAILED", ready_for_import=False)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Create private artificial bytes and exercise the batch wrapper in an image."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import signal
import sqlite3

import yaml

from .batch_execution import execute_batch
from .identity import source_object_id
from .naming import allocate_columns
from .snapshots import digest, inventory, write_json_exclusive
from .sqlite_values import SQLiteValueLimits
from .unordered_values import UnorderedLimits


def build_fixture(root, *, image_id, git_revision):
    """Fixed two-table fixture, never accept a caller's source file or database."""
    root = Path(root)
    snapshot_id, relative = "artificial-v1", "artificial.sqlite"
    snapshot_root = root / "snapshots"
    snapshot = snapshot_root / snapshot_id
    snapshot.mkdir(parents=True, exist_ok=False)
    scratch = root / "scratch"
    scratch.mkdir(exist_ok=True)
    source = snapshot / relative
    objects = []
    with sqlite3.connect(source) as db:
        for name, values in (("artificial_values", [None, "", "茶香", "茶香", " z "]), ("empty_values", [])):
            db.execute(f'CREATE TABLE "{name}"(v TEXT)')
            db.executemany(f'INSERT INTO "{name}" VALUES (?)', [(v,) for v in values])
            identity = source_object_id(relative_path=relative, archive_chain=[], object_name=name, carrier="sqlite")
            key = allocate_columns(["v"], object_id=identity)[0].identity
            objects.append(dict(source_object_id=identity, source_object_name=name, source_columns=["v"],
                columns=[dict(source_ordinal=0, column_key=key, pg_type="text", allow_null_value=True)]))
    authority = str(root / "authority-never-read")
    roots = root / "roots.yaml"
    roots.write_text(yaml.safe_dump(dict(version=1,
        roots={"usedata": dict(path=authority, host="synthetic", role="authoritative-source")},
        target=dict(instance="pg32b", host="unused", port=5433, database="xiangrugu", user="unused"),
        deployment={"source_snapshots": dict(container_root=str(snapshot_root), container_evidence_root=str(root))})),
        encoding="utf-8")
    members = inventory(snapshot)
    certificate = dict(version=1, status="VERIFIED", snapshot_id=snapshot_id, source_path=authority,
                       members=members, manifest_sha256=digest(members))
    selected = members[0]
    scope = dict(version=1, source_read_authorized=False, synthetic_data_authorized=True,
        snapshot_id=snapshot_id, source=selected, rule_id="artificial-batch", postgresql_authorized=False,
        ready_for_import=False, bindings={"fixture": "fixed-two-table-v1"}, objects=objects)
    budget = dict(version=1, synthetic_only=True, max_seconds=60,
        read_limits=asdict(SQLiteValueLimits(max_rows=100, max_file_bytes=1048576)),
        sort_limits=asdict(UnorderedLimits(max_rows=100, max_temp_bytes=64*1024**2)))
    documents = {"certificate": certificate, "scope_file": scope, "budget_file": budget}
    request = dict(roots=str(roots), roots_sha256=hashlib.sha256(roots.read_bytes()).hexdigest(),
        snapshot_id=snapshot_id, relative_path=relative, expected_size=selected["size"], expected_sha256=selected["sha256"],
        manifest_sha256=certificate["manifest_sha256"], output=str(root / "batch.json"),
        image_id=image_id, git_revision=git_revision, rule_id="artificial-batch", scratch_parent=str(scratch),
        synthetic_root=str(root), synthetic_only=True)
    for key, doc in documents.items():
        path = root / (key + ".json")
        write_json_exclusive(path, doc)
        request[key] = str(path)
        hash_key = {"certificate": "certificate_sha256", "scope_file": "scope_sha256", "budget_file": "budget_sha256"}[key]
        request[hash_key] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json_exclusive(root / "request.json", request)
    return request


def run(root, *, image_id, git_revision, cancelled=lambda: False):
    request = build_fixture(root, image_id=image_id, git_revision=git_revision)
    return execute_batch(request, cancelled=cancelled)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--git-revision", required=True)
    args = parser.parse_args()
    stopped = False
    def stop(signum, frame):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        run(args.root, image_id=args.image_id, git_revision=args.git_revision, cancelled=lambda: stopped)
        print(json.dumps(dict(status="ARTIFICIAL_BATCH_STAGED", ready_for_import=False)))
        return 0
    except Exception:
        print(json.dumps(dict(status="ARTIFICIAL_BATCH_FAILED", ready_for_import=False)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Development-only schema evidence probe, executed from a candidate test image.

One explicitly selected project snapshot member; no NAS or PostgreSQL access.
No business rows, source DDL execution, formal contract update or import.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import signal
import stat

from xiangrugu_datamgmt.config import load_config
from xiangrugu_datamgmt.snapshots import digest, write_json_exclusive
from xiangrugu_datamgmt.sqlite_diagnostic import inspect_sqlite_structure


def read_metadata(path, maximum=1024 * 1024):
    if not path.is_absolute() or any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("metadata_path")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
        raise ValueError("metadata_budget")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("metadata_budget")
    return raw


def validate_probe_inputs(args):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", args.snapshot_id):
        raise ValueError("snapshot_id")
    if (not args.relative_path or "\\" in args.relative_path or
            any(part in ("", ".", "..") for part in args.relative_path.split("/"))):
        raise ValueError("relative_path")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.image_id) or \
            not re.fullmatch(r"[0-9a-f]{40}", args.git_revision):
        raise ValueError("runtime_identity")
    roots = Path(args.roots)
    roots_raw = read_metadata(roots)
    config = load_config(roots, environ={})  # Never read credentials/environment.
    snapshot = config.snapshot_root / args.snapshot_id
    output = Path(args.output)
    if (not output.is_absolute() or
            output.parent.resolve(strict=True) != output.parent or
            any(part.is_symlink() for part in (output, *output.parents)) or
            output == config.snapshot_root or config.snapshot_root in output.parents or
            output == config.source.path or config.source.path in output.parents or
            output == roots or output == Path(args.certificate)):
        raise ValueError("output_path")
    if output.exists():
        raise FileExistsError("output_exists")
    certificate_path = Path(args.certificate)
    certificate_raw = read_metadata(certificate_path)
    if hashlib.sha256(certificate_raw).hexdigest() != args.certificate_sha256:
        raise ValueError("certificate_identity")
    certificate = json.loads(certificate_raw)
    members = certificate["members"]
    if (certificate["version"] != 1 or certificate["status"] != "VERIFIED" or
            certificate["snapshot_id"] != args.snapshot_id or
            certificate["source_path"] != str(config.source.path) or
            digest(members) != certificate["manifest_sha256"] or
            certificate["manifest_sha256"] != args.manifest_sha256 or
            len({member["path"] for member in members}) != len(members)):
        raise ValueError("certificate_scope")
    selected = dict(path=args.relative_path, kind="file", size=args.expected_size,
                    sha256=args.expected_sha256)
    if [member for member in members if member["path"] == args.relative_path] != [selected]:
        raise ValueError("certificate_member")
    return dict(snapshot=snapshot, output=output, roots=roots, roots_raw=roots_raw,
                certificate_path=certificate_path, certificate_raw=certificate_raw,
                selected=selected)


def prepare(args, *, cancelled=lambda: False):
    inputs = validate_probe_inputs(args)
    snapshot, output, roots = inputs["snapshot"], inputs["output"], inputs["roots"]
    roots_raw, certificate_raw = inputs["roots_raw"], inputs["certificate_raw"]
    certificate_path, selected = inputs["certificate_path"], inputs["selected"]
    observation = inspect_sqlite_structure(snapshot / args.relative_path,
        expected_size=args.expected_size, expected_sha256=args.expected_sha256,
        cancelled=cancelled)
    if read_metadata(certificate_path) != certificate_raw or read_metadata(roots) != roots_raw:
        raise ValueError("metadata_changed")
    result = dict(version=1, status="DRAFT_STRUCTURE_OBSERVATION",
        generated_at=datetime.now(timezone.utc).isoformat(),
        git_revision=args.git_revision, image_id=args.image_id, source_status="dirty",
        rule_id=args.rule_id, source=selected, snapshot_id=args.snapshot_id,
        snapshot_certificate_sha256=args.certificate_sha256,
        snapshot_manifest_sha256=args.manifest_sha256,
        roots_sha256=hashlib.sha256(roots_raw).hexdigest(),
        full_snapshot_verified_this_run=False,
        selected_member_verified_before_and_after=True,
        source_sqlite_connected=True, postgresql_connected=False, source_ddl_executed=False,
        ready_for_import=False, contract_frozen=False, formal_contract_modified=False,
        disposition_retained="BLOCKED", observation=observation)
    write_json_exclusive(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("roots", "snapshot-id", "relative-path", "expected-sha256",
                 "certificate", "certificate-sha256", "manifest-sha256", "output",
                 "image-id", "git-revision", "rule-id"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--expected-size", type=int, required=True)
    args = parser.parse_args()
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    result = prepare(args, cancelled=lambda: stopped)
    counts = {}
    for obj in result["observation"]["objects"]:
        counts[obj["type"]] = counts.get(obj["type"], 0) + 1
    print(json.dumps(dict(status=result["status"], catalog_counts=counts,
                         business_rows_read=0, ready_for_import=False)))


if __name__ == "__main__":
    main()

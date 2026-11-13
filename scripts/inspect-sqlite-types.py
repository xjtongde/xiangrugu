"""Approved selected-table type diagnosis; no import, no raw text output."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import signal

from xiangrugu_datamgmt.snapshots import write_json_exclusive
from xiangrugu_datamgmt.sqlite_profile import ProfileLimits, profile_sqlite

helpers = runpy.run_path(str(Path(__file__).with_name("inspect-sqlite-structure.py")))
read_metadata = helpers["read_metadata"]
validate_probe_inputs = helpers["validate_probe_inputs"]


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("budget_duplicate_key")
        result[key] = value
    return result


def read_profile_budget(args, roles, output):
    path_arg = getattr(args, "budget_file", None)
    approved_sha = roles.get("profile_budget_sha256")
    if path_arg is None and approved_sha is None:
        return ProfileLimits(), None, None
    if path_arg is None or approved_sha is None:
        raise ValueError("budget_authority")
    path = Path(path_arg)
    if path == output:
        raise ValueError("output_path")
    raw = read_metadata(path)
    if hashlib.sha256(raw).hexdigest() != approved_sha:
        raise ValueError("budget_identity")
    document = json.loads(raw, object_pairs_hook=unique_keys)
    caps = dict(vars(ProfileLimits()))
    caps.update(max_rows=2000000, max_cells=128000000,
        max_total_value_bytes=1073741824, max_vm_steps=1000000000, max_seconds=900)
    if (not isinstance(document, dict) or set(document) != {"version", "limits"} or
            type(document["version"]) is not int or document["version"] != 1 or
            not isinstance(document["limits"], dict) or set(document["limits"]) != set(caps) or
            any(type(value) is not int or not 0 < value <= caps[key]
                for key, value in document["limits"].items())):
        raise ValueError("budget_scope")
    return ProfileLimits(**document["limits"]), path, raw


def prepare(args, *, cancelled=lambda: False):
    inputs = validate_probe_inputs(args)
    roles_path = Path(args.roles_file)
    roles_raw = read_metadata(roles_path)
    if hashlib.sha256(roles_raw).hexdigest() != args.roles_sha256:
        raise ValueError("decision_identity")
    roles = json.loads(roles_raw)
    if (roles["roles_approved"] is not True or roles["profile_read_authorized"] is not True or
            roles["raw_text_or_blob_output_authorized"] is not False or
            roles["source_identity"] != inputs["selected"] or
            roles["source_version"] != args.snapshot_id or
            roles["rule_id"] != args.rule_id or
            any(roles[flag] is not False for flag in ("type_mapping_approved",
                "value_contract_approved", "target_mapping_approved", "ready_for_import", "contract_frozen"))):
        raise ValueError("decision_scope")
    if inputs["output"] == roles_path:
        raise ValueError("output_path")
    limits, budget_path, budget_raw = read_profile_budget(args, roles, inputs["output"])
    profile = profile_sqlite(inputs["snapshot"] / args.relative_path,
        expected_size=args.expected_size, expected_sha256=args.expected_sha256,
        tables=roles["profile_scope"], limits=limits, cancelled=cancelled)
    if (read_metadata(roles_path) != roles_raw or
            read_metadata(inputs["certificate_path"]) != inputs["certificate_raw"] or
            read_metadata(inputs["roots"]) != inputs["roots_raw"] or
            (budget_path is not None and read_metadata(budget_path) != budget_raw)):
        raise ValueError("metadata_changed")
    result = dict(version=1, status="DRAFT_SELECTED_TABLE_TYPE_PROFILE",
        generated_at=datetime.now(timezone.utc).isoformat(),
        git_revision=args.git_revision, image_id=args.image_id, source_status="dirty",
        source=inputs["selected"], rule_id=args.rule_id, source_version=args.snapshot_id,
        roles_decision_sha256=args.roles_sha256, certificate_sha256=args.certificate_sha256,
        profile_budget_sha256=roles.get("profile_budget_sha256"), profile_limits=vars(limits),
        snapshot_manifest_sha256=args.manifest_sha256,
        roots_sha256=hashlib.sha256(inputs["roots_raw"]).hexdigest(),
        full_snapshot_verified_this_run=False, selected_member_verified_before_and_after=True,
        source_sqlite_connected=True, postgresql_connected=False, raw_text_or_blob_emitted=False,
        type_mapping_approved=False, value_contract_approved=False,
        ready_for_import=False, contract_frozen=False, disposition_retained="BLOCKED", profile=profile)
    write_json_exclusive(inputs["output"], result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("roots", "snapshot-id", "relative-path", "expected-sha256",
                 "certificate", "certificate-sha256", "manifest-sha256", "output",
                 "image-id", "git-revision", "rule-id", "roles-file", "roles-sha256"):
        parser.add_argument("--"+name, required=True)
    parser.add_argument("--expected-size", type=int, required=True)
    parser.add_argument("--budget-file")
    args = parser.parse_args()
    stopped = False
    def stop(signum, frame):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    result = prepare(args, cancelled=lambda: stopped)
    print(json.dumps(dict(status=result["status"],
        table_counts={t["name"]: t["row_count"] for t in result["profile"]["tables"]},
        rows_read=result["profile"]["rows_read"], cells_read=result["profile"]["cells_read"],
        ready_for_import=False)))


if __name__ == "__main__":
    main()

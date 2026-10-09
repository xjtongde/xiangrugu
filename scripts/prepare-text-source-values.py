"""Development-only evidence probe; run from the candidate test image.

No NAS or database access. Roots and inputs are explicit command arguments.
Output is an exclusive non-executable draft, never a release contract.
"""
import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import stat

import yaml

from xiangrugu_datamgmt.canonical import ValueLimits, schema_bytes
from xiangrugu_datamgmt.snapshots import digest, write_json_exclusive
from xiangrugu_datamgmt.source_text import read_utf8_tsv
from xiangrugu_datamgmt.text_values import schema_from_approved, summarize_text_values

RULES = {"m008002", "m008003", "m008004", "m004812", "m006642"}


def read_regular(root, relative, maximum):
    """Reject all symlink components; bounded read, no path fallback."""
    if not relative or any(part in ("", ".", "..") for part in relative.split("/")):
        raise ValueError("path")
    path = root
    for part in relative.split("/"):
        path = path / part
        if path.is_symlink():
            raise ValueError("symlink")
    if root.resolve(strict=True) != root or path.resolve(strict=True).parent != path.parent:
        raise ValueError("path")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum:
            raise ValueError("file_budget")
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        raise ValueError("file_budget")
    return raw


def independent_reference(raw, obj, decision):
    """stdlib CSV + hand-written v1 framing, independent of canonical helpers."""
    text = raw.decode(decision["codec"], errors="strict")
    records = tuple(tuple(row) for row in csv.reader(
        io.StringIO(text, newline=""), delimiter="\t", quotechar='"', doublequote=True,
        escapechar="\\" if decision["backslash_escape"] else None, strict=True,
        skipinitialspace=False,
    ))
    parsed = read_utf8_tsv(raw, bom_as_signature=decision["bom_as_signature"],
                           backslash_escape=decision["backslash_escape"])
    if records != parsed:
        raise ValueError("independent_field_difference")
    columns = [[col["column_id"], col["target_name"], "text", False]
               for col in obj["source_columns"]]
    columns.append(["derived:__src_rownum", "__src_rownum", "bigint", False])
    column_json = json.dumps(columns, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    hasher = hashlib.sha256(b"XRGVALUE\x00\x01" + bytes.fromhex(obj["source_object_id"])
                            + hashlib.sha256(column_json).digest())
    stream_bytes = 74
    fields = 0
    for ordinal, row in enumerate(records[1:], 1):
        payload = bytearray()
        for value in row:
            encoded = value.encode("utf-8", errors="strict")
            payload.extend(b"\x01" + len(encoded).to_bytes(8, "big") + encoded)
        payload.extend(b"\x02" + ordinal.to_bytes(8, "big", signed=True))
        frame = b"\x52" + (len(row)+1).to_bytes(4, "big") + len(payload).to_bytes(8, "big") + payload
        hasher.update(frame)
        stream_bytes += len(frame)
        fields += len(row) + 1
    count = len(records) - 1
    hasher.update(b"\x45" + count.to_bytes(8, "big"))
    old = hashlib.sha256()
    for row in records:
        old.update((json.dumps(row, ensure_ascii=True, separators=(",", ":"))+"\n").encode("ascii"))
    if old.hexdigest() != obj["source_value_evidence"]["ordered_strings_sha256_including_header"]:
        raise ValueError("prior_reading_evidence")
    return dict(row_count=count, field_count=fields, stream_bytes=stream_bytes+9,
                sha256=hasher.hexdigest()), fields - count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("snapshot", "inputs", "certificate", "output", "image-id", "git-revision"):
        parser.add_argument("--"+name, required=True)
    args = parser.parse_args()
    snapshot, inputs = Path(args.snapshot), Path(args.inputs)
    certificate_raw = Path(args.certificate).read_bytes()
    certificate = json.loads(certificate_raw)
    projection_raw = read_regular(inputs, "text-schema-approved.draft.yaml", 1048576)
    projection = json.loads(projection_raw)
    if (certificate["status"] != "VERIFIED"
            or certificate["snapshot_id"] != projection["source_version"]
            or snapshot.name != certificate["snapshot_id"]
            or digest(certificate["members"]) != certificate["manifest_sha256"]
            or certificate["manifest_sha256"] != projection["snapshot_manifest_sha256"]
            or projection["contract_frozen"] is not False
            or projection["ready_for_import"] is not False
            or len(projection["objects"]) != 5
            or {obj["rule_id"] for obj in projection["objects"]} != RULES):
        raise ValueError("snapshot_or_scope")
    decisions = {}
    input_hashes = {"text-schema-approved.draft.yaml": hashlib.sha256(projection_raw).hexdigest()}
    for filename in projection["reading_decisions_files"]:
        decision_raw = read_regular(inputs, filename, 1048576)
        document = yaml.safe_load(decision_raw)
        if (document["reading_semantics_approved"] is not True
                or document["source_version"] != projection["source_version"]):
            raise ValueError("reading_approval")
        input_hashes[filename] = hashlib.sha256(decision_raw).hexdigest()
        for rule in document["rules"]:
            if rule["rule_id"] in decisions:
                raise ValueError("duplicate_decision")
            decisions[rule["rule_id"]] = rule
    if set(decisions) != RULES:
        raise ValueError("decision_scope")
    members = {entry["path"]: entry for entry in certificate["members"]}
    results, selected = [], []
    for obj in projection["objects"]:
        decision = decisions[obj["rule_id"]]
        schema, header = schema_from_approved(obj, decision)
        relative = decision["relative_path"]
        expected_member = dict(path=relative, kind="file", size=decision["raw_size"],
                               sha256=decision["raw_sha256"])
        if members.get(relative) != expected_member:
            raise ValueError("certificate_member")
        raw = read_regular(snapshot, relative, 16*1024*1024)
        summary = summarize_text_values(
            raw, schema=schema, expected_header=header, expected_count=obj["source_record_count"],
            expected_raw_sha256=decision["raw_sha256"], expected_raw_size=decision["raw_size"],
            bom_as_signature=decision["bom_as_signature"], backslash_escape=decision["backslash_escape"])
        reference, source_fields = independent_reference(raw, obj, decision)
        if asdict(summary) != reference:
            raise ValueError("independent_stream_difference")
        results.append(dict(rule_id=obj["rule_id"], source_object_id=schema.source_object_id,
            source=expected_member, expected=asdict(summary), source_fields_checked=source_fields,
            schema_sha256=hashlib.sha256(schema_bytes(schema)).hexdigest(),
            value_columns=[asdict(column) for column in schema.columns],
            independent_reference_equal=True, disposition_retained="BLOCKED"))
        selected.append(expected_member)
        print(json.dumps({"rule_id": obj["rule_id"], "rows": summary.row_count,
                          "fields": source_fields, "status": "source_expectation_prepared"}), flush=True)
    # Re-read the five selected members only, never claim full-snapshot validation.
    for entry in selected:
        raw = read_regular(snapshot, entry["path"], 16*1024*1024)
        if len(raw) != entry["size"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError("selected_source_changed")
    if Path(args.certificate).read_bytes() != certificate_raw:
        raise ValueError("certificate_changed")
    output = dict(version=1, status="draft", scope="five-approved-text-source-values-only",
        generated_at=datetime.now(timezone.utc).isoformat(), git_revision=args.git_revision,
        image_id=args.image_id, source_status="dirty", input_sha256=input_hashes,
        source_version=projection["source_version"], snapshot_manifest_sha256=certificate["manifest_sha256"],
        certificate_sha256=hashlib.sha256(certificate_raw).hexdigest(),
        selected_members_verified_before_and_after=True, full_snapshot_verified_this_run=False,
        canonical_format="XRGVALUE-v1", header_excluded=True, rownum_start=1,
        source_field_count=sum(obj["source_fields_checked"] for obj in results),
        derived_field_count=sum(obj["expected"]["row_count"] for obj in results),
        objects=results, ready_for_import=False, contract_frozen=False,
        formal_contract_modified=False, table_names_approved=False, target_mapping_approved=False,
        source_expected_values_prepared=True, full_release_value_contract_complete=False,
        database_connected=False)
    write_json_exclusive(Path(args.output), output)


if __name__ == "__main__":
    main()

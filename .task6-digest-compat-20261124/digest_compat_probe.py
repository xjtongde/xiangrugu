#!/usr/bin/env python3
"""Digest compatibility probe: run under baseline and extended PYTHONPATH, compare outputs.

Old-style contract documents must yield identical canonical bytes/SHA-256 across versions.
Extension values must participate in the digest (mutations change it).
"""
import hashlib
import json
import sys
from pathlib import Path

from xiangrugu_datamgmt.contracts import ReleaseContract

HERE = Path(__file__).resolve().parent
REVIEW = {"approved_by": "isolated-test", "approved_at": "2026-11-24T00:00:00Z",
          "approval_ref": "isolated-test-only-not-a-real-approval"}


def legacy_doc(status):
    doc = {"version": 1, "release_id": "2026-10-06-legacy-compat-probe",
           "source_version": "probe", "inventory_sha256": "a" * 64,
           "status": status, "review": REVIEW if status == "frozen" else None,
           "exceptions": [],
           "rules": [{"rule_id": "legacy", "selector": {"relative_path": "legacy.csv",
                                                        "archive_chain": [], "archive_ordinals": []},
                      "expected": {"kind": "file", "sha256": "c" * 64, "size": 10, "signature": "unknown"},
                      "disposition": "IMPORT", "reason": "legacy compatibility probe",
                      "format_family": "text",
                      "encodings": [{"object_name": "legacy", "column": "name", "codec": "utf-8", "errors": "strict"}],
                      "targets": [{"object_name": "legacy", "schema": "harv", "table": "legacy__data",
                                   "expected_count": 1, "expected_sha256": "b" * 64}],
                      "validator": "canonical-value-v1"}]}
    return doc


def main():
    out = {"version_label": sys.argv[1] if len(sys.argv) > 1 else "unknown"}
    for status in ("draft", "frozen"):
        contract = ReleaseContract.model_validate(legacy_doc(status))
        out[f"legacy_{status}_sha256"] = contract.sha256
        out[f"legacy_{status}_canonical_bytes_len"] = len(contract.canonical_bytes())
        out[f"legacy_{status}_canonical_sha256_of_bytes"] = hashlib.sha256(contract.canonical_bytes()).hexdigest()
    cand_path = HERE.parent / ".task6-contract-extension-20261123" / "candidate-contract.json"
    if cand_path.exists():
        try:
            cand = ReleaseContract.model_validate(json.loads(cand_path.read_text()))
            out["candidate_sha256"] = cand.sha256
            doc = json.loads(cand_path.read_text())
            rule = next(r for r in doc["rules"] if r["rule_id"] == "m008002")
            rule["targets"][0]["columns"][0]["target_column"] = "mutated_name"
            out["candidate_mutated_target_sha256"] = ReleaseContract.model_validate(doc).sha256
            doc = json.loads(cand_path.read_text())
            rule = next(r for r in doc["rules"] if r["rule_id"] == "m002709")
            lat = next(c for c in rule["targets"][0]["columns"] if c["source_column"] == "LAT")
            lat["pg_type"] = "numeric(20,5)"
            lat["source_width_bytes"] = 20
            out["candidate_mutated_width_sha256"] = ReleaseContract.model_validate(doc).sha256
        except Exception as exc:
            out["candidate_parse"] = f"REJECTED: {type(exc).__name__}"
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()
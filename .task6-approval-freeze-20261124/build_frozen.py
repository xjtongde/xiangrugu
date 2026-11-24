#!/usr/bin/env python3
"""Generate the frozen delivery candidate from the approved draft (real approval registered).

Stdlib-only construction; formal frozen-gate validation runs in the 32 isolated env.
Candidate delivery only: no controlled reception, no database write.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DRAFT = REPO / ".task6-contract-extension-20261123" / "candidate-contract.json"
APPROVAL = json.loads((HERE / "approval-record.json").read_text())


def main():
    doc = json.loads(DRAFT.read_text())
    assert doc["status"] == "draft"
    before = json.dumps(doc, sort_keys=True)
    doc["status"] = "frozen"
    doc["review"] = APPROVAL["contract_review"]
    (HERE / "frozen-candidate.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    draft = json.loads(DRAFT.read_text())
    delta = []
    for key in sorted(set(draft) | set(doc)):
        if draft.get(key) != doc.get(key):
            delta.append(key)
    report = {"changed_top_level_keys": delta,
              "only_status_and_review_changed": delta == ["review", "status"],
              "rules_identical": draft["rules"] == doc["rules"],
              "review": doc["review"],
              "real_approval": doc["review"]["approved_by"] == "茶香",
              "anchored_commit": APPROVAL["anchored_commit"]}
    (HERE / "freeze-delta-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print("FROZEN_CANDIDATE_BUILT delta", delta, "rules_identical", report["rules_identical"])


if __name__ == "__main__":
    main()
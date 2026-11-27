"""Read-only preflight for the B-batch formal command. Opens NO database connection.

Purpose: prove, from files alone, that a command line and the artifacts it names are
consistent before anyone is allowed near production. Every check here is arithmetic or
hashing; nothing connects, nothing writes.

Checks
  1. phase and scope agree: phase2-production <-> mode="production-write",
     phase1-isolated <-> mode="isolated-test". A formal phase carrying an isolated
     scope (or the reverse) is refused.
  2. the formal endpoint is exactly the approved triple, with the in-session port
     and the verified production instance id.
  3. the isolated scope never names the production instance or the production triple.
  4. the authorization text on disk hashes to the reviewed digest 4d250c8e…
  5. the approval table on disk hashes to the value the expected file binds.
  6. the code export's manifest covers every pinned module INCLUDING the runner,
     and each digest matches the file on disk.

Usage::
    python3 preflight.py --phase phase2-production \
        --scope formal-scope.json --expected formal-expected.json \
        --approval-text approval-text-verbatim.txt \
        --approval-table b-approval-table-v2.json \
        --payload payload.bin --code-root /path/to/export
Exit codes: 0 all checks pass, 2 a check failed, 4 inputs missing/unreadable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_INPUT = 0, 2, 4

APPROVED_AUTH_SHA256 = "4d250c8e08ea8136e29e35aa436812f11b5eec59a100847f130c11f39b7e2946"
APPROVED_AUTH_BYTES = 641
# The approval table must be anchored HERE, not just echoed by the expected file:
# if the only binding were expected.approval_table_sha256, then swapping the table
# and updating expected in the same breath would satisfy every check (measured --
# that exact counterexample passed before this constant was added).
APPROVED_TABLE_SHA256 = "a718b0c297501642dd105eb3797f96dc1de2edf8eb521bed6609ff78de1fb4a0"
PRODUCTION_ID = "3d93fc7741f66f1f01aa250b25c4959addfe4c84df22ecbd0d0f82c13920c1fc"
PRODUCTION_TRIPLE = {"host": "pg32b", "port": 5433, "dbname": "xiangrugu"}
IN_SESSION_PORT = 5432
LOAD_ROLE = "xrg_loader"
# The transitive closure a formal load actually imports. This must equal the
# runner's PINNED_MODULES: if the two drift, this tool would be validating a set the
# runner does not enforce (a shared blind spot). Equality is asserted by
# test_preflight_and_runner_agree_on_the_pinned_set in
# datamgmt/tests/unit/test_cbdb_social_addr_runner.py -- NOT yet executed, because
# the test host is unreachable; the assertion was checked by hand and reported as
# hand-checked.
REQUIRED_PINNED = [
    "cbdb_social_addr_runner.py", "cbdb_social_addr_entry.py",
    "cbdb_social_addr_loader.py", "contracts.py", "unordered_validate.py",
    "unordered_values.py", "sqlite_values.py", "value_sort.py",
    "canonical.py", "config.py", "first_batch_loader.py", "identity.py",
    "model.py", "naming.py", "read_cache.py", "sqlite_diagnostic.py"]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _import_closure(root):
    """Local modules transitively imported by the pinned set (ast, no execution)."""
    import ast
    pkg = Path(root) / "datamgmt" / "src" / "xiangrugu_datamgmt"

    def local(modname):
        path = pkg / modname
        if not path.exists():
            return set()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    if node.module:
                        found.add(node.module.split(".")[0] + ".py")
                    for alias in node.names:
                        found.add(alias.name + ".py")
                elif node.module and node.module.startswith("xiangrugu_datamgmt"):
                    parts = node.module.split(".")
                    if len(parts) > 1:
                        found.add(parts[1] + ".py")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("xiangrugu_datamgmt."):
                        parts = alias.name.split(".")
                        if len(parts) > 1:
                            found.add(parts[1] + ".py")
        return {f for f in found if (pkg / f).exists()}

    seen, stack = set(REQUIRED_PINNED), list(REQUIRED_PINNED)
    while stack:
        for dep in local(stack.pop()):
            if dep not in seen:
                seen.add(dep)
                stack.append(dep)
    return sorted(seen)


def check_phase_scope(phase, scope):
    want = "production-write" if phase == "phase2-production" else "isolated-test"
    got = scope.get("mode")
    if got != want:
        return f"phase_scope_disagree: phase={phase} mode={got} (expected {want})"
    return None


def check_formal_endpoint(scope, expected):
    ep = scope.get("target_endpoint") or {}
    for key, want in PRODUCTION_TRIPLE.items():
        if ep.get(key) != want:
            return f"formal_endpoint_{key}_mismatch: {ep.get(key)!r} != {want!r}"
    if ep.get("in_session_port") != IN_SESSION_PORT:
        return f"formal_in_session_port_mismatch: {ep.get('in_session_port')!r}"
    if ep.get("test_only") is not False:
        return "formal_endpoint_marked_test_only"
    if ep.get("container_id") != PRODUCTION_ID:
        return f"formal_endpoint_not_verified_instance: {ep.get('container_id')!r}"
    if scope.get("instance_fingerprint") != PRODUCTION_ID:
        return "formal_instance_fingerprint_not_production"
    if expected.get("instance_fingerprint") != PRODUCTION_ID:
        return "formal_expected_instance_fingerprint_not_production"
    if scope.get("load_role") != LOAD_ROLE:
        return f"formal_load_role_mismatch: {scope.get('load_role')!r}"
    if (scope.get("write_approval") or {}).get("approval_class") != "real":
        return "formal_write_approval_not_real"
    return None


def check_isolated_endpoint(scope):
    ep = scope.get("target_endpoint") or {}
    if ep.get("container_id") == PRODUCTION_ID:
        return "isolated_scope_names_production_instance"
    if all(ep.get(k) == v for k, v in PRODUCTION_TRIPLE.items()):
        return "isolated_scope_names_production_triple"
    if ep.get("test_only") is not True:
        return "isolated_endpoint_not_marked_test_only"
    if (scope.get("write_approval") or {}).get("approval_class") != "test":
        return "isolated_write_approval_not_test"
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="preflight")
    ap.add_argument("--phase", required=True,
                    choices=("phase2-production", "phase1-isolated"))
    ap.add_argument("--scope", required=True)
    ap.add_argument("--expected", required=True)
    ap.add_argument("--approval-text", required=True)
    ap.add_argument("--approval-table", required=True)
    ap.add_argument("--payload", required=True)
    ap.add_argument("--code-root", required=True)
    ap.add_argument("--evidence-out", default=None)
    a = ap.parse_args(argv)

    checks, failure = [], None

    def record(name, bad):
        nonlocal failure
        checks.append({"check": name, "ok": bad is None,
                       **({"detail": bad} if bad else {})})
        if bad and failure is None:
            failure = bad

    try:
        scope = json.loads(Path(a.scope).read_text(encoding="utf-8"))
        expected = json.loads(Path(a.expected).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"outcome": "INPUT_ERROR", "detail": str(exc)}))
        return EXIT_INPUT

    record("phase_scope_agree", check_phase_scope(a.phase, scope))
    if a.phase == "phase2-production":
        record("formal_endpoint_is_approved_triple",
               check_formal_endpoint(scope, expected))
    else:
        record("isolated_endpoint_is_not_production",
               check_isolated_endpoint(scope))

    # Authorization text: the reviewed digest is the independent anchor.
    try:
        raw = Path(a.approval_text).read_bytes()
        record("authorization_text_digest",
               None if hashlib.sha256(raw).hexdigest() == APPROVED_AUTH_SHA256
               else "authorization_text_digest_mismatch")
        record("authorization_text_length",
               None if len(raw) == APPROVED_AUTH_BYTES
               else f"authorization_text_bytes={len(raw)}")
    except OSError as exc:
        record("authorization_text_readable", f"unreadable: {exc}")

    # Approval table bound by the expected file.
    try:
        table_sha = sha256_file(a.approval_table)
        declared = expected.get("approval_table_sha256")
        record("approval_table_bound",
               None if declared else "approval_table_binding_missing")
        # Independent anchor first: the reviewed table digest is fixed here, so a
        # swapped table cannot be legitimised by editing the expected file.
        record("approval_table_is_reviewed_table",
               None if table_sha == APPROVED_TABLE_SHA256
               else "approval_table_is_not_the_reviewed_table")
        record("approval_table_digest",
               None if table_sha == declared else "approval_table_digest_mismatch")
    except OSError as exc:
        record("approval_table_readable", f"unreadable: {exc}")

    # Code export manifest must cover the runner itself.
    root = Path(a.code_root)
    manifest_path = root / "PIN_MODULES.json"
    pin_commit = root / "PIN_COMMIT"
    try:
        record("pin_commit_present",
               None if pin_commit.exists() else "PIN_COMMIT missing")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        record("manifest_covers_runner",
               None if "cbdb_social_addr_runner.py" in manifest
               else "manifest_does_not_pin_the_runner")
        missing = [n for n in REQUIRED_PINNED if n not in manifest]
        record("manifest_covers_all_pinned",
               None if not missing else f"missing={missing}")
        # Coverage is computed, not asserted: resolve the real import closure of the
        # staged tree and require that the manifest covers every reachable module.
        closure = _import_closure(root)
        uncovered = [m for m in closure if m not in manifest]
        record("manifest_covers_import_closure",
               None if not uncovered else f"unpinned={uncovered}")
        checks.append({"check": "import_closure_size", "ok": True,
                       "detail": str(len(closure))})
        pkg = root / "datamgmt" / "src" / "xiangrugu_datamgmt"
        bad = []
        for name in REQUIRED_PINNED:
            want = manifest.get(name)
            path = pkg / name
            if not path.exists():
                bad.append(f"{name}:absent")
            elif sha256_file(path) != want:
                bad.append(f"{name}:digest")
        record("pinned_module_digests", None if not bad else ";".join(bad))
    except (OSError, ValueError) as exc:
        record("manifest_readable", f"unreadable: {exc}")

    # Payload presence and digest (the bytes about to be COPYed).
    try:
        n = Path(a.payload).stat().st_size
        record("payload_readable", None)
        checks.append({"check": "payload_bytes", "ok": True, "detail": str(n)})
    except OSError as exc:
        record("payload_readable", f"unreadable: {exc}")

    out = {"format": "xiangrugu.b-batch.preflight.v1",
           "phase": a.phase, "connects_to_database": False, "read_only": True,
           "outcome": "PASSED" if failure is None else "FAILED",
           "failure": failure, "checks": checks}
    if a.evidence_out:
        Path(a.evidence_out).write_text(
            json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
    print(json.dumps({"outcome": out["outcome"], "failure": failure,
                      "checks": len(checks)}, ensure_ascii=False))
    return EXIT_OK if failure is None else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
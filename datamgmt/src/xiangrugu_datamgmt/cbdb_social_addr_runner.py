"""Executable runner for the B-batch single-table formal load.

This is the ACTUAL command. It is not a thin wrapper around a library call: it
pins the code it will run to an exact commit, rebuilds the execution context from
the approved artifacts, drives the entry, and emits machine-readable evidence.

Why a separate executable instead of calling the library directly
---------------------------------------------------------------
The formal requirement is that the production code and the parser come from a
REVIEWED FIXED VERSION. A caller that imports whatever happens to be on
``sys.path`` cannot prove that. So this runner:

  1. requires ``--code-commit`` and verifies that the checked-out ``HEAD`` (or an
     explicit ``--code-root``) matches it BEFORE importing anything from the
     package;
  2. records the commit, the module file digests and the contract digest in the
     evidence, so a reviewer can re-derive everything from the commit alone;
  3. refuses to start if the working tree contains uncommitted changes to the
     files it is about to run.

Usage (the exact command is emitted by ``--print-command``)::

    python3 -m xiangrugu_datamgmt.cbdb_social_addr_runner \
        --code-commit <40-hex> \
        --contract <frozen candidate json> \
        --approval-table <approval table json> \
        --approval-text <verbatim authorization txt> \
        --scope <execution scope json> \
        --expected <expected json> \
        --source-snapshot <sqlite3 member> \
        --payload <COPY payload bytes> \
        --scratch /data/var/<real-dir> \
        --evidence-out <path.json>

Exit codes (stable, documented, used by the operator):
    0  COMMITTED (single transaction completed and verified)
    2  REFUSED by a gate (nothing was written; the transaction never committed)
    3  ERROR (unexpected failure; the loader rolled back)
    4  PREFLIGHT failed (code pin, artifact digest, or prerequisite missing)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# --- External anchors for the formal run -------------------------------------
# These are the REVIEWED values. They are fixed in the executing program, not read
# from a scope or expected file, because a binding that comes from the same
# documents it is meant to police is self-certification: swap the artifact, update
# the declaration, and every check still passes. Measured counterexample: an
# approval table swapped together with expected.approval_table_sha256 satisfied all
# self-referential checks.
APPROVED_AUTH_SHA256 = "4d250c8e08ea8136e29e35aa436812f11b5eec59a100847f130c11f39b7e2946"
APPROVED_TABLE_SHA256 = "a718b0c297501642dd105eb3797f96dc1de2edf8eb521bed6609ff78de1fb4a0"

EXIT_COMMITTED = 0
EXIT_REFUSED = 2
EXIT_ERROR = 3
EXIT_PREFLIGHT = 4

# Files whose content decides the behaviour of a formal load. A local edit to any
# of them means we are no longer running the reviewed version.
# Every module that can change what a formal load does. This MUST include the runner
# itself: a manifest that pins everything except the program enforcing the manifest
# would let the enforcement layer be swapped without detection.
# This is the transitive CLOSURE of what a formal load actually imports, not a
# hand-picked list. Pinning only the obvious modules leaves reachable code
# unverified: `first_batch_loader`, for instance, defines LoaderGateError (the type
# of every gate refusal) and the CSV parser used for the instance marker and the
# database list, so editing it would silently redefine the identity check while
# every pinned digest stayed green. `code_pin_closure_gaps` enforces this property
# so a new import cannot quietly fall outside the manifest.
PINNED_MODULES = ("cbdb_social_addr_runner.py",
                  "cbdb_social_addr_entry.py", "cbdb_social_addr_loader.py",
                  "contracts.py", "unordered_validate.py", "unordered_values.py",
                  "sqlite_values.py", "value_sort.py",
                  # --- transitive dependencies reachable from the above ---
                  "canonical.py", "config.py", "first_batch_loader.py",
                  "identity.py", "model.py", "naming.py",
                  "read_cache.py", "sqlite_diagnostic.py")


def _module_import_closure(root):
    """Local modules transitively imported by the pinned set, resolved on disk.

    Uses ``ast`` so the check does not need to import anything (importing would
    execute the very code we are trying to verify, and would also require the
    third-party dependencies to be installed).
    """
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

    seen, stack = set(PINNED_MODULES), list(PINNED_MODULES)
    while stack:
        for dep in local(stack.pop()):
            if dep not in seen:
                seen.add(dep)
                stack.append(dep)
    return sorted(seen)


class PreflightError(Exception):
    """Raised before any database session is opened."""

    def __init__(self, code, detail=""):
        super().__init__(code + (": " + detail if detail else ""))
        self.code, self.detail = code, detail


def _sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(root, *args):
    """Run git, or report absence as a non-zero result rather than an exception.

    A production container legitimately has no git; the export shape must still be
    verifiable, so "git is missing" degrades to "not a git work tree" instead of
    aborting the preflight with an opaque I/O error.
    """
    try:
        return subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, text=True, check=False)
    except (FileNotFoundError, NotImplementedError):
        return subprocess.CompletedProcess(args=["git", *args], returncode=127,
                                           stdout="", stderr="git-not-available")


def verify_code_pin(code_root, expected_commit):
    """Refuse to run unless the code on disk IS the reviewed commit.

    Two supported shapes, because production code is often staged as a read-only
    artifact rather than a live checkout:

      git     ``code_root`` is a git work tree; HEAD must equal the commit and the
              pinned package must have no uncommitted edits.
      export  ``code_root`` holds a ``git archive`` export of the commit plus a
              ``PIN_COMMIT`` file containing that commit; the pinned modules are
              then checked against the digests recorded in ``PIN_MODULES.json``.
    """
    root = Path(code_root)
    pkg = root / "datamgmt" / "src" / "xiangrugu_datamgmt"

    head = _git(root, "rev-parse", "HEAD")
    if head.returncode == 0:
        actual = head.stdout.strip()
        if actual != expected_commit:
            raise PreflightError("code_commit_mismatch", actual)
        # Uncommitted edits to the pinned modules would silently change behaviour.
        dirty = _git(root, "status", "--porcelain", "--",
                     str(pkg.relative_to(root)))
        if dirty.returncode == 0 and dirty.stdout.strip():
            raise PreflightError("pinned_code_dirty", dirty.stdout.strip()[:400])
        shape = "git"
    else:
        pin = root / "PIN_COMMIT"
        if not pin.exists():
            raise PreflightError("code_root_not_a_git_repo",
                                 "no .git and no PIN_COMMIT: cannot prove the version")
        actual = pin.read_text(encoding="utf-8").strip()
        if actual != expected_commit:
            raise PreflightError("code_commit_mismatch", actual)
        manifest = root / "PIN_MODULES.json"
        if not manifest.exists():
            raise PreflightError("pin_manifest_missing", str(manifest))
        recorded = read_json(manifest)
        for name, want in recorded.items():
            have = _sha_file(pkg / name) if (pkg / name).exists() else None
            if have != want:
                raise PreflightError("pinned_module_digest_mismatch", name)
        shape = "export"

    return {
        "commit": actual,
        "shape": shape,
        "modules": {name: _sha_file(pkg / name) for name in PINNED_MODULES
                    if (pkg / name).exists()},
    }


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build_scope(args, expected, contract_sha256, approval_text_sha256):
    """The caller supplies the scope, but the authorization text is supplied HERE.

    The text is read from the operator's file and bound to the scope in code, so a
    scope containing a *self-declared* authorization digest cannot pass: the digest
    the loader checks is recomputed from the bytes on disk.
    """
    scope = read_json(args.scope)
    auth = scope.setdefault("real_write_authorization", {})
    raw = Path(args.approval_text).read_bytes()
    auth["approval_text_verbatim"] = raw.decode("utf-8")
    auth["approval_text_sha256"] = approval_text_sha256
    wa = scope.setdefault("write_approval", {})
    wa.setdefault("approval_text_sha256", approval_text_sha256)
    scope.setdefault("contract_sha256", contract_sha256)
    return scope, raw


def _probe_target(session):
    """Observe what is actually left behind after a refusal or an error.

    "The failed load rolled back and left no half-built table" is a claim about
    database state, so it must be measured, not inferred from the transaction
    structure. This runs on the SAME session after the failure.
    """
    probe = {"measured": False}
    try:
        rel = session.query_csv(
            "SELECT COALESCE(to_regclass('cbdb.cbdb__social_u5f_institution_u5f_addr')::text, '')"
        ).strip()
        probe["target_table_present"] = bool(rel)
        if rel:
            probe["residue_rows"] = int(
                session.query_csv(
                    "SELECT count(*) FROM cbdb.cbdb__social_u5f_institution_u5f_addr"
                ).strip())
        else:
            probe["residue_rows"] = 0
        probe["measured"] = True
    except Exception as exc:  # noqa: BLE001 - a probe failure must be visible
        probe["probe_error"] = type(exc).__name__ + ": " + str(exc)[:200]
    return probe


def run(args):
    evidence = {"format": "xiangrugu.b-batch.single-table-load-evidence.v1",
                "phase": args.phase, "command": sys.argv[1:], "outcome": None}

    # ---- Preflight: everything here happens before a session exists ----------
    try:
        evidence["code_pin"] = verify_code_pin(Path(args.code_root), args.code_commit)
        # A manifest is only as good as its coverage: make the "every reachable
        # module is pinned" property machine-checked instead of relying on whoever
        # edits the list next.
        closure = _module_import_closure(args.code_root)
        gaps = [m for m in closure if m not in PINNED_MODULES]
        evidence["code_pin"]["closure_size"] = len(closure)
        if gaps:
            raise PreflightError("code_pin_closure_gaps", ",".join(gaps))

        if not Path(args.scratch).is_dir() or os.path.islink(args.scratch):
            raise PreflightError("scratch_not_a_real_directory", args.scratch)

        approval_text_sha256 = _sha_file(args.approval_text)
        if approval_text_sha256 != args.approval_text_sha256:
            raise PreflightError("approval_text_digest_mismatch", approval_text_sha256)
        # Same reasoning as the approval table: the reviewed text is anchored in the
        # program, so re-hashing a DIFFERENT text and passing its hash as the expected
        # value cannot succeed.
        if args.phase == "phase2-production" and approval_text_sha256 != APPROVED_AUTH_SHA256:
            raise PreflightError("authorization_text_is_not_the_reviewed_text",
                                 approval_text_sha256)
        evidence["approval_text"] = {"path": args.approval_text,
                                     "sha256": approval_text_sha256,
                                     "bytes": Path(args.approval_text).stat().st_size}

        expected = read_json(args.expected)

        # The approval TABLE is an argument of the formal command, so it must be
        # verified here -- not merely passed through. Reading a file and never
        # checking it would advertise a check that does not exist.
        approval_table_sha256 = _sha_file(args.approval_table)
        declared_approval_table = expected.get("approval_table_sha256")
        if not declared_approval_table:
            # An expected file that does not bind the approval table would silently
            # disable this check, so absence is itself a refusal.
            raise PreflightError("approval_table_binding_missing")
        # Anchor FIRST. Comparing only against `declared` would let a caller swap the
        # table and edit the expected file in the same breath -- the check would then
        # confirm that the forgery matches the forgery.
        if approval_table_sha256 != APPROVED_TABLE_SHA256:
            raise PreflightError("approval_table_is_not_the_reviewed_table",
                                 approval_table_sha256)
        if approval_table_sha256 != declared_approval_table:
            raise PreflightError("approval_table_digest_mismatch", approval_table_sha256)
        evidence["approval_table"] = {"path": args.approval_table,
                                      "sha256": approval_table_sha256}

        # Record the contract FILE bytes for traceability. It is deliberately NOT
        # compared to contract_sha256 here: that value is the CANONICAL digest
        # (pydantic model_dump, sorted, optional extensions dropped), not a file
        # hash -- verified: file a718... vs canonical 56b0076d... The canonical
        # digest is recomputed from the parsed document by the entry's Gate D.
        evidence["contract_file"] = {"path": args.contract,
                                     "file_sha256": _sha_file(args.contract)}

        scope, _raw = build_scope(args, expected, expected.get("contract_sha256"),
                                  approval_text_sha256)
        artifacts = {"contract": read_json(args.contract)}
    except (PreflightError, OSError, ValueError) as exc:
        code = getattr(exc, "code", "preflight_io_error")
        evidence["outcome"] = "PREFLIGHT_FAILED"
        evidence["refusal"] = {"error_code": code, "detail": str(exc)[:600]}
        return EXIT_PREFLIGHT, evidence

    # ---- Import AFTER the pin is verified -----------------------------------
    # Verifying one tree while importing from another would let us pin code A and
    # run code B. Bind the import to the tree we just verified, and prove it by
    # recording where each module was actually loaded from.
    import importlib
    import sys as _sys

    code_src = str(Path(args.code_root) / "datamgmt" / "src")
    for stale in [p for p in _sys.path if p.replace("\\", "/").endswith("/datamgmt/src")]:
        _sys.path.remove(stale)
    _sys.path.insert(0, code_src)
    for mod in [m for m in list(_sys.modules) if m.split(".")[0] == "xiangrugu_datamgmt"]:
        del _sys.modules[mod]

    E = importlib.import_module("xiangrugu_datamgmt.cbdb_social_addr_entry")
    L = importlib.import_module("xiangrugu_datamgmt.cbdb_social_addr_loader")
    ReleaseContract = importlib.import_module(
        "xiangrugu_datamgmt.contracts").ReleaseContract

    loaded_from = {name: getattr(mod, "__file__", None) for name, mod in
                   (("entry", E), ("loader", L))}
    for name, path in loaded_from.items():
        if not path or not str(Path(path).resolve()).startswith(
                str((Path(args.code_root) / "datamgmt" / "src").resolve())):
            evidence["outcome"] = "PREFLIGHT_FAILED"
            evidence["refusal"] = {"error_code": "imported_module_outside_code_root",
                                   "detail": f"{name}: {path}"}
            return EXIT_PREFLIGHT, evidence
    evidence["imported_modules"] = loaded_from

    def parse(doc):
        return ReleaseContract.model_validate(doc)

    def make_loader(session, sc, parsed_doc, target, payload, exp, instance):
        return L.run_single_table(session, sc, parsed_doc, target, payload, instance, exp)

    with open(args.payload, "rb") as fh:
        payload_bytes = fh.read()
    evidence["payload"] = {"path": args.payload, "bytes": len(payload_bytes),
                           "sha256": hashlib.sha256(payload_bytes).hexdigest()}

    # --- Endpoint binding, decided BEFORE a connection exists ------------------
    # The formal run must reach exactly the approved triple. An operator-supplied
    # host/port/role that differs from what the scope declares would mean we are
    # about to write somewhere the authorization never named, so it is refused here
    # rather than discovered after connecting.
    ep = scope["target_endpoint"]
    formal = args.phase == "phase2-production"

    if formal:
        if ep.get("host") != E.PRODUCTION_TARGET["host"]:
            evidence["outcome"] = "PREFLIGHT_FAILED"
            evidence["refusal"] = {"error_code": "formal_endpoint_host_mismatch",
                                   "detail": str(ep.get("host"))}
            return EXIT_PREFLIGHT, evidence
        if ep.get("port") != E.PRODUCTION_TARGET["port"]:
            evidence["outcome"] = "PREFLIGHT_FAILED"
            evidence["refusal"] = {"error_code": "formal_endpoint_port_mismatch",
                                   "detail": str(ep.get("port"))}
            return EXIT_PREFLIGHT, evidence
        if ep.get("dbname") != E.PRODUCTION_TARGET["dbname"]:
            evidence["outcome"] = "PREFLIGHT_FAILED"
            evidence["refusal"] = {"error_code": "formal_endpoint_dbname_mismatch",
                                   "detail": str(ep.get("dbname"))}
            return EXIT_PREFLIGHT, evidence
        if ep.get("in_session_port") != E.IN_SESSION_PORT:
            evidence["outcome"] = "PREFLIGHT_FAILED"
            evidence["refusal"] = {"error_code": "formal_in_session_port_mismatch",
                                   "detail": str(ep.get("in_session_port"))}
            return EXIT_PREFLIGHT, evidence
        if ep.get("test_only") is not False:
            evidence["outcome"] = "PREFLIGHT_FAILED"
            evidence["refusal"] = {"error_code": "formal_endpoint_marked_test_only"}
            return EXIT_PREFLIGHT, evidence
        marker = (ep.get("container_id") or "")
        if not marker:
            evidence["outcome"] = "PREFLIGHT_FAILED"
            evidence["refusal"] = {"error_code": "formal_endpoint_missing_container_id"}
            return EXIT_PREFLIGHT, evidence
        if marker == E._PRODUCTION_CONTAINER_ID:
            pass  # the verified production instance: expected for a formal run
        else:
            evidence["outcome"] = "PREFLIGHT_FAILED"
            evidence["refusal"] = {"error_code": "formal_endpoint_not_verified_instance",
                                   "detail": marker}
            return EXIT_PREFLIGHT, evidence

        # Overrides are REFUSED, not merely ignored: silently substituting an
        # endpoint would make the evidence describe a target the caller never
        # approved, which is exactly the failure this whole runner exists to stop.
        if args.connect_host or args.connect_port or args.load_role:
            evidence["outcome"] = "PREFLIGHT_FAILED"
            evidence["refusal"] = {
                "error_code": "formal_endpoint_override_refused",
                "detail": "phase2-production connects to the approved endpoint only; "
                          "--connect-host/--connect-port/--load-role are not accepted"}
            return EXIT_PREFLIGHT, evidence
        connect_host, connect_port = ep["host"], int(ep["port"])
        load_role = E.LOAD_ROLE
    else:
        # Isolated mode: never the production instance, never the production triple.
        marker = (ep.get("container_id") or "")
        if marker == E._PRODUCTION_CONTAINER_ID:
            evidence["outcome"] = "PREFLIGHT_FAILED"
            evidence["refusal"] = {"error_code": "isolated_mode_targets_production_instance"}
            return EXIT_PREFLIGHT, evidence
        if (ep.get("host") == E.PRODUCTION_TARGET["host"]
                and ep.get("port") == E.PRODUCTION_TARGET["port"]
                and ep.get("dbname") == E.PRODUCTION_TARGET["dbname"]):
            evidence["outcome"] = "PREFLIGHT_FAILED"
            evidence["refusal"] = {"error_code": "isolated_mode_targets_production_endpoint"}
            return EXIT_PREFLIGHT, evidence
        load_role = args.load_role or E.LOAD_ROLE
        connect_host = args.connect_host or ep["host"]
        connect_port = int(args.connect_port or ep["port"])

    password = os.environ.get("XNG_LOAD_PASSWORD")
    if not password:
        evidence["outcome"] = "PREFLIGHT_FAILED"
        evidence["refusal"] = {"error_code": "load_password_not_supplied",
                              "detail": "set XNG_LOAD_PASSWORD (never on the command line)"}
        return EXIT_PREFLIGHT, evidence

    # One connection, one session, for the identity check AND the DDL. No reconnect,
    # no database switch: the entry gates verify what this exact session is.
    session = L.PsqlSession(
        ["psql", "-X", "-q", "-tA", "--csv", "-v", "ON_ERROR_STOP=1",
         "-h", connect_host, "-p", str(connect_port),
         "-U", load_role, "-d", ep["dbname"]],
        env=dict(os.environ, PGPASSWORD=password),
    )
    evidence["session"] = {"connect_host": connect_host,
                           "connect_port": connect_port,
                           "declared_target_port": ep["port"],
                           "declared_in_session_port": E.IN_SESSION_PORT,
                           "dbname": ep["dbname"],
                           "load_role": load_role,
                           "formal": formal,
                           "override_refused": formal,
                           "no_db_switch": True, "no_reconnect": True}
    try:
        ev = E.run_execution_candidate(session, scope, expected, artifacts, parse,
                                       make_loader, payload_bytes)
    except (L.LoaderGateError, E.LoaderGateError) as exc:
        evidence["outcome"] = "REFUSED"
        evidence["refusal"] = {"error_code": getattr(exc, "code", "gate_error"),
                              "detail": str(exc)[:600]}
        evidence["target_probe_after"] = _probe_target(session)
        return EXIT_REFUSED, evidence
    except Exception as exc:  # noqa: BLE001 - evidence must record anything
        evidence["outcome"] = "ERROR"
        evidence["refusal"] = {"error_code": "unexpected_error",
                              "detail": type(exc).__name__ + ": " + str(exc)[:600]}
        evidence["target_probe_after"] = _probe_target(session)
        return EXIT_ERROR, evidence
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass

    evidence["outcome"] = "COMMITTED" if ev.get("committed") else "ROLLED_BACK"
    evidence["result"] = ev
    return (EXIT_COMMITTED if ev.get("committed") else EXIT_ERROR), evidence


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cbdb_social_addr_runner")
    ap.add_argument("--phase", required=True, choices=("phase1-isolated", "phase2-production"))
    ap.add_argument("--code-root", required=True, help="checkout to run; must match --code-commit")
    ap.add_argument("--code-commit", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--approval-table", required=True)
    ap.add_argument("--approval-text", required=True)
    ap.add_argument("--approval-text-sha256", required=True)
    ap.add_argument("--scope", required=True)
    ap.add_argument("--expected", required=True)
    ap.add_argument("--payload", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--load-role", default=None,
                    help="load role (defaults to the approved xrg_loader)")
    ap.add_argument("--connect-host", default=None)
    ap.add_argument("--connect-port", default=None,
                    help="outer port to connect to (defaults to the approved 5433)")
    ap.add_argument("--evidence-out", required=True)
    args = ap.parse_args(argv)

    code, evidence = run(args)
    out = Path(args.evidence_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(json.dumps({"outcome": evidence["outcome"], "exit_code": code,
                      "evidence": str(out)}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
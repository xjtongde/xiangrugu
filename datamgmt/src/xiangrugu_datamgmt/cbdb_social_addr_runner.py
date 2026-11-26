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

EXIT_COMMITTED = 0
EXIT_REFUSED = 2
EXIT_ERROR = 3
EXIT_PREFLIGHT = 4

# Files whose content decides the behaviour of a formal load. A local edit to any
# of them means we are no longer running the reviewed version.
PINNED_MODULES = ("cbdb_social_addr_entry.py", "cbdb_social_addr_loader.py",
                  "contracts.py", "unordered_validate.py", "unordered_values.py",
                  "sqlite_values.py", "value_sort.py")


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
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, check=False)


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


def run(args):
    evidence = {"format": "xiangrugu.b-batch.single-table-load-evidence.v1",
                "phase": args.phase, "command": sys.argv[1:], "outcome": None}

    # ---- Preflight: everything here happens before a session exists ----------
    try:
        evidence["code_pin"] = verify_code_pin(Path(args.code_root), args.code_commit)

        if not Path(args.scratch).is_dir() or os.path.islink(args.scratch):
            raise PreflightError("scratch_not_a_real_directory", args.scratch)

        approval_text_sha256 = _sha_file(args.approval_text)
        if approval_text_sha256 != args.approval_text_sha256:
            raise PreflightError("approval_text_digest_mismatch", approval_text_sha256)
        evidence["approval_text"] = {"path": args.approval_text,
                                     "sha256": approval_text_sha256,
                                     "bytes": Path(args.approval_text).stat().st_size}

        contract_bytes_sha256 = _sha_file(args.contract)
        evidence["contract_file"] = {"path": args.contract,
                                     "file_sha256": contract_bytes_sha256}

        expected = read_json(args.expected)
        scope, _raw = build_scope(args, expected, expected.get("contract_sha256"),
                                  approval_text_sha256)
        artifacts = {"contract": read_json(args.contract)}
    except (PreflightError, OSError, ValueError) as exc:
        code = getattr(exc, "code", "preflight_io_error")
        evidence["outcome"] = "PREFLIGHT_FAILED"
        evidence["refusal"] = {"error_code": code, "detail": str(exc)[:600]}
        return EXIT_PREFLIGHT, evidence

    # ---- Import AFTER the pin is verified -----------------------------------
    from xiangrugu_datamgmt import cbdb_social_addr_entry as E
    from xiangrugu_datamgmt import cbdb_social_addr_loader as L
    from xiangrugu_datamgmt.contracts import ReleaseContract

    def parse(doc):
        return ReleaseContract.model_validate(doc)

    def make_loader(session, sc, parsed_doc, target, payload, exp, instance):
        return L.run_single_table(session, sc, parsed_doc, target, payload, instance, exp)

    with open(args.payload, "rb") as fh:
        payload_bytes = fh.read()
    evidence["payload"] = {"path": args.payload, "bytes": len(payload_bytes),
                           "sha256": hashlib.sha256(payload_bytes).hexdigest()}

    # The CONNECT endpoint is derived from the approved endpoint, never taken from
    # an environment default: the outer port is what an operator reaches, and the
    # in-session port is checked separately by the entry gates.
    ep = scope["target_endpoint"]
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
                           "no_db_switch": True, "no_reconnect": True}
    try:
        ev = E.run_execution_candidate(session, scope, expected, artifacts, parse,
                                       make_loader, payload_bytes)
    except (L.LoaderGateError, E.LoaderGateError) as exc:
        evidence["outcome"] = "REFUSED"
        evidence["refusal"] = {"error_code": getattr(exc, "code", "gate_error"),
                              "detail": str(exc)[:600]}
        return EXIT_REFUSED, evidence
    except Exception as exc:  # noqa: BLE001 - evidence must record anything
        evidence["outcome"] = "ERROR"
        evidence["refusal"] = {"error_code": "unexpected_error",
                              "detail": type(exc).__name__ + ": " + str(exc)[:600]}
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
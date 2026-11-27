"""Unit tests for the formal-load runner's preflight contract.

The runner is the only entry point allowed to write the formal database, so the
properties that make it trustworthy are tested directly rather than assumed:

* it refuses to run code that is not the pinned commit;
* it verifies the approval table it was handed instead of merely receiving it;
* it imports from the tree it verified, not from whatever ``sys.path`` offers.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

# Load the runner by path: the dev container's site-packages carries an older
# copy of this package that shadows the source tree, and the runner must be tested
# as the module that will actually run.
import importlib.util

_RUNNER_PATH = (Path(__file__).resolve().parents[2]
                / "src" / "xiangrugu_datamgmt" / "cbdb_social_addr_runner.py")
_spec = importlib.util.spec_from_file_location("_xrg_runner_under_test", _RUNNER_PATH)
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture()
def pinned_export(tmp_path):
    """A minimal export-shaped code root with a PIN_COMMIT and module manifests."""
    root = tmp_path / "code"
    pkg = root / "datamgmt" / "src" / "xiangrugu_datamgmt"
    pkg.mkdir(parents=True)
    (pkg / "cbdb_social_addr_entry.py").write_text("# entry\n", encoding="utf-8")
    (pkg / "cbdb_social_addr_loader.py").write_text("# loader\n", encoding="utf-8")
    commit = "a" * 40
    (root / "PIN_COMMIT").write_text(commit + "\n", encoding="utf-8")
    (root / "PIN_MODULES.json").write_text(json.dumps({
        "cbdb_social_addr_entry.py": _sha(pkg / "cbdb_social_addr_entry.py"),
        "cbdb_social_addr_loader.py": _sha(pkg / "cbdb_social_addr_loader.py"),
    }), encoding="utf-8")
    return root, commit, pkg


def test_export_pin_accepts_a_matching_export(pinned_export):
    root, commit, _pkg = pinned_export
    pin = R.verify_code_pin(root, commit)
    assert pin["commit"] == commit
    assert pin["shape"] == "export"


def test_export_pin_rejects_a_different_commit(pinned_export):
    root, _commit, _pkg = pinned_export
    with pytest.raises(R.PreflightError) as exc:
        R.verify_code_pin(root, "b" * 40)
    assert exc.value.code == "code_commit_mismatch"


def test_export_pin_rejects_an_edited_module(pinned_export):
    """A local edit to a pinned module means we are no longer running the review."""
    root, commit, pkg = pinned_export
    (pkg / "cbdb_social_addr_entry.py").write_text("# tampered\n", encoding="utf-8")
    with pytest.raises(R.PreflightError) as exc:
        R.verify_code_pin(root, commit)
    assert exc.value.code == "pinned_module_digest_mismatch"


def test_export_pin_requires_a_manifest(pinned_export):
    root, commit, _pkg = pinned_export
    (root / "PIN_MODULES.json").unlink()
    with pytest.raises(R.PreflightError) as exc:
        R.verify_code_pin(root, commit)
    assert exc.value.code == "pin_manifest_missing"


def test_unpinned_directory_is_refused(tmp_path):
    """Neither .git nor PIN_COMMIT: the version cannot be proven, so refuse."""
    with pytest.raises(R.PreflightError) as exc:
        R.verify_code_pin(tmp_path, "c" * 40)
    assert exc.value.code == "code_root_not_a_git_repo"


def test_git_absence_is_reported_not_raised(tmp_path, monkeypatch):
    """Production containers have no git; absence must degrade, not explode."""
    def boom(*_a, **_k):
        raise FileNotFoundError("git")

    monkeypatch.setattr(R.subprocess, "run", boom)
    result = R._git(tmp_path, "rev-parse", "HEAD")
    assert result.returncode == 127


def test_preflight_verifies_the_approval_table_it_was_given(tmp_path, pinned_export):
    """--approval-table must be CHECKED, not merely accepted as an argument."""
    root, commit, _pkg = pinned_export
    table = tmp_path / "approval-table.json"
    table.write_text('{"tables": []}\n', encoding="utf-8")
    text = tmp_path / "approval.txt"
    text.write_bytes(b"approval body\n")
    expected = tmp_path / "expected.json"
    expected.write_text(json.dumps({"approval_table_sha256": "0" * 64}), encoding="utf-8")
    scope = tmp_path / "scope.json"
    scope.write_text("{}", encoding="utf-8")

    args = R.argparse.Namespace(
        phase="phase1-isolated", code_root=str(root), code_commit=commit,
        contract=str(tmp_path / "contract.json"),
        approval_table=str(table), approval_text=str(text),
        approval_text_sha256=_sha(text), scope=str(scope),
        expected=str(expected), payload=str(tmp_path / "p.bin"),
        scratch=str(tmp_path), evidence_out=str(tmp_path / "ev.json"))
    (tmp_path / "contract.json").write_text("{}", encoding="utf-8")

    code, evidence = R.run(args)
    assert code == R.EXIT_PREFLIGHT
    assert evidence["refusal"]["error_code"] == "approval_table_digest_mismatch"


def test_preflight_rejects_a_relabelled_authorization_text(tmp_path, pinned_export):
    """A caller-supplied digest that does not match the bytes is refused."""
    root, commit, _pkg = pinned_export
    table = tmp_path / "approval-table.json"
    table.write_text('{"tables": []}\n', encoding="utf-8")
    text = tmp_path / "approval.txt"
    text.write_bytes(b"real body\n")
    expected = tmp_path / "expected.json"
    expected.write_text(json.dumps({"approval_table_sha256": _sha(table)}), encoding="utf-8")
    contract = tmp_path / "contract.json"
    contract.write_text("{}", encoding="utf-8")

    args = R.argparse.Namespace(
        phase="phase1-isolated", code_root=str(root), code_commit=commit,
        contract=str(contract), approval_table=str(table), approval_text=str(text),
        approval_text_sha256="f" * 64, scope=str(contract), expected=str(expected),
        payload=str(tmp_path / "p.bin"), scratch=str(tmp_path),
        evidence_out=str(tmp_path / "ev.json"))
    code, evidence = R.run(args)
    assert code == R.EXIT_PREFLIGHT
    assert evidence["refusal"]["error_code"] == "approval_text_digest_mismatch"


def test_exit_code_constants_match_the_documented_contract():
    """The operator-facing contract must not drift silently."""
    assert (R.EXIT_COMMITTED, R.EXIT_REFUSED, R.EXIT_ERROR, R.EXIT_PREFLIGHT) == (0, 2, 3, 4)

def test_expected_must_bind_the_approval_table(tmp_path, pinned_export):
    """Omitting the key must refuse, not silently skip the approval-table check."""
    root, commit, _pkg = pinned_export
    table = tmp_path / "approval-table.json"
    table.write_text('{"tables": []}\n', encoding="utf-8")
    text = tmp_path / "approval.txt"
    text.write_bytes(b"body\n")
    expected = tmp_path / "expected.json"
    expected.write_text(json.dumps({}), encoding="utf-8")  # no approval_table_sha256
    contract = tmp_path / "contract.json"
    contract.write_text("{}", encoding="utf-8")

    args = R.argparse.Namespace(
        phase="phase1-isolated", code_root=str(root), code_commit=commit,
        contract=str(contract), approval_table=str(table), approval_text=str(text),
        approval_text_sha256=_sha(text), scope=str(contract), expected=str(expected),
        payload=str(tmp_path / "p.bin"), scratch=str(tmp_path),
        evidence_out=str(tmp_path / "ev.json"))
    code, evidence = R.run(args)
    assert code == R.EXIT_PREFLIGHT
    assert evidence["refusal"]["error_code"] == "approval_table_binding_missing"


class _FakeSession:
    def __init__(self, present):
        self.present, self.queries = present, []

    def query_csv(self, sql):
        self.queries.append(sql)
        if "to_regclass" in sql:
            return "cbdb.cbdb__social_u5f_institution_u5f_addr" if self.present else ""
        return "7"


def test_probe_measures_absence_after_a_refusal():
    """"Rolled back, nothing left behind" must be OBSERVED, not inferred."""
    session = _FakeSession(present=False)
    probe = R._probe_target(session)
    assert probe["measured"] is True
    assert probe["target_table_present"] is False
    assert probe["residue_rows"] == 0


def test_probe_reports_residue_when_a_table_survives():
    session = _FakeSession(present=True)
    probe = R._probe_target(session)
    assert probe["target_table_present"] is True
    assert probe["residue_rows"] == 7


def test_probe_failure_is_visible_not_silent():
    class Boom:
        def query_csv(self, _sql):
            raise RuntimeError("connection gone")

    probe = R._probe_target(Boom())
    assert probe["measured"] is False
    assert "connection gone" in probe["probe_error"]


# ---------------------------------------------------------------------------
# Endpoint binding: the formal run must reach exactly the approved triple, and
# must refuse overrides BEFORE a connection exists.
# ---------------------------------------------------------------------------
def _formal_args(tmp_path, pinned_export, **over):
    root, commit, _pkg = pinned_export
    table = tmp_path / "approval-table.json"
    table.write_text('{"tables": []}\n', encoding="utf-8")
    text = tmp_path / "approval.txt"
    text.write_bytes(b"body\n")
    contract = tmp_path / "contract.json"
    contract.write_text("{}", encoding="utf-8")
    expected = tmp_path / "expected.json"
    expected.write_text(json.dumps({"approval_table_sha256": _sha(table)}), encoding="utf-8")
    scope = tmp_path / "scope.json"
    scope.write_text(json.dumps({
        "mode": "production-write",
        "target_endpoint": {"host": "pg32b", "port": 5433, "dbname": "xiangrugu",
                            "in_session_port": 5432, "test_only": False,
                            "container_id": "3" * 64},
    }), encoding="utf-8")
    ns = dict(phase="phase2-production", code_root=str(root), code_commit=commit,
              contract=str(contract), approval_table=str(table), approval_text=str(text),
              approval_text_sha256=_sha(text), scope=str(scope), expected=str(expected),
              payload=str(tmp_path / "p.bin"), scratch=str(tmp_path),
              connect_host=None, connect_port=None, load_role=None,
              evidence_out=str(tmp_path / "ev.json"))
    ns.update(over)
    return R.argparse.Namespace(**ns)


def test_formal_mode_refuses_a_connect_host_override(tmp_path, pinned_export):
    """An override would write somewhere the authorization never named: refuse."""
    code, evidence = R.run(_formal_args(tmp_path, pinned_export, connect_host="127.0.0.1"))
    assert code == R.EXIT_PREFLIGHT
    assert evidence["refusal"]["error_code"] == "formal_endpoint_override_refused"


def test_formal_mode_refuses_a_connect_port_override(tmp_path, pinned_export):
    code, evidence = R.run(_formal_args(tmp_path, pinned_export, connect_port="5432"))
    assert code == R.EXIT_PREFLIGHT
    assert evidence["refusal"]["error_code"] == "formal_endpoint_override_refused"


def test_formal_mode_refuses_a_load_role_override(tmp_path, pinned_export):
    code, evidence = R.run(_formal_args(tmp_path, pinned_export, load_role="postgres"))
    assert code == R.EXIT_PREFLIGHT
    assert evidence["refusal"]["error_code"] == "formal_endpoint_override_refused"


def test_formal_mode_refuses_a_non_production_instance(tmp_path, pinned_export):
    args = _formal_args(tmp_path, pinned_export)
    scope = json.loads(Path(args.scope).read_text(encoding="utf-8"))
    scope["target_endpoint"]["container_id"] = "a" * 64
    Path(args.scope).write_text(json.dumps(scope), encoding="utf-8")
    code, evidence = R.run(args)
    assert code == R.EXIT_PREFLIGHT
    assert evidence["refusal"]["error_code"] == "formal_endpoint_not_verified_instance"


def test_isolated_mode_never_targets_the_production_instance(tmp_path, pinned_export):
    args = _formal_args(tmp_path, pinned_export, phase="phase1-isolated")
    scope = json.loads(Path(args.scope).read_text(encoding="utf-8"))
    scope["mode"] = "isolated-test"
    scope["target_endpoint"]["test_only"] = True
    scope["target_endpoint"]["container_id"] = R_PROD_ID()
    Path(args.scope).write_text(json.dumps(scope), encoding="utf-8")
    code, evidence = R.run(args)
    assert code == R.EXIT_PREFLIGHT
    assert evidence["refusal"]["error_code"] == "isolated_mode_targets_production_instance"


def test_runner_pins_itself():
    """A manifest that omits the enforcer can be satisfied while the enforcer is swapped."""
    assert "cbdb_social_addr_runner.py" in R.PINNED_MODULES


def R_PROD_ID():
    """The verified production container id, as defined in the entry module.

    _PRODUCTION_CONTAINER_ID lives in cbdb_social_addr_entry.py; the runner only
    references it as E._PRODUCTION_CONTAINER_ID. Read it from the module that
    actually defines it rather than scanning the wrong file.
    """
    SRC = Path(R.__file__).resolve().parent
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    src = (SRC / "cbdb_social_addr_entry.py").read_text(encoding="utf-8")
    marker = '_PRODUCTION_CONTAINER_ID = "'
    start = src.index(marker) + len(marker)
    return src[start:src.index('"', start)]


# ---------------------------------------------------------------------------
# Pinning closure and anchor coverage. These lock the properties that keep the
# manifest honest; without them the lists drift silently.
# ---------------------------------------------------------------------------
def test_pinned_closure_has_no_reachable_gaps():
    """Every module reachable from the pinned set must itself be pinned."""
    closure = R._module_import_closure(REPO_ROOT())
    gaps = [m for m in closure if m not in R.PINNED_MODULES]
    assert gaps == [], f"reachable but unpinned: {gaps}"


def test_pinned_closure_covers_behaviour_dependencies():
    """first_batch_loader defines LoaderGateError and parses the instance marker."""
    assert "first_batch_loader.py" in R.PINNED_MODULES


def test_preflight_and_runner_agree_on_the_pinned_set():
    """preflight.py validates a set; if it differs from the runner's, the two
    checks would be confirming the same blind spot. Compare them for real."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "xrg_preflight", REPO_ROOT() / ".b-batch-real-runner-binding-20261127"
        / "preflight.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert tuple(mod.REQUIRED_PINNED) == tuple(R.PINNED_MODULES)


def test_runner_anchors_are_the_reviewed_values():
    assert R.APPROVED_AUTH_SHA256.startswith("4d250c8e")
    assert R.APPROVED_TABLE_SHA256.startswith("a718b0c2")


def REPO_ROOT():
    p = Path(R.__file__).resolve()
    while p.name != "xiangrugu" and p.parent != p:
        p = p.parent
        if (p / ".b-batch-real-runner-binding-20261127").is_dir():
            return p
    return p

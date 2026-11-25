"""Production entry R52: positive identity with legacy DBs present, in-entry digest
recompute (artifact-changed-but-caller-consistent negative), approval binding."""
import copy

import pytest

from xiangrugu_datamgmt import production_entry as pe
from xiangrugu_datamgmt import first_batch_loader as fbl
from test_first_batch_loader import FakeSession, _contract, _payload, _expected, _csv

INV_DOC = {"entries": [], "issues": [], "checksums": [], "limits": []}
EV_DOCS = {"nul": {"x": 1}, "chgis": {"x": 2}}
INV_SHA = pe._inventory_sha(INV_DOC)
EV_SHAS = {k: pe._evidence_sha(v) for k, v in EV_DOCS.items()}
FP = "d" * 64


class ProdFake(FakeSession):
    def __init__(self, contract, existing=(), corrupt=None, dbname="xiangrugu", port="5432",
                 ext="1", ns="chgis,harv", dbs="postgres,template0,template1,xiangrugu,cbdb,cbdb_reh",
                 marker=FP):
        super().__init__(contract, existing=existing, corrupt=corrupt)
        self.identity = [dbname, port, "172.17.0.9", "18.6", "2026-11-25 14:00:00+00"]
        self.ext, self.ns, self.dbs, self.marker = ext, ns, dbs, marker
        self.sqls = []

    def execute(self, sql):
        self.sqls.append(sql)
        super().execute(sql)

    def query_csv(self, sql):
        if "current_database()" in sql:
            return _csv([self.identity])
        if "xrg_instance_marker" in sql:
            return _csv([[self.marker]])
        if "pg_extension" in sql:
            return self.ext
        if "pg_namespace" in sql:
            return _csv([[self.ns]])
        if "FROM pg_database" in sql:
            return _csv([[self.dbs]])
        return super().query_csv(sql)


def _pscope(contract):
    return {"version": 1, "scope_id": "first-batch-production-candidate-r52", "mode": "production-candidate",
            "write_approval": {"approved_by": "isolated-test", "approved_at": "2026-11-25T14:17:28Z",
                                "approval_ref": "test-only-not-a-real-write-approval@16f94a6",
                                "approval_class": "test",
                                "bound_object_rule_ids": sorted(fbl.FIRST_BATCH_RULES)},
            "target_endpoint": {"dbname": "xiangrugu", "port": 5432, "container_id": FP, "test_only": True},
            "instance_fingerprint": FP,
            "contract_sha256": "c" * 64, "inventory_sha256": INV_SHA,
            "writeoff_evidence_sha256": dict(EV_SHAS),
            "objects": [{"rule_id": rid, "schema_name": "harv", "table": f"t_{rid}"}
                         for rid in fbl.FIRST_BATCH_RULES],
            "full_ready_for_import": False, "uncovered_members": 7995}


def _pexpected(contract):
    exp = _expected(contract)
    exp["contract_sha256"] = "c" * 64
    exp["inventory_sha256"] = INV_SHA
    exp["evidence_shas"] = dict(EV_SHAS)
    exp["instance_fingerprint"] = FP
    return exp


def _artifacts(contract):
    return {"contract": contract, "inventory": copy.deepcopy(INV_DOC), "evidence": copy.deepcopy(EV_DOCS)}


def _fn(contract):
    return lambda d: "c" * 64 if d is contract else "f" * 64


def _run(s, contract=None, scope=None, expected=None, artifacts=None, fn=None):
    contract = contract or _contract()
    return pe.run_production_load(s, scope or _pscope(contract), contract,
                                  {rid: _payload(rid) for rid in fbl.FIRST_BATCH_RULES},
                                  expected or _pexpected(contract),
                                  artifacts or _artifacts(contract), fn or _fn(contract))


def test_positive_with_legacy_cbdb_cbdb_reh_visible():
    contract = _contract()
    s = ProdFake(contract)
    ev = _run(s, contract)
    assert ev["status"] == "FIRST_BATCH_TRIAL_LOAD_PASS" and ev["total_rows"] == 47725
    assert ev["target_identity_in_session"]["legacy_databases_visible"] == ["cbdb", "cbdb_reh"]
    assert ev["target_identity_in_session"]["instance_marker_verified"] == FP
    assert s.commits == 1 and s.begins == 1
    joined = " ".join(s.sqls)
    assert "CREATE SCHEMA" not in joined and "CREATE EXTENSION" not in joined
    assert ev["recomputed_digests"]["contract_sha256"] == "c" * 64


def test_wrong_database_refused():
    contract = _contract()
    s = ProdFake(contract, dbname="cbdb")
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "wrong_database" and s.begins == 0


def test_wrong_port_refused():
    contract = _contract()
    s = ProdFake(contract, port="5433")
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "wrong_port" and s.begins == 0


def test_identity_unproven_marker_missing():
    contract = _contract()
    s = ProdFake(contract, marker="")
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "identity_unproven" and s.begins == 0


def test_identity_unproven_marker_mismatch():
    contract = _contract()
    s = ProdFake(contract, marker="9" * 64)
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "identity_unproven" and s.begins == 0


def test_fingerprint_drift_scope_vs_expected():
    contract = _contract()
    scope = _pscope(contract)
    scope["instance_fingerprint"] = "9" * 64
    s = ProdFake(contract)
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract, scope)
    assert e.value.code == "instance_fingerprint_drift" and s.begins == 0


def test_artifact_changed_but_caller_summaries_consistent_contract():
    contract = _contract()
    changed = copy.deepcopy(contract)
    changed["rules"][0]["targets"][0]["table"] = "tampered"
    s = ProdFake(contract)
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract, artifacts={"contract": changed, "inventory": copy.deepcopy(INV_DOC),
                                      "evidence": copy.deepcopy(EV_DOCS)})
    assert e.value.code == "artifact_drift_recomputed" and s.begins == 0


def test_artifact_changed_but_caller_summaries_consistent_inventory():
    contract = _contract()
    inv2 = copy.deepcopy(INV_DOC)
    inv2["entries"] = [{"relative_path": "x", "kind": "file", "size": 1, "sha256": "0" * 64}]
    s = ProdFake(contract)
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract, artifacts={"contract": contract, "inventory": inv2, "evidence": copy.deepcopy(EV_DOCS)})
    assert e.value.code == "artifact_drift_recomputed" and s.begins == 0


def test_artifact_changed_but_caller_summaries_consistent_evidence():
    contract = _contract()
    ev2 = copy.deepcopy(EV_DOCS)
    ev2["nul"]["x"] = 999
    s = ProdFake(contract)
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract, artifacts={"contract": contract, "inventory": copy.deepcopy(INV_DOC), "evidence": ev2})
    assert e.value.code == "artifact_drift_recomputed" and s.begins == 0


def test_missing_write_approval_refused():
    contract = _contract()
    scope = _pscope(contract)
    scope["write_approval"]["approval_ref"] = ""
    s = ProdFake(contract)
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract, scope)
    assert e.value.code == "write_approval_missing" and s.begins == 0


def test_approval_not_bound_to_seven_refused():
    contract = _contract()
    scope = _pscope(contract)
    scope["write_approval"]["bound_object_rule_ids"] = sorted(fbl.FIRST_BATCH_RULES)[:6]
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(ProdFake(contract), contract, scope)
    assert e.value.code == "write_approval_not_bound_to_seven_targets"


def test_test_approval_cannot_target_production_endpoint():
    contract = _contract()
    scope = _pscope(contract)
    scope["target_endpoint"] = {"host": "pg32b", "port": 5433, "dbname": "xiangrugu",
                                 "test_only": True, "container_id": FP}
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(ProdFake(contract), contract, scope)
    assert e.value.code == "test_approval_cannot_target_production"


def test_real_approval_requires_formal_target_and_authority():
    contract = _contract()
    scope = _pscope(contract)
    scope["write_approval"]["approval_class"] = "real"
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(ProdFake(contract), contract, scope)
    assert e.value.code == "real_approval_target_not_pg32b_xiangrugu"
    scope["target_endpoint"] = dict(pe.PRODUCTION_TARGET)
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(ProdFake(contract), contract, scope)
    assert e.value.code == "real_authority_ref_missing"


def test_target_exists_refused_no_overwrite():
    contract = _contract()
    s = ProdFake(contract, existing=("harv.t_m008003",))
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "target_already_exists" and s.begins == 0 and s.commits == 0


def test_prerequisites_missing_not_created():
    contract = _contract()
    s = ProdFake(contract, ext="0")
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "prerequisite_missing" and not any("CREATE EXTENSION" in q for q in s.sqls)
    s2 = ProdFake(contract, ns="harv")
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s2, contract)
    assert e.value.code == "prerequisite_missing" and not any("CREATE SCHEMA" in q for q in s2.sqls)


def test_injected_failure_rollback_zero_residue_clean_retry():
    contract = _contract()
    s = ProdFake(contract, corrupt=("t_m006642", 3))
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "readback_mismatch"
    assert s.rollbacks == 1 and s.commits == 0 and s.visible == set()
    s2 = ProdFake(contract)
    ev = _run(s2, contract)
    assert ev["committed"] and s2.commits == 1 and len(s2.visible) == 7


def test_full_ready_and_uncovered_gates_hold():
    contract = _contract()
    scope = _pscope(contract)
    scope["full_ready_for_import"] = True
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(ProdFake(contract), contract, scope)
    assert e.value.code == "full_ready_gate_flipped"
    scope = _pscope(contract)
    scope["uncovered_members"] = 7994
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(ProdFake(contract), contract, scope)
    assert e.value.code == "uncovered_count_drift"
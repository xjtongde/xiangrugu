"""Production entry candidate: in-session identity, prerequisites-not-created,
independent write approval, injected-failure rollback and clean retry."""
import pytest

from xiangrugu_datamgmt import production_entry as pe
from xiangrugu_datamgmt import first_batch_loader as fbl
from test_first_batch_loader import FakeSession, _contract, _payload, _expected, _csv


class ProdFake(FakeSession):
    def __init__(self, contract, existing=(), corrupt=None, dbname="xiangrugu", port="5432",
                 ext="1", ns="chgis,harv", dbs="postgres,template0,template1,xiangrugu"):
        super().__init__(contract, existing=existing, corrupt=corrupt)
        self.identity = [dbname, port, "172.17.0.9", "18.6", "2026-11-25 13:00:00+00"]
        self.ext, self.ns, self.dbs = ext, ns, dbs
        self.sqls = []

    def execute(self, sql):
        self.sqls.append(sql)
        super().execute(sql)

    def query_csv(self, sql):
        if "current_database()" in sql:
            return _csv([self.identity])
        if "pg_extension" in sql:
            return self.ext
        if "pg_namespace" in sql:
            return _csv([[self.ns]])
        if "FROM pg_database" in sql:
            return _csv([[self.dbs]])
        return super().query_csv(sql)


def _pscope(contract):
    return {"version": 1, "scope_id": "first-batch-production-candidate", "mode": "production-candidate",
            "write_approval": {"approved_by": "isolated-test", "approved_at": "2026-11-25T13:47:55Z",
                                "approval_ref": "test-only-not-a-real-write-approval@a1bd502",
                                "approval_class": "test"},
            "target_endpoint": {"dbname": "xiangrugu", "port": 5432, "container_id": "d" * 64, "test_only": True},
            "contract_sha256": "c" * 64, "inventory_sha256": "i" * 64,
            "writeoff_evidence_sha256": {"nul": "n" * 64, "chgis": "h" * 64},
            "objects": [{"rule_id": rid, "schema_name": "harv", "table": f"t_{rid}"}
                         for rid in fbl.FIRST_BATCH_RULES],
            "full_ready_for_import": False, "uncovered_members": 7995}


def _run(s, contract=None, scope=None, expected=None):
    contract = contract or _contract()
    return pe.run_production_load(s, scope or _pscope(contract), contract,
                                  {rid: _payload(rid) for rid in fbl.FIRST_BATCH_RULES},
                                  expected or _expected(contract))


def test_positive_prerequisites_not_created():
    contract = _contract()
    s = ProdFake(contract)
    ev = _run(s, contract)
    assert ev["status"] == "FIRST_BATCH_TRIAL_LOAD_PASS" and ev["total_rows"] == 47725
    assert s.commits == 1 and s.begins == 1
    joined = " ".join(s.sqls)
    assert "CREATE SCHEMA" not in joined and "CREATE EXTENSION" not in joined
    assert ev["target_identity_in_session"]["dbname"] == "xiangrugu"
    assert ev["approval_class"] == "test"
    assert ev["production_target_constant"] == {"host": "pg32b", "port": 5433, "dbname": "xiangrugu"}


def test_wrong_database_refused_in_session():
    contract = _contract()
    s = ProdFake(contract, dbname="xiangrugu_trial")
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "wrong_database" and s.begins == 0


def test_wrong_port_refused_in_session():
    contract = _contract()
    s = ProdFake(contract, port="5433")
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "wrong_port" and s.begins == 0


def test_missing_write_approval_refused():
    contract = _contract()
    scope = _pscope(contract)
    scope["write_approval"]["approval_ref"] = ""
    s = ProdFake(contract)
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract, scope)
    assert e.value.code == "write_approval_missing" and s.begins == 0


def test_real_approval_requires_formal_target():
    contract = _contract()
    scope = _pscope(contract)
    scope["write_approval"]["approval_class"] = "real"
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(ProdFake(contract), contract, scope)
    assert e.value.code == "real_approval_target_not_pg32b_xiangrugu"


def test_real_approval_requires_authority_ref():
    contract = _contract()
    scope = _pscope(contract)
    scope["write_approval"]["approval_class"] = "real"
    scope["target_endpoint"] = dict(pe.PRODUCTION_TARGET)
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(ProdFake(contract), contract, scope)
    assert e.value.code == "real_authority_ref_missing"


def test_contract_artifact_drift_refused():
    contract = _contract()
    scope = _pscope(contract)
    scope["contract_sha256"] = "f" * 64
    s = ProdFake(contract)
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract, scope)
    assert e.value.code == "artifact_drift" and s.begins == 0


def test_evidence_artifact_drift_refused():
    contract = _contract()
    scope = _pscope(contract)
    scope["writeoff_evidence_sha256"]["chgis"] = "f" * 64
    s = ProdFake(contract)
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract, scope)
    assert e.value.code == "artifact_drift" and s.begins == 0


def test_target_exists_refused_no_overwrite():
    contract = _contract()
    s = ProdFake(contract, existing=("harv.t_m008003",))
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "target_already_exists" and s.begins == 0 and s.commits == 0


def test_postgis_prerequisite_missing_not_created():
    contract = _contract()
    s = ProdFake(contract, ext="0")
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "prerequisite_missing" and s.begins == 0
    assert not any("CREATE EXTENSION" in q for q in s.sqls)


def test_schema_prerequisite_missing_not_created():
    contract = _contract()
    s = ProdFake(contract, ns="harv")
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "prerequisite_missing" and s.begins == 0
    assert not any("CREATE SCHEMA" in q for q in s.sqls)


def test_injected_readback_failure_rollback_zero_residue_then_clean_retry():
    contract = _contract()
    s = ProdFake(contract, corrupt=("t_m006642", 3))
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "readback_mismatch"
    assert s.rollbacks == 1 and s.commits == 0 and s.visible == set()
    s2 = ProdFake(contract)
    ev = _run(s2, contract)
    assert ev["committed"] and s2.commits == 1 and len(s2.visible) == 7


def test_production_database_visible_refused():
    contract = _contract()
    s = ProdFake(contract, dbs="postgres,template0,template1,xiangrugu,cbdb")
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "production_database_visible" and s.begins == 0


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
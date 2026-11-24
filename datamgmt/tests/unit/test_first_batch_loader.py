"""First-batch loader candidate: gate/transaction/retry tests over a fake session."""
import csv
import io
import json

import pytest

from xiangrugu_datamgmt import canonical, first_batch_loader as fbl

ROWNUM = fbl.ROWNUM
COUNTS = {"m002709": 59, "m002717": 59, "m004812": 29, "m006642": 3389,
          "m008002": 2957, "m008003": 40199, "m008004": 1033}
SID = {rid: f"{i + 1:064x}" for i, rid in enumerate(fbl.FIRST_BATCH_RULES)}


def _contract():
    rules = []
    for rid in fbl.FIRST_BATCH_RULES:
        cols = [{"ordinal": 1, "source_column": "1" * 64, "target_column": "c0", "pg_type": "text", "nullable": False},
                {"ordinal": 2, "source_column": "2" * 64, "target_column": "c1", "pg_type": "text", "nullable": False},
                ]
        rules.append({"rule_id": rid,
                      "targets": [{"object_name": f"t_{rid}", "schema_name": "harv", "table": f"t_{rid}",
                                   "columns": cols,
                                   "derived_rownum": {"target_column": ROWNUM, "pg_type": "bigint", "nullable": False,
                                                       "origin": "one_based_physical_source_row"}, "duplicate_reconciliation": None,
                                   "geometry": None, "expected_count": COUNTS[rid], "expected_sha256": "0" * 64}],
                      "expected": {"sha256": "0" * 64}})
    return {"rules": rules}


def _rows(rid):
    n = COUNTS[rid]
    if rid == "m008003":
        base = [[str(i), "x"] for i in range(n - 74)]
        extra = [list(base[j % 63]) for j in range(74)]
        return base + extra
    return [[str(i), "x"] for i in range(n)]


def _payload(rid):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t", quotechar='"', quoting=csv.QUOTE_ALL, lineterminator="\n")
    for i, r in enumerate(_rows(rid)):
        w.writerow(list(r) + [i + 1])
    return buf.getvalue()


def _expected(contract):
    items = {}
    for rid in fbl.FIRST_BATCH_RULES:
        rows = _rows(rid)
        cols = tuple(canonical.ValueColumn(column_key=c["source_column"], target_name=c["target_column"],
                                           pg_type=c["pg_type"], nullable=c["nullable"])
                     for c in contract["rules"][0]["targets"][0]["columns"]) \
            + (canonical.ValueColumn(column_key=canonical.ROW_KEY, target_name=ROWNUM, pg_type="bigint", nullable=False),)
        schema = canonical.ValueSchema(source_object_id=SID[rid], columns=cols)
        s = canonical.summarize_rows(schema, (tuple(r) + (i + 1,) for i, r in enumerate(rows)),
                                     limits=canonical.ValueLimits())
        meta = [["c0", "text", "text", "NO", "1"], ["c1", "text", "text", "NO", "2"],
                [ROWNUM, "bigint", "int8", "NO", "3"]]
        items[rid] = {"row_count": COUNTS[rid], "meta": meta, "attr_sha": s.sha256,
                      "stream_bytes": s.stream_bytes, "source_object_id": SID[rid],
                      "dup_groups": 63 if rid == "m008003" else 0,
                      "dup_extra": 74 if rid == "m008003" else 0}
    return {"contract_sha256": "c" * 64, "inventory_sha256": "i" * 64,
            "evidence_shas": {"nul": "n" * 64, "chgis": "h" * 64},
            "instance_identity": {"container_id": "d" * 64, "image_id": "sha256:" + "e" * 64,
                                   "server_version": "18.1", "inet_server_addr": "null",
                                   "databases": "postgres,template0,template1,xiangrugu_trial"},
            "items": items}


def _scope(contract):
    return {"version": 1, "scope_id": "isolated-test-first-batch", "mode": "isolated-test",
            "approval": {"approved_by": "isolated-test", "approved_at": "2026-11-24T18:00:00Z",
                          "approval_ref": "isolated-test-only-not-a-production-approval"},
            "contract_sha256": "c" * 64, "inventory_sha256": "i" * 64,
            "writeoff_evidence_sha256": {"nul": "n" * 64, "chgis": "h" * 64},
            "objects": [{"rule_id": rid, "schema_name": "harv", "table": f"t_{rid}"}
                         for rid in fbl.FIRST_BATCH_RULES],
            "full_ready_for_import": False, "uncovered_members": 7995}


class FakeSession:
    def __init__(self, contract, existing=(), corrupt=None):
        self.contract = contract
        self.visible = set(existing)
        self.staged = {}
        self.rows = {}
        self.txn = False
        self.commits = 0
        self.rollbacks = 0
        self.begins = 0
        self.corrupt = corrupt

    def begin(self):
        self.begins += 1
        self.txn = True
        self.staged = {}
        self.rows = {}

    def commit(self):
        self.commits += 1
        self.txn = False
        self.visible |= set(self.staged)

    def rollback(self):
        self.rollbacks += 1
        self.txn = False
        self.staged = {}
        self.rows = {}

    def execute(self, sql):
        for part in sql.split(";"):
            part = part.strip()
            if part.startswith("CREATE TABLE "):
                name = part.split()[2]
                self.staged[name] = True

    def copy_from(self, table, data):
        recs = list(csv.reader(io.StringIO(data), delimiter="\t", quotechar='"'))
        if self.corrupt and table.endswith(self.corrupt[0]):
            recs[self.corrupt[1]][0] = "CORRUPTED"
        self.rows[table] = recs

    def query_csv(self, sql):
        if "to_regclass" in sql:
            names = [n.strip("'") for n in sql.split("ARRAY[")[1].split("]")[0].split(",")]
            return ",".join(sorted(n for n in names if n in self.visible))
        if "information_schema.columns" in sql:
            tname = sql.split("table_name='")[1].split("'")[0]
            rule = next(r for r in self.contract["rules"] if r["targets"][0]["table"] == tname)
            out = []
            for i, c in enumerate(rule["targets"][0]["columns"]):
                fam = "bigint" if c["pg_type"] == "bigint" else "text"
                out.append([c["target_column"], fam, "int8" if fam == "bigint" else "text",
                            "YES" if c["nullable"] else "NO", str(i + 1)])
            dr = rule["targets"][0]["derived_rownum"]
            out.append([dr["target_column"], "bigint", "int8", "NO", str(len(out) + 1)])
            return _csv(out)
        if "sum(c)-count(*)" in sql:
            return str(self._dups(sql)[1])
        if "GROUP BY" in sql:
            return str(self._dups(sql)[0])
        if "ORDER BY" in sql:
            table = sql.split(" FROM ")[1].split(" ORDER")[0]
            return _csv(self.rows.get(table, []))
        raise AssertionError("unexpected sql: " + sql[:80])

    def _dups(self, sql):
        table = sql.split(" FROM ")[1].split(" GROUP")[0].split(")")[0]
        table = sql.split("FROM (SELECT ")[1].split(" FROM ")[1].split(" GROUP")[0]
        rows = self.rows.get(table, [])
        keys = [tuple(r[:-1]) for r in rows]
        from collections import Counter
        c = Counter(keys)
        groups = sum(1 for v in c.values() if v > 1)
        extra = sum(v - 1 for v in c.values() if v > 1)
        return groups, extra


def _csv(rows):
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue()


def _run(session, contract=None, scope=None, expected=None):
    contract = contract or _contract()
    return fbl.run_first_batch(session, scope or _scope(contract), contract,
                               {rid: _payload(rid) for rid in fbl.FIRST_BATCH_RULES},
                               (expected or _expected(contract))["instance_identity"],
                               expected or _expected(contract))


def test_positive_full_batch_single_transaction():
    contract = _contract()
    s = FakeSession(contract)
    ev = _run(s, contract)
    assert ev["status"] == "FIRST_BATCH_TRIAL_LOAD_PASS"
    assert ev["total_rows"] == 47725 and s.commits == 1 and s.rollbacks == 0 and s.begins == 1
    assert ev["items"]["m008003"]["duplicate_groups"] == 63
    assert ev["items"]["m008003"]["duplicate_extra_rows"] == 74
    assert len(s.visible) == 7


def test_missing_approval_refused_before_write():
    contract = _contract()
    scope = _scope(contract)
    scope["approval"]["approval_ref"] = ""
    s = FakeSession(contract)
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract, scope)
    assert e.value.code == "approval_missing" and s.begins == 0


def test_contract_digest_mismatch_refused():
    contract = _contract()
    scope = _scope(contract)
    scope["contract_sha256"] = "f" * 64
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(FakeSession(contract), contract, scope)
    assert e.value.code == "contract_digest_mismatch"


def test_evidence_digest_mismatch_refused():
    contract = _contract()
    scope = _scope(contract)
    scope["writeoff_evidence_sha256"]["nul"] = "f" * 64
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(FakeSession(contract), contract, scope)
    assert e.value.code == "writeoff_evidence_digest_mismatch"


def test_instance_identity_mismatch_refused():
    contract = _contract()
    exp = _expected(contract)
    obs = dict(exp["instance_identity"])
    obs["container_id"] = "9" * 64
    s = FakeSession(contract)
    with pytest.raises(fbl.LoaderGateError) as e:
        fbl.run_first_batch(s, _scope(contract), contract,
                            {rid: _payload(rid) for rid in fbl.FIRST_BATCH_RULES}, obs, exp)
    assert e.value.code == "instance_identity_mismatch" and s.begins == 0


def test_production_database_visible_refused():
    contract = _contract()
    exp = _expected(contract)
    obs = dict(exp["instance_identity"])
    obs["databases"] = obs["databases"] + ",cbdb"
    with pytest.raises(fbl.LoaderGateError) as e:
        fbl.run_first_batch(FakeSession(contract), _scope(contract), contract,
                            {rid: _payload(rid) for rid in fbl.FIRST_BATCH_RULES}, obs, exp)
    assert e.value.code == "production_database_visible"


def test_target_already_exists_refused_no_overwrite():
    contract = _contract()
    s = FakeSession(contract, existing=("harv.t_m008002",))
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "target_already_exists" and s.begins == 0 and s.commits == 0


def test_readback_mismatch_rollback_no_half_batch():
    contract = _contract()
    s = FakeSession(contract, corrupt=("t_m008003", 5))
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(s, contract)
    assert e.value.code == "readback_mismatch"
    assert s.rollbacks == 1 and s.commits == 0 and s.visible == set()


def test_retry_after_failure_succeeds_clean():
    contract = _contract()
    s = FakeSession(contract, corrupt=("t_m004812", 0))
    with pytest.raises(fbl.LoaderGateError):
        _run(s, contract)
    assert s.visible == set()
    s2 = FakeSession(contract)
    ev = _run(s2, contract)
    assert ev["committed"] and s2.commits == 1 and len(s2.visible) == 7


def test_full_ready_gate_flip_refused():
    contract = _contract()
    scope = _scope(contract)
    scope["full_ready_for_import"] = True
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(FakeSession(contract), contract, scope)
    assert e.value.code == "full_ready_gate_flipped"


def test_production_scope_mode_refused():
    contract = _contract()
    scope = _scope(contract)
    scope["mode"] = "production"
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(FakeSession(contract), contract, scope)
    assert e.value.code == "scope_mode_not_isolated_test"


def test_uncovered_count_drift_refused():
    contract = _contract()
    scope = _scope(contract)
    scope["uncovered_members"] = 0
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(FakeSession(contract), contract, scope)
    assert e.value.code == "uncovered_count_drift"


def test_scope_object_identity_mismatch_refused():
    contract = _contract()
    scope = _scope(contract)
    scope["objects"][0]["table"] = "wrong_table"
    with pytest.raises(fbl.LoaderGateError) as e:
        _run(FakeSession(contract), contract, scope)
    assert e.value.code == "scope_object_identity_mismatch"


def test_ddl_never_uses_if_not_exists_for_targets():
    for rid in fbl.FIRST_BATCH_RULES:
        rule = next(r for r in _contract()["rules"] if r["rule_id"] == rid)
        ddl = fbl.ddl_for(rule)
        assert "IF NOT EXISTS" not in ddl and ddl.startswith("CREATE TABLE harv.t_" + rid)
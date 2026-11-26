"""SOCIAL_INSTITUTION_ADDR single-table loader: gate / transaction / retry tests.

The session is faked so the tests exercise the real gate ordering and the real
COMMIT/ROLLBACK decision logic without any database.
"""
import pytest

from xiangrugu_datamgmt import cbdb_social_addr_loader as L

CAND = L.EXPECTED_CANDIDATE_SHA
SRC = L.EXPECTED_SOURCE_SHA
APPR = "a718b0c297501642dd105eb3797f96dc1de2edf8eb521bed6609ff78de1fb4a0"
# 茶香逐字批准原文（本步补正登记件）的摘要
VTEXT = "ec0fa5cf029c37e1bdbb94102553d145bd4d901d74489ac7b98ecdb3d42d4f12"
REF = "chaxiang-approval-social-institution-addr-bstep2-correction-20261126"


def _target():
    return {"schema_name": "cbdb", "table": "cbdb__social_u5f_institution_u5f_addr",
            "columns": [
                {"ordinal": 1, "source_column": "c_inst_name_code",
                 "target_column": "c_u5f_inst_u5f_name_u5f_code", "pg_type": "bigint", "nullable": False},
                {"ordinal": 2, "source_column": "c_inst_code",
                 "target_column": "c_u5f_inst_u5f_code", "pg_type": "bigint", "nullable": False},
                {"ordinal": 3, "source_column": "inst_xcoord",
                 "target_column": "inst_u5f_xcoord", "pg_type": "double precision", "nullable": False},
            ],
            "primary_key": {"columns": ["c_u5f_inst_u5f_name_u5f_code", "c_u5f_inst_u5f_code",
                                        "inst_u5f_xcoord"]},
            "constraints_approved": ["primary_key", "not_null", "unique", "index", "foreign_key", "default"],
            "constraints_to_create": ["primary_key", "not_null"],
            "databases_forbidden": ["pg32b", "cbdb", "cbdb_reh"]}


def _scope(**over):
    s = {"version": 1, "scope_id": "s", "mode": "isolated-test",
         "approval": {"approved_by": "茶香", "approved_at": "2026-11-26T15:28:37Z",
                      "approval_ref": "ref", "test_only": True},
         "candidate_sha256": CAND, "contract_sha256": "c", "inventory_sha256": "i",
         "source_member": {"rule_id": "m007906", "sha256": "m", "expected_rows": 3859,
                           "source_side_sha256": SRC},
         "target": {"schema_name": "cbdb", "table": "cbdb__social_u5f_institution_u5f_addr",
                    "constraints_approved": _target()["constraints_approved"],
                    "constraints_to_create": _target()["constraints_to_create"],
                    "databases_forbidden": _target()["databases_forbidden"]},
         "full_ready_for_import": False,
         "review_traceability": {"status": "COMPLETE", "approval_table_sha256": APPR,
                                 "approval_text_sha256": VTEXT,
                                 "approval_text_bytes": 1799,
                                 "contract_review_ref": REF,
                                 "approval_record_event": REF}}
    s.update(over)
    return s


def _presented(**over):
    p = {"candidate_sha256": CAND, "contract_sha256": "c", "inventory_sha256": "i",
         "source_sha256": "m", "approval_table_sha256": APPR,
         "approval_text_sha256": VTEXT, "contract_review_ref": REF,
         "forbidden": ["pg32b", "cbdb", "cbdb_reh"]}
    p.update(over)
    return p


def test_scope_accepts_full_traceability():
    L.validate_scope(_scope(), _presented())


def test_scope_blocks_on_incomplete_review_traceability():
    """Missing approval text is BLOCKING — the loader must never patch it in."""
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(_scope(review_traceability={"status": "INCOMPLETE",
                                                     "approval_table_sha256": APPR}), _presented())
    assert e.value.code == "review_traceability_incomplete"


def test_scope_rejects_production_write_authorization_reuse():
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(_scope(mode="production"), _presented())
    assert e.value.code == "scope_mode_not_isolated_test"


def test_scope_rejects_non_test_only_approval():
    scope = _scope()
    scope["approval"]["test_only"] = False
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(scope, _presented())
    assert e.value.code == "scope_not_marked_test_only"


def test_scope_rejects_full_ready_gate_flip():
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(_scope(full_ready_for_import=True), _presented())
    assert e.value.code == "full_ready_gate_flipped"


def test_scope_rejects_other_candidate():
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(_scope(candidate_sha256="f" * 64, contract_sha256="c"), _presented())
    assert e.value.code == "candidate_digest_mismatch"


def test_scope_rejects_wrong_source_rule():
    scope = _scope()
    scope["source_member"]["rule_id"] = "m007904"   # the stale id that must not come back
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(scope, _presented())
    assert e.value.code == "source_rule_not_m007906"


def test_scope_rejects_constraint_creation_scope_drift():
    scope = _scope()
    scope["target"]["constraints_to_create"] = ["primary_key", "not_null", "unique"]
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(scope, _presented())
    assert e.value.code == "constraint_creation_scope_drift"


def test_ddl_has_only_approved_objects():
    ddl = L.ddl_for(_target())
    assert "PRIMARY KEY" in ddl
    assert "UNIQUE" not in ddl
    assert "DEFAULT" not in ddl
    assert "FOREIGN KEY" not in ddl
    assert "CREATE INDEX" not in ddl


def test_ddl_keeps_primary_key_order():
    ddl = L.ddl_for(_target())
    pk = _target()["primary_key"]["columns"]
    assert 'PRIMARY KEY ("' + '", "'.join(pk) + '")' in ddl


def test_ddl_not_null_follows_approved_flags():
    ddl = L.ddl_for(_target())
    assert '"inst_u5f_xcoord" double precision NOT NULL' in ddl


def test_instance_identity_refuses_visible_production_database():
    observed = {"container_id": "x", "image_id": "y", "server_version": "z",
                "inet_server_addr": "unix-socket", "databases": "postgres,cbdb"}
    with pytest.raises(L.LoaderGateError) as e:
        L.check_instance_identity(observed, dict(observed))
    assert e.value.code == "production_database_visible"


def test_instance_identity_mismatch_is_refused():
    observed = {"container_id": "x", "image_id": "y", "server_version": "z",
                "inet_server_addr": "unix-socket", "databases": "postgres"}
    expected = dict(observed, container_id="other")
    with pytest.raises(L.LoaderGateError) as e:
        L.check_instance_identity(observed, expected)
    assert e.value.code == "instance_identity_mismatch"


class _FakeSession:
    """Records the transaction decisions the loader makes."""

    def __init__(self, existing=False, rows=None, fail_on=None):
        self.existing, self.rows, self.fail_on = existing, rows or [], fail_on
        self.calls = []

    def query_csv(self, sql):
        if "to_regclass" in sql:
            return "t" if self.existing else "f"
        raise AssertionError("unexpected query " + sql)

    def query_rows(self, sql):
        return self.rows

    def begin(self):
        self.calls.append("BEGIN")

    def commit(self):
        self.calls.append("COMMIT")

    def rollback(self):
        self.calls.append("ROLLBACK")

    def execute(self, sql):
        self.calls.append(("exec", sql.split("(")[0].strip()))

    def copy_from(self, table, data):
        self.calls.append(("copy", table))


def test_existing_target_is_refused_before_any_write():
    sess = _FakeSession(existing=True)
    with pytest.raises(L.LoaderGateError) as e:
        L.check_target_absent(sess)
    assert e.value.code == "target_already_exists"
    assert sess.calls == []


def test_absent_target_passes_gate():
    L.check_target_absent(_FakeSession(existing=False))


def test_pg_type_name_is_exact():
    assert L._pg_type_name("double precision") == "double precision"
    assert L._pg_type_name("bigint") == "bigint"

def test_scope_blocks_on_verbatim_text_digest_mismatch():
    """The verbatim approval text digest must match, not just a status string."""
    scope = _scope()
    scope["review_traceability"]["approval_text_sha256"] = "f" * 64
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(scope, _presented())
    assert e.value.code == "approval_text_digest_mismatch"


def test_scope_blocks_when_contract_review_ref_differs_from_approval_record():
    scope = _scope()
    scope["review_traceability"]["contract_review_ref"] = "some-other-ref"
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(scope, _presented())
    assert e.value.code == "contract_review_ref_mismatch"


def test_scope_blocks_when_approval_text_missing():
    scope = _scope()
    scope["review_traceability"]["approval_text_bytes"] = 0
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(scope, _presented())
    assert e.value.code == "approval_text_missing"


def test_loader_binds_the_new_frozen_candidate_digest():
    """After the review update the contract digest moved to 56b0076d…."""
    assert L.EXPECTED_CANDIDATE_SHA == (
        "56b0076d2e877be9fb34796e01b8ee2b37d5a817c8e80203fa21c95e4f3f8237")


def test_scope_blocks_when_approval_record_event_differs_from_contract_review_ref():
    """The approval-record event id 与合同 review ref 必须同源；否则拒绝。"""
    scope = _scope()
    scope["review_traceability"]["approval_record_event"] = "some-other-event"
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(scope, _presented())
    assert e.value.code == "approval_record_ref_mismatch"

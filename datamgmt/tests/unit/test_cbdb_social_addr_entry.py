"""Formal execution-command candidate: endpoint / marker / role / one-parse gates."""
import pytest

from xiangrugu_datamgmt import cbdb_social_addr_entry as E
from xiangrugu_datamgmt import cbdb_social_addr_loader as L

CAND = "56b0076d2e877be9fb34796e01b8ee2b37d5a817c8e80203fa21c95e4f3f8237"
APPR = "a718b0c297501642dd105eb3797f96dc1de2edf8eb521bed6609ff78de1fb4a0"
VTEXT = "ec0fa5cf029c37e1bdbb94102553d145bd4d901d74489ac7b98ecdb3d42d4f12"
REF = "chaxiang-approval-social-institution-addr-bstep2-correction-20261126"
FP = "303439004f2951b0cb04f0acdf24ea82230a90d314a817b2e953760e494dc846"


def _scope(**over):
    s = {
        "version": 1, "mode": "execution-candidate",
        "write_approval": {"approved_by": "茶香", "approved_at": "2026-11-26T16:55:36Z",
                           "approval_ref": REF, "approval_class": "test",
                           "bound_object_rule_ids": ["m007906"]},
        "target_endpoint": {"host": "pg32b", "port": 5433, "dbname": "xiangrugu",
                            "in_session_port": 5432, "test_only": True,
                            "container_id": FP},
        "endpoint_mapping_verified": True,
        "target": {"schema_name": "cbdb", "table": "cbdb__social_u5f_institution_u5f_addr"},
        "contract_sha256": CAND, "inventory_sha256": "i",
        "approval_table_sha256": APPR, "approval_text_sha256": VTEXT,
        "instance_fingerprint": FP, "contract_review_ref": REF,
        "full_ready_for_import": False,
    }
    s.update(over)
    return s


def _presented(**over):
    p = {"contract_sha256": CAND, "inventory_sha256": "i",
         "approval_table_sha256": APPR, "approval_text_sha256": VTEXT,
         "instance_fingerprint": FP}
    p.update(over)
    return p


def _loader_presented(scope, **over):
    """What the LOADER gate expects to be told about this scope."""
    rt = scope.get("review_traceability") or {}
    p = {"candidate_sha256": scope["candidate_sha256"],
         "contract_sha256": scope["contract_sha256"],
         "inventory_sha256": scope["inventory_sha256"],
         "source_sha256": scope["source_member"]["sha256"],
         "approval_table_sha256": rt.get("approval_table_sha256"),
         "approval_text_sha256": rt.get("approval_text_sha256"),
         "contract_review_ref": rt.get("contract_review_ref"),
         "forbidden": scope["target"]["databases_forbidden"]}
    p.update(over)
    return p


# ---------------------------------------------------------------- Gate A
def test_endpoint_accepts_pg32b_5433_xiangrugu():
    E.validate_execution_scope(_scope(), _presented())


def test_endpoint_rejects_port_5432_as_target():
    """5432 is the in-session port; it must never be the declared target."""
    s = _scope()
    s["target_endpoint"]["port"] = 5432
    with pytest.raises(E.LoaderGateError) as e:
        E.validate_execution_scope(s, _presented())
    assert e.value.code == "target_port_not_5433"


def test_endpoint_requires_in_session_port_declared_5432():
    s = _scope()
    s["target_endpoint"]["in_session_port"] = 5433
    with pytest.raises(E.LoaderGateError) as e:
        E.validate_execution_scope(s, _presented())
    assert e.value.code == "in_session_port_not_declared_5432"


def test_endpoint_rejects_wrong_host():
    s = _scope()
    s["target_endpoint"]["host"] = "pg32"
    with pytest.raises(E.LoaderGateError) as e:
        E.validate_execution_scope(s, _presented())
    assert e.value.code == "target_host_not_pg32b"


def test_formal_dbname_is_fixed_when_not_test_only():
    """A real approval must target the literal database name xiangrugu."""
    s = _scope()
    s["target_endpoint"]["dbname"] = "otherdb"
    s["write_approval"]["approval_class"] = "real"
    s["real_authority_ref"] = "some-real-auth"
    with pytest.raises(E.LoaderGateError) as e:
        E.validate_execution_scope(s, _presented())
    assert e.value.code == "target_dbname_not_xiangrugu"


def test_isolated_stand_in_may_use_a_different_dbname():
    """A test-only stand-in (e.g. trialdb) is allowed; the formal name is not."""
    s = _scope()
    s["target_endpoint"]["dbname"] = "trialdb"
    E.validate_execution_scope(s, _presented())


# ---------------------------------------------------------------- Gate E
def test_test_approval_cannot_target_production():
    """A test approval that is not explicitly test-only is reaching the formal target."""
    s = _scope()
    s["target_endpoint"]["test_only"] = False
    with pytest.raises(E.LoaderGateError) as e:
        E.validate_execution_scope(s, _presented())
    assert e.value.code == "test_approval_cannot_target_production"


def test_test_approval_cannot_bind_the_production_container():
    """Even with test_only=True, binding the real pg32b container is refused."""
    s = _scope()
    s["target_endpoint"]["container_id"] = E._PRODUCTION_CONTAINER_ID
    with pytest.raises(E.LoaderGateError) as e:
        E.validate_execution_scope(s, _presented())
    assert e.value.code == "test_approval_cannot_target_production"


def test_test_approval_allowed_on_isolated_stand_in():
    """The normal case: isolated container, test_only, not the production container."""
    E.validate_execution_scope(_scope(), _presented())


def test_test_approval_must_declare_container_id():
    s = _scope()
    s["target_endpoint"]["container_id"] = ""
    with pytest.raises(E.LoaderGateError) as e:
        E.validate_execution_scope(s, _presented())
    assert e.value.code == "test_endpoint_missing_container_id"


def test_real_approval_requires_authority_ref():
    s = _scope()
    s["write_approval"]["approval_class"] = "real"
    with pytest.raises(E.LoaderGateError) as e:
        E.validate_execution_scope(s, _presented())
    assert e.value.code == "real_authority_ref_missing"


def test_first_batch_approval_reuse_is_forbidden():
    s = _scope()
    s["write_approval"]["approval_ref"] = "88f4f1ac-first-batch"
    with pytest.raises(E.LoaderGateError) as e:
        E.validate_execution_scope(s, _presented())
    assert e.value.code == "first_batch_approval_reuse_forbidden"


def test_write_approval_must_bind_this_single_rule():
    s = _scope()
    s["write_approval"]["bound_object_rule_ids"] = ["m007904"]
    with pytest.raises(E.LoaderGateError) as e:
        E.validate_execution_scope(s, _presented())
    assert e.value.code == "write_approval_not_bound_to_single_target"


def test_full_ready_gate_must_stay_false():
    with pytest.raises(E.LoaderGateError) as e:
        E.validate_execution_scope(_scope(full_ready_for_import=True), _presented())
    assert e.value.code == "full_ready_gate_flipped"


def test_artifact_drift_is_refused():
    with pytest.raises(E.LoaderGateError) as e:
        E.validate_execution_scope(_scope(), _presented(approval_text_sha256="0" * 64))
    assert e.value.code == "artifact_drift"


# ------------------------------------------------------- Gate B/C (session)
class _Sess:
    """Minimal psql-session stub. Keys are matched most-specific-first."""

    # Ordered so that 'count(*)' does not swallow 'instance_marker IS NOT NULL',
    # and the marker SELECT is checked before the generic marker predicates.
    ORDER = (
        "SELECT instance_id FROM public.xrg_instance_marker",
        "count(*) FROM public.xrg_instance_marker",
        "to_regclass('public.xrg_instance_marker') IS NOT NULL",
        "string_agg(datname",
        "current_user",
        "current_setting('role', true)",
        "current_database()",
        "SHOW server_version",
        "SHOW port",
        "inet_server_addr()",
        "rolsuper",
        "to_regnamespace",
    )

    def __init__(self, answers):
        self.a = dict(answers)

    def query_csv(self, sql):
        s = " ".join(sql.split())
        for k in self.ORDER:
            if k in s:
                return str(self.a.get(k, ""))
        return ""


def _answers(**over):
    a = {"current_database()": "xiangrugu",
         "SHOW server_version": "18.6",
         "inet_server_addr()": "unix-socket",
         "SHOW port": "5432",
         "to_regclass('public.xrg_instance_marker') IS NOT NULL": "1",
         "string_agg(datname": "postgres,template0,template1,trialdb",
         "count(*) FROM public.xrg_instance_marker": "1",
         "SELECT instance_id FROM public.xrg_instance_marker": FP,
         "current_user": E.LOAD_ROLE,
         "current_setting('role', true)": "none",
         "rolsuper": "0",
         "to_regnamespace": "0"}
    a.update(over)
    return a


def test_session_verification_rejects_missing_marker():
    sess = _Sess(_answers(**{"to_regclass('public.xrg_instance_marker') IS NOT NULL": "0"}))
    with pytest.raises(E.LoaderGateError) as e:
        E.verify_instance_and_role_in_session(sess, _scope(), {})
    assert e.value.code == "marker_table_missing"


def test_session_verification_rejects_marker_value_mismatch():
    sess = _Sess(_answers(**{"SELECT instance_id FROM public.xrg_instance_marker": "other"}))
    with pytest.raises(E.LoaderGateError):
        E.verify_instance_and_role_in_session(sess, _scope(), {})


def test_session_verification_rejects_in_session_port_not_5432():
    sess = _Sess(_answers(**{"SHOW port": "6000"}))
    with pytest.raises(E.LoaderGateError) as e:
        E.verify_instance_and_role_in_session(sess, _scope(), {})
    assert e.value.code == "in_session_port_mismatch"


def test_session_verification_rejects_superuser_load_role():
    sess = _Sess(_answers(**{"rolsuper": "1"}))
    with pytest.raises(E.LoaderGateError) as e:
        E.verify_instance_and_role_in_session(sess, _scope(), {})
    assert e.value.code == "load_role_is_superuser"


def test_session_verification_rejects_wrong_role():
    sess = _Sess(_answers(**{"current_user": "postgres"}))
    with pytest.raises(E.LoaderGateError) as e:
        E.verify_instance_and_role_in_session(sess, _scope(), {})
    assert e.value.code == "load_role_mismatch"


def test_target_from_parsed_rejects_non_m007906():
    class T:
        schema_name, table = "cbdb", "cbdb__social_u5f_institution_u5f_addr"
        columns, primary_key = (), type("K", (), {"columns": ("a",)})()
        expected_count, expected_sha256 = 3859, "x" * 64

    class R:
        rule_id, targets = "m007904", (T(),)

    class P:
        rules = (R(),)
        status, review, sha256 = "frozen", object(), "f" * 64

    with pytest.raises(E.LoaderGateError) as e:
        E.target_from_parsed(P())
    assert e.value.code == "contract_rule_set_mismatch"

def test_role_none_literal_means_no_set_role_and_is_accepted():
    """PG returns the literal 'none' when no SET ROLE was issued; that is the normal case."""
    sess = _Sess(_answers(**{"current_setting('role', true)": "none"}))
    ev = E.verify_instance_and_role_in_session(sess, _scope(), {})
    assert ev["load_role"] == E.LOAD_ROLE


def test_active_set_role_override_is_refused():
    """A session that switched into another role must not be trusted as the load role."""
    sess = _Sess(_answers(**{"current_setting('role', true)": "postgres"}))
    with pytest.raises(E.LoaderGateError) as e:
        E.verify_instance_and_role_in_session(sess, _scope(), {})
    assert e.value.code == "load_role_override_active"


# ---------------------------------------------------------- formal (real) branch
import hashlib as _hashlib

PROD_AUTH_TEXT = (
    "\u8336\u9999\u6279\u51c6\u539f\u6587\uff08\u6b63\u5f0f\u5199\u5e93\uff09\n"
    "\u6211\u6279\u51c6\u5c06\u6e90\u6210\u5458 m007906 \u7684 SOCIAL_INSTITUTION_ADDR "
    "\u6620\u5c04\u5230 cbdb.cbdb__social_u5f_institution_u5f_addr\u3002\n"
    "\u4ec5\u9650\u8be5\u5355\u8868\u3002")
PROD_AUTH_SHA = _hashlib.sha256(PROD_AUTH_TEXT.encode("utf-8")).hexdigest()


def _target():
    return {
        "schema_name": "cbdb", "table": "cbdb__social_u5f_institution_u5f_addr",
        "columns": [{"ordinal": i, "source_column": "s%d" % i, "target_column": "t%d" % i,
                     "pg_type": "text", "nullable": True} for i in range(1, 12)],
        "primary_key": {"columns": ["t1", "t2", "t3", "t4", "t5", "t6"]},
        "expected_count": 3859, "expected_sha256": "x" * 64,
    }


def _real_scope(**over):
    s = _scope()
    s["write_approval"] = {
        "approved_by": "\u8336\u9999", "approved_at": "2026-11-27T01:10:00Z",
        "approval_ref": "chaxiang-real-write-social-institution-addr-20261127",
        "approval_class": "real",
        "approval_text_sha256": PROD_AUTH_SHA,
        "bound_object_rule_ids": ["m007906"],
    }
    s["target_endpoint"] = {"host": "pg32b", "port": 5433, "dbname": "xiangrugu",
                            "in_session_port": 5432}
    s["real_authority_ref"] = "chaxiang-real-write-social-institution-addr-20261127"
    s["expected_source_member_sha256"] = "m" * 64
    s["expected_source_sha256"] = "2cb8c354b0e75e6ae230e3b00540146e823eaa8de8def2abce89ad6179a07579"
    s["real_write_authorization"] = {
        "approval_class": "real",
        "approval_ref": "chaxiang-real-write-social-institution-addr-20261127",
        "approval_text_verbatim": PROD_AUTH_TEXT,
        "approval_text_sha256": PROD_AUTH_SHA,
        "authorized_tables": [{"schema_name": "cbdb",
                               "table": "cbdb__social_u5f_institution_u5f_addr"}],
        "authorized_rule_ids": ["m007906"],
    }
    s.update(over)
    return s


def test_formal_branch_accepts_a_real_verbatim_authorization():
    sc = E.production_scope_from(_real_scope(), _target(), {})
    assert sc["authorization"]["class"] == "real"
    assert sc["authorization"]["authorized_tables"] == [
        "cbdb.cbdb__social_u5f_institution_u5f_addr"]
    assert sc["candidate_sha256"] == CAND


def test_filling_only_approval_class_real_is_refused():
    """The defect this box fixes: a bare approval_class=real must not get through."""
    s = _real_scope()
    del s["real_write_authorization"]
    with pytest.raises(E.LoaderGateError) as e:
        E.production_scope_from(s, _target(), {})
    assert e.value.code == "real_authorization_text_missing"


def test_real_authorization_reference_string_without_text_is_refused():
    s = _real_scope()
    s["real_write_authorization"]["approval_text_verbatim"] = "   "
    with pytest.raises(E.LoaderGateError) as e:
        E.production_scope_from(s, _target(), {})
    assert e.value.code == "real_authorization_text_missing"


def test_real_authorization_digest_mismatch_is_refused():
    s = _real_scope()
    s["real_write_authorization"]["approval_text_sha256"] = "0" * 64
    with pytest.raises(E.LoaderGateError) as e:
        E.production_scope_from(s, _target(), {})
    assert e.value.code == "real_authorization_digest_mismatch"


def test_real_authorization_digest_must_be_bound_to_write_approval():
    s = _real_scope()
    s["write_approval"]["approval_text_sha256"] = "1" * 64
    with pytest.raises(E.LoaderGateError) as e:
        E.production_scope_from(s, _target(), {})
    assert e.value.code == "real_authorization_digest_not_bound_to_write_approval"


def test_real_authorization_ref_must_match_write_approval_ref():
    s = _real_scope()
    s["real_write_authorization"]["approval_ref"] = "another-ref"
    with pytest.raises(E.LoaderGateError) as e:
        E.production_scope_from(s, _target(), {})
    assert e.value.code == "real_authorization_ref_mismatch"


def test_relabelled_test_approval_cannot_become_real():
    s = _real_scope()
    s["real_write_authorization"]["approval_class"] = "test"
    with pytest.raises(E.LoaderGateError) as e:
        E.production_scope_from(s, _target(), {})
    assert e.value.code == "real_authorization_class_mismatch"


def test_real_authorization_marked_test_only_is_refused():
    s = _real_scope()
    s["real_write_authorization"]["test_only"] = True
    with pytest.raises(E.LoaderGateError) as e:
        E.production_scope_from(s, _target(), {})
    assert e.value.code == "real_authorization_marked_test_only"


def test_real_authorization_must_cover_exactly_one_table():
    s = _real_scope()
    s["real_write_authorization"]["authorized_tables"] = [
        {"schema_name": "cbdb", "table": "cbdb__social_u5f_institution_u5f_addr"},
        {"schema_name": "harv", "table": "harvard_u2f_tab__academy_u5f_data_u2e_tab"}]
    with pytest.raises(E.LoaderGateError) as e:
        E.production_scope_from(s, _target(), {})
    assert e.value.code == "real_authorization_scope_not_single_table"


def test_real_authorization_rule_scope_must_be_exactly_m007906():
    s = _real_scope()
    s["real_write_authorization"]["authorized_rule_ids"] = ["m007906", "m008002"]
    with pytest.raises(E.LoaderGateError) as e:
        E.production_scope_from(s, _target(), {})
    assert e.value.code == "real_authorization_rule_scope_mismatch"


def test_real_authorization_text_must_actually_name_the_table():
    """A digest over an unrelated document must not pass."""
    unrelated = "\u8336\u9999\u6279\u51c6\u5176\u4ed6\u4e8b\u9879\u3002"
    s = _real_scope()
    s["real_write_authorization"]["approval_text_verbatim"] = unrelated
    s["real_write_authorization"]["approval_text_sha256"] = _hashlib.sha256(
        unrelated.encode("utf-8")).hexdigest()
    s["write_approval"]["approval_text_sha256"] = s["real_write_authorization"]["approval_text_sha256"]
    with pytest.raises(E.LoaderGateError) as e:
        E.production_scope_from(s, _target(), {})
    assert e.value.code == "real_authorization_text_does_not_name_the_table"


def test_real_branch_refuses_an_isolated_endpoint():
    s = _real_scope()
    s["target_endpoint"]["dbname"] = "trialdb"
    with pytest.raises(E.LoaderGateError) as e:
        E.production_scope_from(s, _target(), {})
    assert e.value.code == "real_branch_endpoint_not_production"


def test_real_branch_refuses_test_only_endpoint():
    s = _real_scope()
    s["target_endpoint"]["test_only"] = True
    with pytest.raises(E.LoaderGateError) as e:
        E.production_scope_from(s, _target(), {})
    assert e.value.code == "real_branch_endpoint_marked_test_only"


def test_isolated_branch_still_requires_test_approval():
    """The isolated path must not silently accept a real approval either.

    A real approval reaching the isolated path is exactly the mirror image of the
    defect this box fixes, so the isolated branch must refuse it too.
    """
    s = _real_scope()
    with pytest.raises(E.LoaderGateError) as e:
        E.isolated_scope_from(s, _target())
    assert e.value.code == "isolated_scope_requires_test_approval"


def test_isolated_branch_accepts_a_test_approval():
    s = _scope()
    s["expected_source_member_sha256"] = "m" * 64
    s["expected_source_sha256"] = "2cb8c354b0e75e6ae230e3b00540146e823eaa8de8def2abce89ad6179a07579"
    sc = E.isolated_scope_from(s, _target())
    assert sc["approval"]["test_only"] is True


def test_formal_branch_scope_declares_production_write_not_isolated_test():
    """A formal write must not describe itself as an isolated test run."""
    sc = E.production_scope_from(_real_scope(), _target(), {})
    assert sc["mode"] == "production-write"
    assert sc["approval"]["test_only"] is False
    assert sc["approval"]["approval_class"] == "real"
    assert sc["approval"]["approval_text_sha256"] == PROD_AUTH_SHA


def test_loader_rejects_production_write_mode_marked_test_only():
    sc = E.production_scope_from(_real_scope(), _target(), {})
    sc["approval"]["test_only"] = True
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(sc, _loader_presented(sc))
    assert e.value.code == "scope_mode_production_write_but_marked_test_only"


def test_loader_rejects_production_write_mode_without_real_class():
    sc = E.production_scope_from(_real_scope(), _target(), {})
    sc["approval"]["approval_class"] = "test"
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(sc, _loader_presented(sc))
    assert e.value.code == "scope_mode_production_write_without_real_class"


def test_loader_rejects_production_write_mode_without_authorization_digest():
    sc = E.production_scope_from(_real_scope(), _target(), {})
    sc["approval"]["approval_text_sha256"] = ""
    with pytest.raises(L.LoaderGateError) as e:
        L.validate_scope(sc, _loader_presented(sc))
    assert e.value.code == "scope_mode_production_write_without_authorization_digest"

"""Formal execution-command candidate: endpoint / marker / role / one-parse gates."""
import pytest

from xiangrugu_datamgmt import cbdb_social_addr_entry as E

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

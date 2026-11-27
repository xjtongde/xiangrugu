"""Regression for the B-batch formal gate mis-rejecting legacy databases (R52).

Production `pg32b` legitimately hosts two *databases* named ``cbdb`` and
``cbdb_reh`` (AGENTS.md: retained for observation only).  The B-batch target is a
*schema* named ``cbdb`` inside the ``xiangrugu`` database.  Gate 2 built its
forbidden list from DATABASE names, so the formal branch could never pass -- it was
refused with ``production_database_visible`` before any DDL ran.

These tests pin the corrected semantics, which follow the first batch's R52 rule in
``production_entry.py``: legacy visibility is ALLOWED on the real branch, and identity
is established POSITIVELY by current database + session port + independently verified
instance marker -- not by shrinking a blacklist.  Every negative case below must still
be refused; otherwise the fix would be a weakening rather than a correction.
"""
import pytest

from xiangrugu_datamgmt import cbdb_social_addr_loader as L

# Observed facts of the real production instance, measured in the previous box.
PROD_DB_NAMES = "cbdb,cbdb_reh,postgres,template0,template1,xiangrugu"
MARKER = "3d93fc7741f66f1f01aa250b25c4959addfe4c84df22ecbd0d0f82c13920c1fc"


def _observed(**over):
    base = {
        "dbname": "xiangrugu",
        "in_session_port": "5432",
        "container_id": MARKER,
        "image_id": "sha256:d562e43664f996da0e4208b375c00c111a543d996475188d852e9189b2a8cd05",
        "server_version": "18.6 (Debian 18.6-1.pgdg12+2)",
        "inet_server_addr": "172.29.0.2/32",
        "instance_marker_verified": MARKER,
        "databases": PROD_DB_NAMES,
    }
    return dict(base, **over)


def _expected(**over):
    # An approved snapshot agrees with the observed facts except where a test says
    # otherwise; the isolated stand-in has no legacy databases at all.
    o = _observed()
    return dict(o, **over)


# ---------------------------------------------------------------- the original bug
def test_formal_branch_no_longer_refuses_legacy_databases():
    """RED before the fix: this exact payload is what production presents."""
    obs = _observed()
    exp = _expected()
    L.check_instance_identity(obs, exp, branch="real")   # must NOT raise


def test_isolated_branch_still_refuses_legacy_databases():
    """The fix must not leak into the isolated branch: a stand-in that can see
    legacy production databases is contamination, not identity."""
    obs = _observed()
    with pytest.raises(L.LoaderGateError) as e:
        L.check_instance_identity(obs, _expected(), branch="test")
    assert e.value.code == "production_database_visible"


def test_existing_isolated_refusal_still_holds():
    """Keeps the pre-existing guard intact (stand-in must not even see xiangrugu)."""
    obs = {"container_id": "x", "image_id": "y", "server_version": "z",
           "inet_server_addr": "unix-socket", "databases": "postgres,cbdb"}
    with pytest.raises(L.LoaderGateError) as e:
        L.check_instance_identity(obs, dict(obs))
    assert e.value.code == "production_database_visible"


# -------------------------------------------------- positive binding must stay strict
@pytest.mark.parametrize("field,value,code", [
    ("dbname", "cbdb", "target_database_mismatch"),
    ("dbname", "postgres", "target_database_mismatch"),
    ("in_session_port", "5433", "in_session_port_mismatch"),
    ("instance_marker_verified", "deadbeef" * 8, "instance_marker_mismatch"),
    ("container_id", "ffff" * 16, "instance_identity_mismatch"),
    ("image_id", "sha256:" + "0" * 64, "instance_identity_mismatch"),
    ("server_version", "17.9 (Debian 17.9-1.pgdg12+2)", "instance_identity_mismatch"),
    ("inet_server_addr", "10.0.0.9/32", "instance_identity_mismatch"),
])
def test_formal_branch_still_refuses_wrong_binding(field, value, code):
    """Wrong database, wrong port, wrong marker -- each alone must still refuse.

    Proving only that the correct combination passes would not distinguish a real
    binding from a removed check.
    """
    obs = _observed(**{field: value})
    exp = _expected()          # expected keeps the APPROVED values
    with pytest.raises(L.LoaderGateError) as e:
        L.check_instance_identity(obs, exp, branch="real")
    assert e.value.code == code


def test_formal_branch_refuses_unverified_marker_even_with_right_databases():
    """Marker is the out-of-band container identity; it cannot be inferred away."""
    obs = _observed(instance_marker_verified=None)
    with pytest.raises(L.LoaderGateError) as e:
        L.check_instance_identity(obs, _expected(), branch="real")
    assert e.value.code == "instance_marker_mismatch"


def test_formal_branch_refuses_extra_unknown_database():
    """Legacy allowance is an explicit name set, not 'any database is fine'.
    A database nobody approved must still break the exact-set comparison."""
    obs = _observed(databases=PROD_DB_NAMES + ",surprise_db")
    with pytest.raises(L.LoaderGateError) as e:
        L.check_instance_identity(obs, _expected(), branch="real")
    assert e.value.code == "instance_identity_mismatch"


def test_legacy_allow_list_matches_first_batch_r52_constant():
    """Same constant as production_entry, so the two entries cannot drift apart."""
    from xiangrugu_datamgmt import production_entry as PE
    assert tuple(L.LEGACY_DATABASES) == tuple(PE.LEGACY_DATABASES)


def test_target_absent_gate_unchanged():
    """Anti-overwrite must survive this change: an existing target still refuses."""
    class S:
        def query_csv(self, sql):
            return "t"      # to_regclass(...) IS NOT NULL -> table exists
    with pytest.raises(L.LoaderGateError) as e:
        L.check_target_absent(S())
    assert e.value.code == "target_already_exists"

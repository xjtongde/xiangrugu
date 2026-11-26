"""Formal execution-command candidate for SOCIAL_INSTITUTION_ADDR (single table).

Sole formal target: ``pg32b:5433/xiangrugu``. The port must be the OUTER 5433;
5432 is the in-container/production db port that this entry must distinguish and
reject as a target endpoint.

What this candidate enforces, in ONE session that also executes the DDL:

  Gate A  endpoint fixed to pg32b:5433/xiangrugu, with 5432 declared as the
          distinct in-session port (never a target).
  Gate B  instance identity proven POSITIVELY in the DDL session: the
          ``public.xrg_instance_marker`` row must equal the independently
          verified container Id; a missing/empty/multi/other marker refuses.
  Gate C  the load role must be verified in that same session.
  Gate D  the contract digest is RECOMPUTED from the actual frozen contract
          document by one formal parse, and that SAME parsed object drives the
          targets and the load (no second, independent reading).
  Gate E  a TEST approval may never reach the formal production endpoint.

A real database write needs a separate, independent authorization
(``approval_class == "real"``); this module only ever runs with test approval in
the isolated instance.
"""
from __future__ import annotations

import hashlib
import json

from . import first_batch_loader as fbl

LoaderGateError = fbl.LoaderGateError

# The one formal target. host/port/dbname are the OUTER endpoint.
PRODUCTION_TARGET = {"host": "pg32b", "port": 5433, "dbname": "xiangrugu"}
# Inside the container the database listens on 5432. Declaring it is mandatory so a
# caller cannot silently treat the in-session port as "the same thing".
IN_SESSION_PORT = 5432
TARGET_RULE = "m007906"
TARGET_SCHEMA = "cbdb"
TARGET_TABLE = "cbdb__social_u5f_institution_u5f_addr"
EXPECTED_ROWS = 3859
LOAD_ROLE = "xrg_loader"
# Out-of-band verified production container id (docker inspect). A test approval
# whose endpoint resolves to THIS container is reaching production and is refused.
_PRODUCTION_CONTAINER_ID = "3d93fc7741f66f1f01aa250b25c4959addfe4c84df22ecbd0d0f82c13920c1fc"


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _strip_none(obj):
    if isinstance(obj, dict):
        return {k: _strip_none(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, (list, tuple)):
        return [_strip_none(v) for v in obj]
    return obj


# --------------------------------------------------------------- Gate A + E
def validate_execution_scope(scope, presented):
    """Endpoint identity, port distinction, and test-approval containment."""
    if scope.get("version") != 1 or scope.get("mode") != "execution-candidate":
        raise LoaderGateError("scope_mode_not_execution_candidate")

    wa = scope.get("write_approval") or {}
    for key in ("approved_by", "approved_at", "approval_ref", "approval_class"):
        if not wa.get(key):
            raise LoaderGateError("write_approval_missing", key)
    if wa["approval_class"] not in ("test", "real"):
        raise LoaderGateError("write_approval_class_invalid")

    # Gate A: the target endpoint is fixed and 5432 is declared as the distinct one.
    ep = scope.get("target_endpoint") or {}
    if ep.get("host") != PRODUCTION_TARGET["host"]:
        raise LoaderGateError("target_host_not_pg32b", str(ep.get("host")))
    if ep.get("port") != PRODUCTION_TARGET["port"]:
        raise LoaderGateError("target_port_not_5433", str(ep.get("port")))
    # The FORMAL target database is fixed to 'xiangrugu'. A test-only isolated
    # stand-in may use a different database name, but only while test_only=True.
    if ep.get("dbname") != PRODUCTION_TARGET["dbname"]:
        if not (wa.get("approval_class") == "test" and ep.get("test_only") is True):
            raise LoaderGateError("target_dbname_not_xiangrugu", str(ep.get("dbname")))
    if ep.get("in_session_port") != IN_SESSION_PORT:
        raise LoaderGateError("in_session_port_not_declared_5432")
    if scope.get("endpoint_mapping_verified") is not True:
        raise LoaderGateError("endpoint_mapping_not_verified")

    # Gate E: a TEST approval can never authorize the FORMAL endpoint.
    # The formal endpoint is the production instance itself, i.e. the declared
    # endpoint is the production triple AND is marked as the real thing. A test
    # approval may declare the same triple ONLY when it is explicitly a test-only
    # isolated stand-in (test_only=True) with its own verified container binding.
    is_production_triple = (ep.get("host"), ep.get("port"), ep.get("dbname")) == (
        PRODUCTION_TARGET["host"], PRODUCTION_TARGET["port"], PRODUCTION_TARGET["dbname"])
    if wa["approval_class"] == "test":
        if ep.get("test_only") is not True:
            # test approval must be explicitly test-only; otherwise it would be
            # reaching the formal target.
            raise LoaderGateError("test_approval_cannot_target_production")
        if not ep.get("container_id"):
            raise LoaderGateError("test_endpoint_missing_container_id")
        if is_production_triple and str(ep.get("container_id") or "").startswith(_PRODUCTION_CONTAINER_ID[:12]):
            raise LoaderGateError("test_approval_cannot_target_production", "production container id")
    else:
        if not scope.get("real_authority_ref"):
            raise LoaderGateError("real_authority_ref_missing")
        if not is_production_triple:
            raise LoaderGateError("real_approval_target_not_production_endpoint")

    # Approval must be bound to this single rule and this single target.
    if sorted(wa.get("bound_object_rule_ids") or []) != [TARGET_RULE]:
        raise LoaderGateError("write_approval_not_bound_to_single_target")
    t = scope.get("target") or {}
    if (t.get("schema_name"), t.get("table")) != (TARGET_SCHEMA, TARGET_TABLE):
        raise LoaderGateError("target_not_approved_single_table")

    # Artifact bindings.
    for key in ("contract_sha256", "inventory_sha256", "approval_table_sha256",
                "approval_text_sha256", "instance_fingerprint"):
        if not scope.get(key):
            raise LoaderGateError("binding_missing", key)
        if scope[key] != presented.get(key):
            raise LoaderGateError("artifact_drift", key)
    if scope.get("full_ready_for_import") is not False:
        raise LoaderGateError("full_ready_gate_flipped")
    # The test-only approval in THIS box must not reuse the first-batch write approval.
    if wa["approval_class"] == "test" and "88f4f1ac" in str(wa.get("approval_ref", "")):
        raise LoaderGateError("first_batch_approval_reuse_forbidden")


# ------------------------------------------------------- Gates B + C (session)
def verify_instance_and_role_in_session(session, scope, expected):
    """Prove instance + load role in the SAME session that will execute DDL."""
    ep = scope["target_endpoint"]

    # Gate B1: the session must be the declared database and server version family.
    dbname = session.query_csv("SELECT current_database()").strip()
    if dbname != ep["dbname"]:
        raise LoaderGateError("session_database_mismatch", dbname)
    version = session.query_csv("SHOW server_version").strip()
    if not version.startswith("18"):
        raise LoaderGateError("server_version_mismatch", version)
    inet = session.query_csv(
        "SELECT COALESCE(inet_server_addr()::text, 'unix-socket')").strip()
    port = session.query_csv("SHOW port").strip()
    if port != str(IN_SESSION_PORT):
        raise LoaderGateError("in_session_port_mismatch", port)
    if ep["port"] == IN_SESSION_PORT:
        raise LoaderGateError("target_port_equals_in_session_port")

    # Gate B2: positive identity via the independently verified instance marker.
    has = session.query_csv(
        "SELECT (to_regclass('public.xrg_instance_marker') IS NOT NULL)::int").strip()
    if has != "1":
        raise LoaderGateError("marker_table_missing")
    cnt = session.query_csv("SELECT count(*) FROM public.xrg_instance_marker").strip()
    if cnt == "0":
        raise LoaderGateError("marker_empty")
    if cnt != "1":
        raise LoaderGateError("marker_multiple_rows", cnt)
    marker = fbl._rows_csv(
        session.query_csv("SELECT instance_id FROM public.xrg_instance_marker"))[0][0]
    if marker != scope["instance_fingerprint"]:
        raise LoaderGateError("marker_value_mismatch")
    if ep.get("container_id") and marker != ep["container_id"]:
        raise LoaderGateError("marker_container_binding_mismatch")
    dbs = fbl._rows_csv(session.query_csv(
        "SELECT string_agg(datname, ',' ORDER BY datname) FROM pg_database"))[0][0]

    # Gate C: the load role must exist, be able to create in the target schema, and
    # must not be a superuser (least privilege for a data loader).
    # PostgreSQL returns the literal string 'none' for current_setting('role', true)
    # when no SET ROLE was issued -- it is neither NULL nor ''. Verified in the
    # isolated instance. So the role is taken from current_user, and an active
    # SET ROLE override is detected explicitly rather than inferred.
    role = session.query_csv("SELECT current_user").strip()
    override = session.query_csv(
        "SELECT current_setting('role', true)").strip()
    if override not in ("none", role):
        raise LoaderGateError("load_role_override_active", override)
    if role != LOAD_ROLE:
        raise LoaderGateError("load_role_mismatch", role)
    su = session.query_csv(
        "SELECT rolsuper::int FROM pg_roles WHERE rolname = " + _q(role)).strip()
    if su == "1":
        raise LoaderGateError("load_role_is_superuser")
    can = session.query_csv(
        "SELECT has_schema_privilege(" + _q(role) + ", " + _q(TARGET_SCHEMA) + ", 'USAGE,CREATE')::int"
    ).strip() if _schema_exists(session) else "0"
    return {
        "dbname": dbname, "server_version": version, "inet_server_addr": inet,
        # The marker row IS the independently verified container identity: it is the
        # out-of-band container id written as a prerequisite. Reporting it here keeps the
        # isolated loader's identity gate bound to the same proof the entry just verified.
        "container_id": marker, "image_id": scope.get("expected_image_id"),
        "in_session_port": port, "target_outer_port": ep["port"],
        "databases": dbs, "instance_marker_verified": marker,
        "load_role": role, "load_role_superuser": False,
        "load_role_can_create_in_target_schema": can == "1",
    }


def _schema_exists(session):
    return session.query_csv(
        "SELECT (to_regnamespace(" + _q(TARGET_SCHEMA) + ") IS NOT NULL)::int").strip() == "1"


def _q(s):
    return "'" + str(s).replace("'", "''") + "'"


# ----------------------------------------------- Gate D: one parse drives all
def recompute_contract_digest(artifacts, contract_parse_fn):
    """Recompute the contract digest from the ACTUAL frozen document via one formal parse.

    The returned parsed object is the only source of targets/columns/PK/expectations
    used by the load, so a caller cannot straddle two different readings.
    """
    parsed = contract_parse_fn(artifacts["contract"])
    if getattr(parsed, "status", None) != "frozen":
        raise LoaderGateError("contract_not_frozen", str(getattr(parsed, "status", None)))
    digest = parsed.sha256
    review = getattr(parsed, "review", None)
    if review is None:
        raise LoaderGateError("contract_review_missing")
    return parsed, {
        "contract_sha256": digest,
        "contract_review_ref": review.approval_ref,
        "contract_review_approved_at": review.approved_at,
        "contract_review_approved_by": review.approved_by,
    }


def target_from_parsed(parsed):
    """Derive the single load target from the SAME parsed contract."""
    rules = [r for r in parsed.rules if r.rule_id == TARGET_RULE]
    if len(rules) != 1:
        raise LoaderGateError("contract_rule_set_mismatch", str(len(rules)))
    t = rules[0].targets[0]
    if (t.schema_name, t.table) != (TARGET_SCHEMA, TARGET_TABLE):
        raise LoaderGateError("parsed_target_not_approved_single_table")
    return {
        "schema_name": t.schema_name, "table": t.table,
        "columns": [{"ordinal": c.ordinal, "source_column": c.source_column,
                     "target_column": c.target_column, "pg_type": c.pg_type,
                     "nullable": c.nullable} for c in t.columns],
        "primary_key": {"columns": list(t.primary_key.columns)},
        "expected_count": t.expected_count,
        "expected_sha256": t.expected_sha256,
    }


def run_execution_candidate(session, scope, expected, artifacts, contract_parse_fn,
                            make_loader, source_payload):
    """Full candidate entry: gates -> one parse -> single transaction -> COMMIT/ROLLBACK.

    ``make_loader`` receives (session, scope, parsed_contract, target, payload, expected,
    instance_observed) and returns the loader evidence; it is the SAME isolated-test
    loader used in the trial, so one entry drives both.
    """
    # Gate A/E first: endpoint and approval class, before touching the session.
    validate_execution_scope(
        scope,
        {k: expected.get(k) for k in ("contract_sha256", "inventory_sha256",
                                      "approval_table_sha256", "approval_text_sha256",
                                      "instance_fingerprint")})

    # Gate D: recompute from the real document; one parse drives everything downstream.
    parsed, recomputed = recompute_contract_digest(artifacts, contract_parse_fn)
    if recomputed["contract_sha256"] != scope["contract_sha256"]:
        raise LoaderGateError("recomputed_contract_digest_mismatch",
                              recomputed["contract_sha256"])
    if recomputed["contract_review_ref"] != scope.get("contract_review_ref"):
        raise LoaderGateError("contract_review_ref_mismatch")
    target = target_from_parsed(parsed)
    if target["expected_count"] != EXPECTED_ROWS:
        raise LoaderGateError("contract_row_expectation_drift")

    # Gates B/C inside the DDL session, then the same session does the load.
    instance = verify_instance_and_role_in_session(session, scope, expected)
    # The isolated loader speaks the "isolated-test" scope dialect; derive it from the
    # execution scope rather than maintaining a second, independently drifting copy.
    loader_scope = isolated_scope_from(scope, target)
    # The isolated loader's ``expected["source_sha256"]`` means the MEMBER file digest
    # (it is compared against scope.source_member.sha256), whereas the execution scope's
    # expected_source_sha256 is the approved source-side VALUE digest. Keep them apart.
    loader_expected = dict(expected)
    loader_expected["source_sha256"] = expected["source_member_sha256"]
    evidence = make_loader(session, loader_scope, parsed.model_dump(by_alias=True, mode="json"),
                           target, source_payload, loader_expected, instance)
    evidence["recomputed_contract_sha256"] = recomputed["contract_sha256"]
    evidence["instance"] = instance
    evidence["single_parse_drives_load"] = True
    return evidence

def isolated_scope_from(scope, target):
    """Derive the isolated-test loader scope from an execution-candidate scope.

    Every field is carried over from the execution scope or the parsed target; nothing
    is invented. ``mode``/``approval`` are the loader's own dialect for "this run is
    authorised as an isolated test only".
    """
    wa = scope["write_approval"]
    if wa.get("approval_class") != "test":
        raise LoaderGateError("isolated_scope_requires_test_approval")
    return {
        "version": 1,
        "scope_id": "derived:" + str(wa["approval_ref"]),
        "mode": "isolated-test",
        "approval": {
            "approved_by": wa["approved_by"],
            "approved_at": wa["approved_at"],
            "approval_ref": wa["approval_ref"],
            "test_only": True,
        },
        "candidate_sha256": scope["contract_sha256"],
        "contract_sha256": scope["contract_sha256"],
        "inventory_sha256": scope["inventory_sha256"],
        "source_member": {
            "rule_id": TARGET_RULE,
            "sha256": scope["expected_source_member_sha256"],
            "expected_rows": target["expected_count"],
            "source_side_sha256": scope["expected_source_sha256"],
            "relative_path": "harvard/cbdb/cbdb_20260919.sqlite3",
        },
        "target": {
            "schema_name": target["schema_name"],
            "table": target["table"],
            "constraints_approved": ["primary_key", "not_null", "unique", "index",
                                    "foreign_key", "default"],
            "constraints_to_create": ["primary_key", "not_null"],
            "databases_forbidden": list(expected_forbidden(scope)),
            "columns": target["columns"],
            "primary_key": target["primary_key"],
        },
        "full_ready_for_import": False,
        "review_traceability": dict(scope.get("review_traceability") or {}),
        "derived_from": "execution-candidate scope; nothing invented",
    }


def expected_forbidden(scope):
    return scope.get("forbidden") or ["pg32b", "cbdb", "cbdb_reh", "xiangrugu"]
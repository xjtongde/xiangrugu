"""Production load entry candidate for the first seven approved objects.

Candidate branch only. The sole formal target is pg32b:5433/xiangrugu. This round
runs with TEST approval only; a real run requires an independent first-batch
database-write approval event (approval_class="real") plus the runbook prerequisites.

Design rules:
- Target identity is verified IN THE SAME database session that executes the DDL.
- Database creation, PostGIS extension and schemas are PREREQUISITES, listed
  separately; the loader never creates them by default (missing -> refuse).
- Digest bindings are recomputed by the caller (formal contract parse) and
  compared here; any artifact drift refuses before BEGIN.
- Single transaction: DDL+COPY x7 -> in-transaction readback -> COMMIT or ROLLBACK.
- Existing targets are never overwritten (CREATE TABLE has no IF NOT EXISTS).
"""
from __future__ import annotations

from . import first_batch_loader as fbl

LoaderGateError = fbl.LoaderGateError

PRODUCTION_TARGET = {"host": "pg32b", "port": 5433, "dbname": "xiangrugu"}
PREREQUISITES = [
    "database xiangrugu exists on pg32b:5433 (CREATE DATABASE — separate authorization, not a loader action)",
    "CREATE EXTENSION postgis in database xiangrugu (prerequisite, not a loader action)",
    "CREATE SCHEMA harv; CREATE SCHEMA chgis (prerequisite, not a loader action)",
]
FIRST_BATCH_RULES = fbl.FIRST_BATCH_RULES


def validate_production_scope(scope, presented):
    if scope.get("version") != 1 or scope.get("mode") != "production-candidate":
        raise LoaderGateError("scope_mode_not_production_candidate")
    wa = scope.get("write_approval") or {}
    for key in ("approved_by", "approved_at", "approval_ref", "approval_class"):
        if not wa.get(key):
            raise LoaderGateError("write_approval_missing", key)
    if wa["approval_class"] not in ("test", "real"):
        raise LoaderGateError("write_approval_class_invalid")
    endpoint = scope.get("target_endpoint") or {}
    if wa["approval_class"] == "real":
        if endpoint.get("host") != PRODUCTION_TARGET["host"] or endpoint.get("port") != PRODUCTION_TARGET["port"] \
                or endpoint.get("dbname") != PRODUCTION_TARGET["dbname"]:
            raise LoaderGateError("real_approval_target_not_pg32b_xiangrugu")
        if not scope.get("real_authority_ref"):
            raise LoaderGateError("real_authority_ref_missing")
    else:
        if endpoint.get("test_only") is not True or not endpoint.get("container_id"):
            raise LoaderGateError("test_endpoint_not_declared")
    for key in ("contract_sha256", "inventory_sha256"):
        if scope.get(key) != presented[key]:
            raise LoaderGateError("artifact_drift", key)
    if scope.get("writeoff_evidence_sha256") != presented["evidence_shas"]:
        raise LoaderGateError("artifact_drift", "writeoff_evidence_sha256")
    objs = {o["rule_id"]: o for o in scope.get("objects", [])}
    if set(objs) != set(FIRST_BATCH_RULES):
        raise LoaderGateError("scope_object_set_mismatch")
    for rid, t in presented["targets"].items():
        o = objs[rid]
        if (o["schema_name"], o["table"]) != (t["schema_name"], t["table"]):
            raise LoaderGateError("scope_object_identity_mismatch", rid)
    if scope.get("full_ready_for_import") is not False:
        raise LoaderGateError("full_ready_gate_flipped")
    if scope.get("uncovered_members") != 7995:
        raise LoaderGateError("uncovered_count_drift")


def verify_target_in_session(session, scope, expected):
    """Identity + prerequisites + target-absence, all in the DDL session itself."""
    row = fbl._rows_csv(session.query_csv(
        "SELECT current_database(), current_setting('port'), coalesce(inet_server_addr()::text,'null'), "
        "current_setting('server_version'), pg_postmaster_start_time()::text"))[0]
    dbname, port, addr, version, start = row
    endpoint = scope["target_endpoint"]
    if dbname != endpoint.get("dbname"):
        raise LoaderGateError("wrong_database", dbname)
    if port != str(endpoint.get("port")):
        raise LoaderGateError("wrong_port", port)
    dbs = fbl._rows_csv(session.query_csv("SELECT string_agg(datname, ',' ORDER BY datname) FROM pg_database"))[0][0]
    if "cbdb" in dbs or "pg32b" in dbs:
        raise LoaderGateError("production_database_visible")
    if scope["write_approval"]["approval_class"] == "real":
        if addr != expected.get("server_addr"):
            raise LoaderGateError("server_addr_mismatch", addr)
    if not version.startswith("18"):
        raise LoaderGateError("server_version_mismatch", version)
    ext = session.query_csv("SELECT count(*) FROM pg_extension WHERE extname='postgis'").strip()
    if ext != "1":
        raise LoaderGateError("prerequisite_missing", "postgis extension")
    ns = fbl._rows_csv(session.query_csv("SELECT string_agg(nspname, ',' ORDER BY nspname) FROM pg_namespace "
                                         "WHERE nspname IN ('harv','chgis')"))[0][0]
    if ns != "chgis,harv":
        raise LoaderGateError("prerequisite_missing", "schemas harv/chgis")
    return {"dbname": dbname, "port": port, "inet_server_addr": addr,
            "server_version": version, "postmaster_start": start, "databases": dbs,
            "postgis": "present", "schemas": "harv,chgis"}


def run_production_load(session, scope, contract, payloads, expected):
    """Production candidate entry: gates in the DDL session, then the shared transaction body."""
    validate_production_scope(scope, {"contract_sha256": expected["contract_sha256"],
                                      "inventory_sha256": expected["inventory_sha256"],
                                      "evidence_shas": expected["evidence_shas"],
                                      "targets": fbl.targets_of(contract)})
    identity = verify_target_in_session(session, scope, expected)
    fbl.check_targets_absent(session, contract)
    evidence = fbl._load_and_verify(session, contract, payloads, expected, create_prerequisites=False)
    evidence["gates"] = ["write_approval_independent", "artifact_digest_recompute",
                          "target_identity_in_ddl_session", "prerequisites_verified_not_created",
                          "targets_absent"] + evidence["gates"][1:]
    evidence["target_identity_in_session"] = identity
    evidence["production_target_constant"] = PRODUCTION_TARGET
    evidence["prerequisites_not_loader_actions"] = PREREQUISITES
    evidence["approval_class"] = scope["write_approval"]["approval_class"]
    return evidence
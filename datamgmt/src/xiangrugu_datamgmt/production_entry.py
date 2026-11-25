"""Production load entry candidate for the first seven approved objects (R52 corrected).

Candidate branch only. The sole formal target is pg32b:5433/xiangrugu. This round
runs with TEST approval only; a real run requires an independent first-batch
database-write approval event (approval_class="real") plus the runbook prerequisites.

R52 corrections:
- Positive instance identity: legacy databases cbdb/cbdb_reh MAY be visible (they
  exist on the real pg32b); the correct target still passes. Identity is proven
  POSITIVELY in the DDL session via an independently verified instance marker
  (prerequisite xrg_instance_marker, value = out-of-band verified container Id)
  compared to the scope-bound fingerprint. Wrong instance/database, or identity
  that cannot be proven, refuses BEFORE any write.
- Digests are RECOMPUTED inside the entry from the actual artifact documents
  (frozen contract via injected formal parse, original inventory canonical,
  two writeoff evidences compact canonical) and compared to the approved anchors.
  Artifacts changed while the caller's two summaries still agree with each other
  is refused (recomputed mismatch).
- The write approval must bind the seven target rule ids; a test approval can
  never authorize a write against the formal production endpoint.

Design rules kept: identity/prerequisites/target-absence verified in the SAME
session that executes DDL; database/PostGIS/schemas/marker are prerequisites,
never created by the loader; single transaction DDL+COPY x7 -> in-transaction
readback -> COMMIT or ROLLBACK; existing targets never overwritten.
"""
from __future__ import annotations

import hashlib
import json

from . import first_batch_loader as fbl
from .inventory import ChecksumAssertion, InventoryEntry, InventoryIssue, InventoryManifest

LoaderGateError = fbl.LoaderGateError

PRODUCTION_TARGET = {"host": "pg32b", "port": 5433, "dbname": "xiangrugu"}
PREREQUISITES = [
    "database xiangrugu exists on pg32b:5433 (CREATE DATABASE — separate authorization, not a loader action)",
    "CREATE EXTENSION postgis in database xiangrugu (prerequisite, not a loader action)",
    "CREATE SCHEMA harv; CREATE SCHEMA chgis (prerequisite, not a loader action)",
    "public.xrg_instance_marker(instance_id text) populated with the independently verified instance Id "
    "(docker inspect out-of-band; prerequisite, not a loader action)",
]
FIRST_BATCH_RULES = fbl.FIRST_BATCH_RULES
LEGACY_DATABASES = ("cbdb", "cbdb_reh")


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _evidence_sha(evidence):
    return _sha(json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _inventory_sha(doc):
    entries = tuple(InventoryEntry(
        relative_path=e["relative_path"], archive_chain=tuple(e.get("archive_chain", ())),
        archive_ordinals=tuple(e.get("archive_ordinals", ())), kind=e.get("kind", "file"),
        size=e.get("size"), sha256=e.get("sha256"), signature=e.get("signature", "unknown"))
        for e in doc["entries"])
    issues = tuple(InventoryIssue(
        code=i["code"], relative_path=i["relative_path"],
        archive_chain=tuple(i.get("archive_chain", ())), archive_ordinals=tuple(i.get("archive_ordinals", ())),
        detail=i.get("detail", ""), blocking=i.get("blocking", True)) for i in doc["issues"])
    checksums = tuple(ChecksumAssertion(
        ledger=c["ledger"], line=c["line"], raw_name=c["raw_name"], target=c["target"],
        expected_sha256=c["expected_sha256"], matched=c["matched"],
        archive_chain=tuple(c.get("archive_chain", ())), archive_ordinals=tuple(c.get("archive_ordinals", ())))
        for c in doc["checksums"])
    limits = tuple(sorted((k, int(v)) for k, v in doc["limits"]))
    return InventoryManifest(entries=entries, issues=issues, checksums=checksums, limits=limits).sha256


def recompute_artifact_digests(artifacts, contract_digest_fn):
    return {"contract_sha256": contract_digest_fn(artifacts["contract"]),
            "inventory_sha256": _inventory_sha(artifacts["inventory"]),
            "evidence_shas": {k: _evidence_sha(v) for k, v in artifacts["evidence"].items()}}


def validate_production_scope(scope, presented):
    if scope.get("version") != 1 or scope.get("mode") != "production-candidate":
        raise LoaderGateError("scope_mode_not_production_candidate")
    wa = scope.get("write_approval") or {}
    for key in ("approved_by", "approved_at", "approval_ref", "approval_class"):
        if not wa.get(key):
            raise LoaderGateError("write_approval_missing", key)
    if wa["approval_class"] not in ("test", "real"):
        raise LoaderGateError("write_approval_class_invalid")
    if sorted(wa.get("bound_object_rule_ids", [])) != sorted(FIRST_BATCH_RULES):
        raise LoaderGateError("write_approval_not_bound_to_seven_targets")
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
        if (endpoint.get("host"), endpoint.get("port"), endpoint.get("dbname")) == \
                (PRODUCTION_TARGET["host"], PRODUCTION_TARGET["port"], PRODUCTION_TARGET["dbname"]):
            raise LoaderGateError("test_approval_cannot_target_production")
    if not scope.get("instance_fingerprint"):
        raise LoaderGateError("instance_fingerprint_missing")
    if scope["instance_fingerprint"] != presented.get("instance_fingerprint"):
        raise LoaderGateError("instance_fingerprint_drift")
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
    """Dbname/port + POSITIVE instance identity + prerequisites, in the DDL session."""
    row = fbl._rows_csv(session.query_csv(
        "SELECT current_database(), current_setting('port'), coalesce(inet_server_addr()::text,'null'), "
        "current_setting('server_version'), pg_postmaster_start_time()::text"))[0]
    dbname, port, addr, version, start = row
    endpoint = scope["target_endpoint"]
    if dbname != endpoint.get("dbname"):
        raise LoaderGateError("wrong_database", dbname)
    if port != str(endpoint.get("port")):
        raise LoaderGateError("wrong_port", port)
    if not version.startswith("18"):
        raise LoaderGateError("server_version_mismatch", version)
    # Positive identity: legacy cbdb/cbdb_reh visibility is allowed; the marker proves the instance.
    marker = fbl._rows_csv(session.query_csv(
        "SELECT CASE WHEN to_regclass('public.xrg_instance_marker') IS NULL THEN '' "
        "ELSE coalesce((SELECT instance_id FROM public.xrg_instance_marker LIMIT 1),'') END"))[0][0]
    if not marker or marker != scope["instance_fingerprint"]:
        raise LoaderGateError("identity_unproven", "instance marker missing or mismatched")
    dbs = fbl._rows_csv(session.query_csv("SELECT string_agg(datname, ',' ORDER BY datname) FROM pg_database"))[0][0]
    if scope["write_approval"]["approval_class"] == "real":
        if addr != expected.get("server_addr"):
            raise LoaderGateError("server_addr_mismatch", addr)
    ext = session.query_csv("SELECT count(*) FROM pg_extension WHERE extname='postgis'").strip()
    if ext != "1":
        raise LoaderGateError("prerequisite_missing", "postgis extension")
    ns = fbl._rows_csv(session.query_csv("SELECT string_agg(nspname, ',' ORDER BY nspname) FROM pg_namespace "
                                         "WHERE nspname IN ('harv','chgis')"))[0][0]
    if ns != "chgis,harv":
        raise LoaderGateError("prerequisite_missing", "schemas harv/chgis")
    return {"dbname": dbname, "port": port, "inet_server_addr": addr,
            "server_version": version, "postmaster_start": start, "databases": dbs,
            "instance_marker_verified": marker,
            "legacy_databases_visible": [d for d in LEGACY_DATABASES if d in dbs.split(",")],
            "postgis": "present", "schemas": "harv,chgis"}


def run_production_load(session, scope, contract, payloads, expected, artifacts, contract_digest_fn):
    """Production candidate entry: recompute -> gates in the DDL session -> shared transaction."""
    recomputed = recompute_artifact_digests(artifacts, contract_digest_fn)
    for key in ("contract_sha256", "inventory_sha256"):
        if recomputed[key] != scope.get(key) or recomputed[key] != expected.get(key):
            raise LoaderGateError("artifact_drift_recomputed", key)
    for k, v in recomputed["evidence_shas"].items():
        if v != scope.get("writeoff_evidence_sha256", {}).get(k) or v != expected.get("evidence_shas", {}).get(k):
            raise LoaderGateError("artifact_drift_recomputed", "evidence:" + k)
    validate_production_scope(scope, {"contract_sha256": expected["contract_sha256"],
                                      "inventory_sha256": expected["inventory_sha256"],
                                      "evidence_shas": expected["evidence_shas"],
                                      "instance_fingerprint": expected["instance_fingerprint"],
                                      "targets": fbl.targets_of(contract)})
    identity = verify_target_in_session(session, scope, expected)
    fbl.check_targets_absent(session, contract)
    evidence = fbl._load_and_verify(session, contract, payloads, expected, create_prerequisites=False)
    evidence["gates"] = ["artifact_digest_recomputed_in_entry", "write_approval_independent_bound_seven",
                          "target_identity_positive_in_ddl_session", "prerequisites_verified_not_created",
                          "targets_absent"] + evidence["gates"][1:]
    evidence["target_identity_in_session"] = identity
    evidence["recomputed_digests"] = recomputed
    evidence["production_target_constant"] = PRODUCTION_TARGET
    evidence["prerequisites_not_loader_actions"] = PREREQUISITES
    evidence["approval_class"] = scope["write_approval"]["approval_class"]
    return evidence
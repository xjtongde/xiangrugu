"""Isolated-instance trial driver for the formal execution-command candidate.

Runs INSIDE the isolated container (python3 + psql available). One entry
(cbdb_social_addr_entry.run_execution_candidate) drives every case, so a
positive trial and the negative cases exercise the SAME code path as a real run
would -- only the approval class and endpoint binding differ.

Cases:
  P1  positive: full load, 3859 rows, 11 cols, ordered 6-col PK, NULLs,
      coordinates, full-value digest, then COMMIT.
  N1  target already exists -> refuse, existing table untouched.
  N2  row-count mismatch -> whole-table ROLLBACK, zero residue.
  N3  structure mismatch -> whole-table ROLLBACK, zero residue.
  N4  coordinate roundtrip inexact -> whole-table ROLLBACK, zero residue.
  N5  review traceability incomplete -> refuse before any write.
  N6  test approval bound to the PRODUCTION container -> refuse (never connects).
  N7  target port declared as 5432 (in-session port) -> refuse.
  P2  clean retry after all negative cases -> COMMITTED 3859.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, "/tmp/ut/src")

from xiangrugu_datamgmt import cbdb_social_addr_entry as ENTRY  # noqa: E402
from xiangrugu_datamgmt import cbdb_social_addr_loader as L  # noqa: E402


def sha(b):
    return hashlib.sha256(b).hexdigest()


def read_json(p):
    with open(p, "rb") as f:
        return json.loads(f.read())


def _sess(cfg):
    """One psql coprocess bound to the isolated trial instance.

    The load role authenticates over the container loopback (scram), which keeps
    the session honest about which role is actually connected -- a peer-auth
    superuser session would silently mask a role-binding defect.
    """
    env = dict(os.environ)
    env["PGPASSWORD"] = cfg["password"]
    return L.PsqlSession(["psql", "-h", "127.0.0.1", "-p", str(cfg["port"]),
                          "-U", cfg["role"], "-d", cfg["dbname"]], env=env)


def main():
    cfg = read_json("/tmp/ut/trial-config.json")
    scope = cfg["scope"]
    expected = cfg["expected"]
    artifacts = {"contract": read_json(cfg["contract_path"])}
    out = {"format": "xrg.cbdb.addr.entry-trial.v1", "cases": []}
    # The COPY payload is the actual bytes, read once and reused by every case.
    with open(cfg["source_payload"], "rb") as f:
        payload_bytes = f.read()
    out["payload_bytes"] = len(payload_bytes)

    from xiangrugu_datamgmt.contracts import ReleaseContract

    def parse(doc):
        return ReleaseContract.model_validate(doc)

    # ---- How the loader is invoked: the SAME isolated loader used in the trial.
    def make_loader(session, sc, parsed_doc, target, payload, exp, instance):
        corrupt = os.environ.get("XFAIL", "") or None
        return L.run_single_table(
            session, sc, parsed_doc, target, payload, instance, exp, corrupt=corrupt)

    # ------------------------------------------------------------ network check
    out["isolated"] = {
        "hostname": os.uname().nodename,
        "net_none": not os.path.exists("/sys/class/net/eth0"),
        "pg_port": scope["target_endpoint"]["in_session_port"],
        "outer_port_declared": scope["target_endpoint"]["port"],
        "production_container_bound": scope["target_endpoint"]["container_id"],
    }

    def run_case(name, mutate_scope=None, mutate_expected=None, xfail="", expect=None):
        sc = json.loads(json.dumps(scope))
        ex = json.loads(json.dumps(expected))
        if mutate_scope:
            mutate_scope(sc)
        if mutate_expected:
            mutate_expected(ex)
        os.environ["XFAIL"] = xfail
        rec = {"case": name, "xfail": xfail, "expected": expect}
        session = _sess(cfg)
        try:
            ev = ENTRY.run_execution_candidate(
                session, sc, ex, artifacts, parse, make_loader, payload_bytes)
            rec["result"] = "LOADED"
            rec["committed_rows"] = ev.get("row_count")
            # NOTE: whole-table value equality is NOT asserted here. The loader no
            # longer invents a digest; it is proven by the project's unordered
            # comparator below (independent_readback.comparison). Emitting a
            # `sha_equal: false` placeholder here would read as a failed check.
            rec["pk_distinct"] = ev.get("pk_distinct")
            rec["pk_null_free"] = ev.get("pk_null_free")
            rec["non_primary_index_count"] = ev.get("non_primary_index_count")
            rec["constraint_types"] = ev.get("constraint_types")

            rec["column_count"] = len(ev.get("columns") or [])
            rec["coord_roundtrip_inexact"] = ev.get("coord_roundtrip_inexact_rows")
            rec["pk_columns_in_order"] = ev.get("pk_columns_in_order")
            rec["rolled_back"] = ev.get("rolled_back")
            rec["committed_flag"] = ev.get("committed")
            rec["null_counts"] = ev.get("null_counts")
            rec["marker_verified"] = ev["instance"].get("instance_marker_verified")
            rec["load_role"] = ev["instance"].get("load_role")
            rec["in_session_port"] = ev["instance"].get("in_session_port")
            rec["single_parse_drives_load"] = ev.get("single_parse_drives_load")
        except (L.LoaderGateError, ENTRY.LoaderGateError) as e:
            # Both the entry's own gates (endpoint/approval) and the isolated loader's
            # gates raise LoaderGateError; either way the run was REFUSED, not a failure.
            rec["result"] = "REFUSED"
            rec["error_code"] = e.code
            rec["detail"] = str(e)[:300]
        except Exception as e:  # pragma: no cover
            rec["result"] = "ERROR"
            rec["error"] = type(e).__name__ + ": " + str(e)[:300]
        finally:
            try:
                session.close()
            except Exception:
                pass
        # residue probe: is the target table present afterwards?
        probe = _sess(cfg)
        try:
            tl = L.TARGET_TABLE
            present = probe.query_csv(
                "SELECT (to_regclass('" + L.TARGET_SCHEMA + "." + tl + "') IS NOT NULL)::int").strip()
            rec["table_present_after"] = present == "1"
            rec["residue_rows"] = (
                int(probe.query_csv('SELECT count(*) FROM "' + L.TARGET_SCHEMA + '".' + tl).strip())
                if present == "1" else 0)
        finally:
            probe.close()
        out["cases"].append(rec)
        return rec

    # P1 positive
    run_case("P1_positive_full_load", expect="COMMITTED 3859")

    # N1 target already exists
    run_case("N1_target_already_exists", expect="REFUSED, untouched")

    # drop for the failure cases
    drop = _sess(cfg)
    drop.query_csv('DROP TABLE IF EXISTS "' + L.TARGET_SCHEMA + '".' + L.TARGET_TABLE)
    drop.close()

    run_case("N2_row_count_mismatch", xfail="row_count", expect="ROLLBACK 0 residue")
    run_case("N3_structure_mismatch", xfail="structure", expect="ROLLBACK 0 residue")
    run_case("N4_coord_roundtrip_inexact", xfail="coord", expect="ROLLBACK 0 residue")
    run_case(
        "N5_review_traceability_incomplete",
        mutate_scope=lambda s: s["review_traceability"].__setitem__("status", "INCOMPLETE")
        if "review_traceability" in s else s.__setitem__(
            "review_traceability", {"status": "INCOMPLETE", "missing_chain": "approval text absent"}),
        expect="REFUSED before write")
    # N5b–N5e: the four STRUCTURED traceability branches (not just the status string).
    run_case(
        "N5b_approval_text_digest_mismatch",
        mutate_scope=lambda s: s["review_traceability"].__setitem__(
            "approval_text_sha256", "0" * 64),
        expect="REFUSED before write (approval_text_digest_mismatch)")
    run_case(
        "N5c_contract_review_ref_mismatch",
        mutate_scope=lambda s: s["review_traceability"].__setitem__(
            "contract_review_ref", "some-other-ref"),
        expect="REFUSED before write (contract_review_ref_mismatch)")
    run_case(
        "N5d_approval_record_ref_mismatch",
        mutate_scope=lambda s: s["review_traceability"].__setitem__(
            "approval_record_event", "some-other-event"),
        expect="REFUSED before write (approval_record_ref_mismatch)")
    run_case(
        "N5e_approval_text_missing",
        mutate_scope=lambda s: s["review_traceability"].__setitem__("approval_text_bytes", 0),
        expect="REFUSED before write (approval_text_missing)")
    run_case(
        "N6_test_approval_bound_to_production_container",
        mutate_scope=lambda s: s["target_endpoint"].__setitem__(
            "container_id", ENTRY._PRODUCTION_CONTAINER_ID),
        expect="REFUSED, never connects")
    run_case(
        "N7_target_port_is_in_session_5432",
        mutate_scope=lambda s: s["target_endpoint"].__setitem__("port", 5432),
        expect="REFUSED")

    # P2 clean retry
    run_case("P2_clean_retry", expect="COMMITTED 3859")

    # Independent whole-table value verification of the committed state.
    # Uses the project's own unordered comparator (source sqlite stream vs target PG
    # rows) so the evidence type matches every other loader -- no locally invented
    # digest that could silently diverge from the approved 2cb8c354… 口径.
    from xiangrugu_datamgmt.unordered_validate import (
        UnorderedEvidence, UnorderedInput, compare_unordered)
    from xiangrugu_datamgmt.unordered_values import UnorderedColumn, UnorderedSchema
    from xiangrugu_datamgmt.value_sort import UnorderedLimits

    inpts = json.load(open("/tmp/ut/inputs.json"))
    obj = inpts["approved"]
    schema = UnorderedSchema(obj["source_object_id"],
                             tuple(UnorderedColumn(**c) for c in obj["columns"]))
    target_cols = [c["target_column"] for c in
                   json.load(open(cfg["contract_path"]))["rules"][0]["targets"][0]["columns"]]

    verify = _sess(cfg)
    try:
        present = verify.query_csv(
            "SELECT (to_regclass('cbdb.cbdb__social_u5f_institution_u5f_addr') IS NOT NULL)::int").strip()
        if present != "1":
            out["independent_readback"] = {"table_absent": True}
        else:
            tgt_rows = list(verify.query_rows(
                "SELECT " + ", ".join('"' + c + '"' for c in target_cols)
                + ' FROM "cbdb"."cbdb__social_u5f_institution_u5f_addr"'))
            out["independent_readback"] = {
                "method": "project unordered comparator (source sqlite vs target PG)",
                "table": "cbdb.cbdb__social_u5f_institution_u5f_addr",
                "target_row_count": len(tgt_rows),
                "column_count": len(target_cols),
            }
    finally:
        verify.close()

    # The comparator needs the source stream; it is opened in the driver so the
    # comparison is driven by source bytes, never by the payload we already sent.
    SNAP = "/mnt/wd61workmetadata/usedata/harvard/cbdb/cbdb_20260919.sqlite3"
    from xiangrugu_datamgmt.sqlite_values import open_sqlite_values
    SNAP_SIZE = 586485760
    SNAP_SHA = "bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400"

    def _src():
        with open_sqlite_values(SNAP, expected_size=SNAP_SIZE, expected_sha256=SNAP_SHA,
                                relative_path="harvard/cbdb/cbdb_20260919.sqlite3",
                                table="SOCIAL_INSTITUTION_ADDR",
                                source_columns=tuple(obj["source_columns"]),
                                schema=schema) as stream:
            for row in stream:
                yield tuple(row)

    types = [c["pg_type"] for c in obj["columns"]]

    def _coerce(v, t):
        """Restore the native Python value the schema expects (psql gives text)."""
        if v is None or v == "" or v == "\\N":
            return None
        if t == "bigint":
            return int(v)
        if t == "double precision":
            return float(v)
        return v

    def _tgt():
        for row in tgt_rows:
            yield tuple(_coerce(v, t) for v, t in zip(row, types))

    src_ev = UnorderedEvidence("source", schema.source_object_id, scope["expected_source_sha256"])
    tgt_ev = UnorderedEvidence("target", "cbdb.cbdb__social_u5f_institution_u5f_addr",
                               scope["expected_source_sha256"])
    limits = UnorderedLimits()
    report = compare_unordered(
        schema,
        UnorderedInput(schema=schema, rows=_src(), evidence=src_ev),
        UnorderedInput(schema=schema, rows=_tgt(), evidence=tgt_ev),
        limits=limits, scratch_parent="/data/var")
    rd = report.to_dict()
    out["independent_readback"]["comparison"] = {
        "result": rd.get("result"),
        "error_code": rd.get("error_code"),
        "source_sha256": rd.get("source_sha256"),
        "target_sha256": rd.get("target_sha256"),
        "differences": len(rd.get("differences") or []),
        "missing_rows": rd.get("missing_rows"),
        "excess_rows": rd.get("excess_rows"),
        "source_count": rd.get("source_count"),
        "target_count": rd.get("target_count"),
    }

    out["summary"] = {
        "cases": len(out["cases"]),
        "loaded": sum(1 for c in out["cases"] if c["result"] == "LOADED"),
        "refused": sum(1 for c in out["cases"] if c["result"] == "REFUSED"),
        "errors": sum(1 for c in out["cases"] if c["result"] == "ERROR"),
        "all_residue_zero_or_expected": all(
            c.get("residue_rows") == 0
            for c in out["cases"]
            if c["case"] not in ("P1_positive_full_load", "N1_target_already_exists", "P2_clean_retry")),
    }
    with open("/tmp/ut/entry-trial-out.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(out["summary"], ensure_ascii=False))
    for c in out["cases"]:
        print(c["case"], "->", c["result"], c.get("error_code", ""),
              "rows=", c.get("committed_rows", c.get("residue_rows")))


if __name__ == "__main__":
    main()
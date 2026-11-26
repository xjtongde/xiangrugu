#!/usr/bin/env python3
"""SOCIAL_INSTITUTION_ADDR single-table loader — isolated trial driver.

POSITIVE run : formal entry cbdb_social_addr_loader.run_single_table against the
               isolated PG (network=none, no production db visible).
NEGATIVE runs: (a) target already exists -> gate refuses before any write;
               (b) injected verification fault (row_count / structure / coord)
                   -> the single transaction ROLLBACKs, zero residue, clean retry;
               (c) review traceability incomplete -> gate refuses before any write.

Source is read read-only from the mounted verified snapshot; nothing is written there.
"""
import hashlib
import json
import subprocess
import sys

sys.path.insert(0, "/data/var/src")
# 注意：本脚本在 32 宿主机执行，psql 经 docker exec 进入隔离容器

from xiangrugu_datamgmt.cbdb_social_addr_loader import (      # noqa: E402
    EXPECTED_CANDIDATE_SHA, EXPECTED_ROWS, EXPECTED_SOURCE_SHA, LoaderGateError,
    PsqlSession, ddl_for, qtable, run_single_table, target_column_names)

SNAP = "/snapshot/harvard/cbdb/cbdb_20260919.sqlite3"
SNAP_SIZE = 586485760
SNAP_SHA = "bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400"
TABLE = "SOCIAL_INSTITUTION_ADDR"
TS, TT = "cbdb", "cbdb__social_u5f_institution_u5f_addr"

IN = json.load(open("/data/var/inputs.json"))
TARGET = IN["target"]
CONTRACT = IN["contract"]
EXPECTED = IN["expected"]
SCOPE = IN["scope"]
SCOPE_TECH = IN["scope_technical_probe"]  # 仅技术探针；正式结论以 SCOPE(INCOMPLETE) 阻断为准
INSTANCE = IN.get("instance_identity") or {}
SRC_COLS = [c["source_column"] for c in TARGET["columns"]]
TYPES = [c["pg_type"] for c in TARGET["columns"]]


PSQL = ["psql", "-X", "-q", "-tA", "-U", "postgres", "-d", "trialdb"]


def psql(sql, stdin=None):
    r = subprocess.run(PSQL + ["-v", "ON_ERROR_STOP=1", "-c", sql],
                       input=stdin, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"SQL_FAILED {sql[:70]} :: {r.stderr.decode()[:300]}")
    return r.stdout.decode()


def source_rows():
    from xiangrugu_datamgmt.unordered_values import UnorderedColumn, UnorderedSchema
    from xiangrugu_datamgmt.sqlite_values import open_sqlite_values
    obj = IN["approved"]
    schema = UnorderedSchema(obj["source_object_id"],
                             tuple(UnorderedColumn(**c) for c in obj["columns"]))
    with open_sqlite_values(SNAP, expected_size=SNAP_SIZE, expected_sha256=SNAP_SHA,
                            relative_path="harvard/cbdb/cbdb_20260919.sqlite3",
                            table=TABLE, source_columns=tuple(obj["source_columns"]),
                            schema=schema) as stream:
        for row in stream:
            yield tuple(row)


def text_field(v, t):
    if v is None:
        return "\\N"
    if t == "double precision":
        return repr(float(v))
    if t == "bigint":
        return str(int(v))
    s = str(v)
    return (s.replace("\\", "\\\\").replace("\t", "\\t")
             .replace("\n", "\\n").replace("\r", "\\r"))


def build_copy_payload():
    rows = list(source_rows())
    out = []
    for row in rows:
        out.append("\t".join(text_field(v, t) for v, t in zip(row, TYPES)))
    return ("\n".join(out) + "\n").encode("utf-8"), len(rows)


def observe_instance():
    ver = psql("show server_version").strip()
    dbs = psql("select string_agg(datname, ',' order by datname) from pg_database").strip()
    addr = psql("select coalesce(inet_server_addr()::text, 'unix-socket')").strip()
    return {"container_id": IN["container_id"], "image_id": IN["image_id"],
            "server_version": ver, "inet_server_addr": addr, "databases": dbs}


def table_exists():
    return psql(f"select to_regclass('{TS}.{TT}') is not null").strip() == "t"


def full_readback():
    cols = target_column_names(TARGET)
    out = {"table": f"{TS}.{TT}", "exists": table_exists()}
    if not out["exists"]:
        out["row_count"] = 0
        return out
    out["row_count"] = int(psql(f"select count(*) from {TS}.{TT}").strip())
    out["null_counts"] = {c: int(psql(f'select count(*) from {TS}.{TT} where "{c}" is null').strip())
                          for c in cols}
    out["structure"] = [l.split("|") for l in psql(
        "select column_name, data_type, is_nullable, ordinal_position from information_schema.columns "
        f"where table_schema='{TS}' and table_name='{TT}' order by ordinal_position").strip().splitlines()]
    out["pk_columns_in_order"] = [l.strip() for l in psql(
        "select a.attname from pg_index i join pg_attribute a on a.attrelid=i.indrelid and a.attnum=any(i.indkey) "
        f"where i.indrelid='{TS}.{TT}'::regclass and i.indisprimary "
        "order by array_position(i.indkey, a.attnum)").strip().splitlines() if l.strip()]
    out["pk_distinct"] = int(psql(
        f'select count(*) from (select distinct {", ".join(chr(34)+c+chr(34) for c in target_column_names(TARGET))} '
        f'from {TS}.{TT}) d').strip())
    out["non_primary_index_count"] = int(psql(
        f"select count(*) from pg_index i where i.indrelid='{TS}.{TT}'::regclass and not i.indisprimary").strip())
    out["constraint_types"] = sorted(l.strip() for l in psql(
        "select distinct contype from pg_constraint where conrelid='" + f"{TS}.{TT}" + "'::regclass").strip().splitlines() if l.strip())
    out["coord_check"] = psql(
        "select count(*) filter (where inst_u5f_xcoord::float8::text <> inst_u5f_xcoord::text) || ',' || "
        "count(*) filter (where inst_u5f_ycoord::float8::text <> inst_u5f_ycoord::text) "
        f"from {TS}.{TT}").strip()
    return out


def main():
    out = {"format": "xiangrugu.cbdb-social-addr-trial.v1",
           "candidate_sha256": EXPECTED_CANDIDATE_SHA,
           "expected_rows": EXPECTED_ROWS, "expected_source_sha": EXPECTED_SOURCE_SHA}
    out["instance"] = observe_instance()
    out["instance"]["isolated"] = ("cbdb_reh" not in out["instance"]["databases"]
                                   and "postgres,template0,template1,trialdb" == out["instance"]["databases"])

    payload, src_rows = build_copy_payload()
    out["copy_rows"] = src_rows
    out["copy_bytes"] = len(payload)

    # ---------- POSITIVE ----------
    sess = PsqlSession(["psql", "-U", "postgres", "-d", "trialdb"])
    try:
        pos = run_single_table(sess, SCOPE_TECH, CONTRACT, TARGET, payload, out["instance"], EXPECTED)
        out["positive"] = {"evidence": pos, "result": "COMMITTED"}
    finally:
        sess.close()
    out["positive_readback"] = full_readback()

    # independent unordered comparison against the approved expectation
    from xiangrugu_datamgmt.unordered_validate import (UnorderedEvidence, UnorderedInput,
                                                      compare_unordered)
    from xiangrugu_datamgmt.unordered_values import UnorderedColumn, UnorderedSchema
    from xiangrugu_datamgmt.value_sort import UnorderedLimits
    obj = IN["approved"]
    schema = UnorderedSchema(obj["source_object_id"],
                             tuple(UnorderedColumn(**c) for c in obj["columns"]))
    copy_out = (f"COPY (SELECT {', '.join(chr(34)+c+chr(34) for c in target_column_names(TARGET))} "
                f"from {TS}.{TT}) TO STDOUT WITH (FORMAT text, NULL '\\N')")

    def target_rows():
        sys.path.insert(0, "/data/var/src")
# 注意：本脚本在 32 宿主机执行，psql 经 docker exec 进入隔离容器
        from xiangrugu_datamgmt.cbdb_social_addr_loader import _rows_csv
        r = subprocess.run(PSQL + ["-v", "ON_ERROR_STOP=1", "-c", copy_out], capture_output=True)
        if r.returncode != 0:
            raise SystemExit("READBACK_FAIL " + r.stderr.decode()[:200])
        unesc = lambda s: s.replace("\\t", "\t").replace("\\n", "\n").replace("\\r", "\r").replace("\\\\", "\\")
        for line in r.stdout.decode().split("\n"):
            if not line:
                continue
            f = line.split("\t")
            yield tuple(None if v == "\\N" else
                        (int(unesc(v)) if t == "bigint" else
                         float(unesc(v)) if t == "double precision" else unesc(v))
                        for v, t in zip(f, TYPES))

    exp_in = UnorderedInput(schema, source_rows(),
                            UnorderedEvidence("source", "snapshot:" + TABLE, EXPECTED_SOURCE_SHA))
    tgt_in = UnorderedInput(schema, target_rows(),
                            UnorderedEvidence("target", f"{TS}.{TT}", "0" * 64))
    d = compare_unordered(schema, exp_in, tgt_in, limits=UnorderedLimits(),
                          scratch_parent="/data/var").to_dict()
    out["comparison"] = {k: d[k] for k in ("result", "source_count", "target_count",
                                           "source_fields", "target_fields", "differences",
                                           "missing_rows", "excess_rows", "source_sha256",
                                           "target_sha256", "error_code", "partial")}
    out["comparison"]["sha_equal"] = (d["source_sha256"] == d["target_sha256"] == EXPECTED_SOURCE_SHA)

    # ---------- NEGATIVE (a): target already exists ----------
    sess = PsqlSession(["psql", "-U", "postgres", "-d", "trialdb"])
    try:
        run_single_table(sess, SCOPE_TECH, CONTRACT, TARGET, payload, out["instance"], EXPECTED)
        out["negative_target_exists"] = {"result": "NOT_REJECTED", "pass": False}
    except LoaderGateError as e:
        out["negative_target_exists"] = {"result": e.code, "pass": e.code == "target_already_exists",
                                         "residue_rows": int(psql(f"select count(*) from {TS}.{TT}").strip())}
    finally:
        sess.close()

    # ---------- NEGATIVE (b): injected verification faults -> rollback, zero residue ----------
    neg = {}
    for fault in ("row_count", "structure", "coord"):
        psql(f"DROP TABLE IF EXISTS {TS}.{TT}")
        sess = PsqlSession(["psql", "-U", "postgres", "-d", "trialdb"])
        try:
            run_single_table(sess, SCOPE_TECH, CONTRACT, TARGET, payload, out["instance"],
                             EXPECTED, corrupt=fault)
            neg[fault] = {"result": "COMMITTED_UNEXPECTED", "pass": False}
        except LoaderGateError as e:
            sess.rollback()
            neg[fault] = {"result": e.code, "pass": True,
                          "table_absent_after": not table_exists(),
                          "residue_rows": 0 if not table_exists() else int(
                              psql(f"select count(*) from {TS}.{TT}").strip())}
        finally:
            sess.close()
    out["negative_rollback"] = neg

    # ---------- clean retry after rollbacks ----------
    psql(f"DROP TABLE IF EXISTS {TS}.{TT}")
    sess = PsqlSession(["psql", "-U", "postgres", "-d", "trialdb"])
    try:
        retry = run_single_table(sess, SCOPE_TECH, CONTRACT, TARGET, payload, out["instance"], EXPECTED)
        out["clean_retry"] = {"result": "COMMITTED", "row_count": retry["row_count"], "pass": True}
    except LoaderGateError as e:
        out["clean_retry"] = {"result": e.code, "pass": False}
    finally:
        sess.close()

    # ---------- NEGATIVE (c): incomplete review traceability ----------
    bad_scope = json.loads(json.dumps(SCOPE))
    bad_scope["review_traceability"]["status"] = "INCOMPLETE"
    psql(f"DROP TABLE IF EXISTS {TS}.{TT}")
    sess = PsqlSession(["psql", "-U", "postgres", "-d", "trialdb"])
    try:
        run_single_table(sess, bad_scope, CONTRACT, TARGET, payload, out["instance"], EXPECTED)
        out["negative_review_traceability"] = {"result": "NOT_REJECTED", "pass": False}
    except LoaderGateError as e:
        out["negative_review_traceability"] = {"result": e.code,
                                               "pass": e.code == "review_traceability_incomplete",
                                               "table_absent_after": not table_exists()}
    finally:
        sess.close()

    # ---------- final PASS ----------
    out["result"] = ("TRIAL_PASS"
                     if out["comparison"]["result"] == "comparison_equal"
                     and out["comparison"]["sha_equal"]
                     and out["positive_readback"]["row_count"] == EXPECTED_ROWS
                     and out["positive_readback"]["pk_distinct"] == EXPECTED_ROWS
                     and out["positive_readback"]["non_primary_index_count"] == 0
                     and all(v["pass"] for v in neg.values())
                     and out["negative_target_exists"]["pass"]
                     and out["clean_retry"]["pass"]
                     and out["negative_review_traceability"]["pass"]
                     else "TRIAL_FAIL")
    print(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True, default=str))
    return 0 if out["result"] == "TRIAL_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
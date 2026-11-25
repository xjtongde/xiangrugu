#!/usr/bin/env python3
"""B batch single-table isolated trial: SOCIAL_INSTITUTION_ADDR (psql transport).

Read-only source (verified snapshot) -> minimal loader into throwaway isolated PG
instance -> readback -> unordered value comparison against the approved
expectation. No production connection. Any failure => whole table rolled back.
"""
import json
import subprocess
import sys

sys.path.insert(0, "/src")

from xiangrugu_datamgmt.sqlite_expectations import summarize_sqlite
from xiangrugu_datamgmt.unordered_validate import (UnorderedEvidence, UnorderedInput,
                                                   compare_unordered)
from xiangrugu_datamgmt.unordered_values import UnorderedColumn, UnorderedSchema
from xiangrugu_datamgmt.value_sort import UnorderedLimits

SNAP = "/snapshot/cbdb_20260919.sqlite3"
SNAP_SIZE = 586485760
SNAP_SHA = "bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400"
REL = "harvard/cbdb/cbdb_20260919.sqlite3"
TABLE = "SOCIAL_INSTITUTION_ADDR"
TS = "cbdb"
TT = "cbdb__social_u5f_institution_u5f_addr"
SCRATCH = "/data/var"
PSQL = ["psql", "-X", "-q", "-U", "postgres", "-d", "trialdb"]

IN = json.load(open("/work/inputs.json"))
OBJ, EXP, MAP = IN["approved"], IN["expected"], IN["mapping"]
COLS = [c["target_column"] for c in MAP]
TYPES = [c["target_type"] for c in MAP]
SRC_COLS = tuple(OBJ["source_columns"])
QCOLS = ", ".join(f'"{c}"' for c in COLS)
COERCE = {"bigint": int, "double precision": float, "text": str}


def schema():
    return UnorderedSchema(OBJ["source_object_id"],
                           tuple(UnorderedColumn(**c) for c in OBJ["columns"]))


def sql(statement, stdin_bytes=None):
    r = subprocess.run(PSQL + ["-tA", "-v", "ON_ERROR_STOP=1", "-c", statement],
                       input=stdin_bytes, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"SQL_FAILED {statement[:80]} :: {r.stderr.decode()[:400]}")
    return r.stdout.decode()


def source_rows():
    from xiangrugu_datamgmt.sqlite_values import open_sqlite_values
    with open_sqlite_values(SNAP, expected_size=SNAP_SIZE, expected_sha256=SNAP_SHA,
                            relative_path=REL, table=TABLE, source_columns=SRC_COLS,
                            schema=schema()) as stream:
        for row in stream:
            yield tuple(row)


def unescape(field):
    out, i = [], 0
    while i < len(field):
        ch = field[i]
        if ch == "\\" and i + 1 < len(field):
            nxt = field[i + 1]
            out.append({"t": "\t", "n": "\n", "r": "\r", "\\": "\\"}.get(nxt, nxt))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def text_field(v):
    if v is None:
        return "\\N"
    if isinstance(v, float):
        return repr(v)
    s = str(v)
    return (s.replace("\\", "\\\\").replace("\t", "\\t")
             .replace("\n", "\\n").replace("\r", "\\r"))


def main():
    out = {"table": TABLE, "target": f"{TS}.{TT}"}

    summary = summarize_sqlite(SNAP, expected_size=SNAP_SIZE, expected_sha256=SNAP_SHA,
                               relative_path=REL, table=TABLE, source_columns=SRC_COLS,
                               schema=schema(), scratch_parent=SCRATCH)
    out["reproduced"] = {k: summary[k] for k in ("expected_count", "expected_sha256",
        "field_count", "schema_hash", "status", "cleanup_complete")}
    out["expectation_match"] = {
        "count": summary["expected_count"] == OBJ["previous_observed_rows"] == EXP["expected_count"],
        "sha": summary["expected_sha256"] == EXP["expected_sha256"],
        "fields": summary["field_count"] == EXP["field_count"],
        "schema": summary["schema_hash"] == EXP["schema_hash"] == OBJ["schema_hash"],
    }
    if not all(out["expectation_match"].values()):
        out["result"] = "TRIAL_FAIL"
        print(json.dumps(out, ensure_ascii=False, sort_keys=True))
        return 1

    sql(f"CREATE SCHEMA IF NOT EXISTS {TS}")
    sql(f"DROP TABLE IF EXISTS {TS}.{TT}")
    ddl = ", ".join(f'"{c}" {t}' for c, t in zip(COLS, TYPES))
    sql(f"CREATE TABLE {TS}.{TT} ({ddl})")

    rows = list(source_rows())
    payload = "".join("\t".join(text_field(v) for v in row) + "\n" for row in rows)
    copy_stmt = (f"COPY {TS}.{TT} ({', '.join(COLS)}) FROM STDIN "
                 f"WITH (FORMAT text, NULL '\\N')")
    sql(copy_stmt, payload.encode())
    out["copied_rows"] = len(rows)

    out["pg_row_count"] = int(sql(f"SELECT count(*) FROM {TS}.{TT}").strip())
    out["null_counts"] = {c: int(sql(
        f'SELECT count(*) FROM {TS}.{TT} WHERE "{c}" IS NULL').strip()) for c in COLS}
    out["duplicate_rows"] = int(sql(
        f"SELECT count(*) FROM (SELECT 1 FROM {TS}.{TT} GROUP BY {QCOLS} HAVING count(*) > 1) d").strip())
    out["pg_structure"] = [l.split("|") for l in sql(
        "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
        f"WHERE table_schema='{TS}' AND table_name='{TT}' ORDER BY ordinal_position").strip().splitlines()]

    def target_rows():
        copy_out = (f"COPY (SELECT {QCOLS} FROM {TS}.{TT}) TO STDOUT "
                    f"WITH (FORMAT text, NULL '\\N')")
        r = subprocess.run(PSQL + ["-v", "ON_ERROR_STOP=1", "-c", copy_out],
                           capture_output=True)
        if r.returncode != 0:
            raise SystemExit("READBACK_FAILED " + r.stderr.decode()[:300])
        for line in r.stdout.decode().split("\n"):
            if not line:
                continue
            fields = line.split("\t")
            yield tuple(None if f == "\\N" else COERCE[t](unescape(f))
                        for f, t in zip(fields, TYPES))

    exp_in = UnorderedInput(schema(), iter(rows),
        UnorderedEvidence("source", "snapshot:" + TABLE, EXP["expected_sha256"]))
    tgt_in = UnorderedInput(schema(), target_rows(),
        UnorderedEvidence("target", f"{TS}.{TT}", "0" * 64))
    d = compare_unordered(schema(), exp_in, tgt_in,
                          limits=UnorderedLimits(), scratch_parent=SCRATCH).to_dict()
    out["comparison"] = {k: d[k] for k in ("result", "source_count", "target_count",
        "source_fields", "target_fields", "differences", "missing_rows", "excess_rows",
        "source_sha256", "target_sha256", "error_code", "error_side", "scan_index",
        "column_key", "partial")}
    out["comparison"]["sha_equal"] = (d["source_sha256"] == d["target_sha256"]
                                      == EXP["expected_sha256"])

    sql(f"DROP TABLE {TS}.{TT}")
    out["rollback"] = {"table_dropped":
        sql(f"SELECT to_regclass('{TS}.{TT}') IS NULL").strip() == "t"}

    out["result"] = ("TRIAL_PASS" if out["pg_row_count"] == EXP["expected_count"]
                     and out["comparison"]["result"] == "comparison_equal"
                     and out["comparison"]["sha_equal"]
                     and len(out["comparison"]["differences"]) == 0
                     and out["rollback"]["table_dropped"] else "TRIAL_FAIL")
    print(json.dumps(out, ensure_ascii=False, sort_keys=True, default=str))
    return 0 if out["result"] == "TRIAL_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""m004812 isolated trial load + full readback (temporary PostgreSQL only).

Reads the verified 32 snapshot read-only, reuses the approved 7 source columns,
one-based rownum, 29 rows and XRGVALUE-v1 expectation. Minimal load path uses
canonical.py (stream verification) + psql COPY into a brand-new temporary
postgres:18-bookworm container with --network none (no host ports, no access to
pg32/pg32b). Instance identity is verified BEFORE any write. Never touches
pg32/pg32b:5433/xiangrugu. Trial table name is explicitly temporary; candidate
production names remain unapproved.
"""
import csv
import hashlib
import io
import json
import subprocess
import sys
import time
from pathlib import Path

from xiangrugu_datamgmt import canonical

SRC = Path("/mnt/wd61workmetadata/usedata/harvard-full/doi_10_7910/DVN/MI56KU/2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab")
SRC_SHA = "cdc6d3e5d6d85e139305efe9c617c756f0eb668c19ce34efc4eca4f6cc8c2728"
SID = "1334a175777350ed2cb0c7ea037bd89fa74f660b1ab351400b09d06d0142ee76"
EXPECTED_SHA = "b3f6ceb609a853cbb06eb7f8004a39f676d1ff5e95fbb46fc0381abbf722f667"
EXPECTED_ROWS = 29
CONTAINER = "xiangrugu-trial-m004812"
IMAGE = "postgres:18-bookworm"
TRIAL_TABLE = "harv.trial_m004812_20261123"
COLUMNS = [
    ("c7a256b06ec71d74817f8ee21157421ce1aeba8fcf67d6196041bbbc4e769f48", "authorlast"),
    ("af17023a88e64e6f6724d4d047b8d7420a0faf3c4c8494eb647941631a98136c", "authorfirst"),
    ("c56bb84ed7c0ace1fcdffaf0d66483736c6a97038c65100164656bd87a9fa0b9", "format"),
    ("f13ff07d214294441502620f83d42df6f6e0ab00e9779ca89542c4a1de252ee8", "language"),
    ("f3ae27351dbd9f8101c67dbb8b85d1b703f6d0e96c610b2937ddd0f8dac046dc", "type"),
    ("144070aa1993d02d92dbd83125e7dca396669af4f2b71d046eaf2041da54bacd", "title"),
    ("de8acd389c549246eb8169b17e74a3ba819380682dff98a35d757a13753bece3", "filename"),
]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def psql(sql, db="xiangrugu_trial", csv_out=False):
    cmd = ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", db, "-v", "ON_ERROR_STOP=1"]
    if csv_out:
        cmd += ["-t", "--csv", "-c", sql]
    else:
        cmd += ["-c", sql]
    return run(cmd)


def parse_tab(raw):
    text = raw.decode("utf-8", errors="strict")
    lines = text.split("\n")
    assert lines[-1] == "" and len(lines) == 31, "line count"
    header = lines[0].split("\t")
    assert header == [t for _, t in COLUMNS], "header != approved columns"
    rows = []
    for line in lines[1:30]:
        fields, i, n = [], 0, len(line)
        while i < n:
            assert line[i] == '"', "field not quoted"
            i += 1
            buf = []
            while i < n:
                ch = line[i]
                if ch == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        buf.append('"'); i += 2; continue
                    i += 1; break
                if ch == "\\" and i + 1 < n and line[i + 1] == '"':
                    buf.append('"'); i += 2; continue  # backslash_escape approved
                buf.append(ch); i += 1
            fields.append("".join(buf))
            if i < n:
                assert line[i] == "\t", "field separator"
                i += 1
        assert len(fields) == 7, "field count"
        rows.append(tuple(fields))
    return rows


def build_schema():
    return canonical.ValueSchema(
        source_object_id=SID,
        columns=tuple(canonical.ValueColumn(column_key=k, target_name=t, pg_type="text", nullable=False)
                      for k, t in COLUMNS)
        + (canonical.ValueColumn(column_key=canonical.ROW_KEY, target_name="__src_rownum",
                                 pg_type="bigint", nullable=False),))


def stream_sha(rows):
    schema = build_schema()
    s = canonical.summarize_rows(schema, (r + (i + 1,) for i, r in enumerate(rows)),
                                 limits=canonical.ValueLimits())
    return s


def main():
    ev = {"version": 1, "object_rule_id": "m004812", "source_object_id": SID,
          "trial_only": True, "formal_contract_modified": False,
          "pg32_pg32b_touched": False, "candidate_names_approved": False}
    raw = SRC.read_bytes()
    ev["source"] = {"path": str(SRC), "sha256": sha(raw), "size": len(raw),
                    "sha_match": sha(raw) == SRC_SHA}
    if not ev["source"]["sha_match"]:
        ev["status"] = "SOURCE_SHA_MISMATCH_STOP"; print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    rows = parse_tab(raw)
    src_summary = stream_sha(rows)
    ev["source_side_stream"] = {"row_count": src_summary.row_count, "field_count": src_summary.field_count,
                                "stream_bytes": src_summary.stream_bytes, "sha256": src_summary.sha256,
                                "expected_sha256": EXPECTED_SHA,
                                "matches_approved_expectation": src_summary.sha256 == EXPECTED_SHA,
                                "rows_match_29": src_summary.row_count == EXPECTED_ROWS}
    if src_summary.sha256 != EXPECTED_SHA or src_summary.row_count != EXPECTED_ROWS:
        ev["status"] = "SOURCE_EXPECTATION_MISMATCH_STOP"; print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    # --- temporary isolated instance ---
    # NOTE: fixed-name pre-delete removed (2026-11-23 spatial2 box dispatch, same
    # safety pattern as trial_text5.py): a name collision must fail closed.
    r = run(["docker", "run", "-d", "--name", CONTAINER, "--network", "none",
             "-e", "POSTGRES_PASSWORD=trial-only-not-production", "-e", "POSTGRES_DB=xiangrugu_trial", IMAGE])
    ev["container_start"] = {"exit": r.returncode, "image": IMAGE, "network": "none",
                             "host_port_mapping": "none", "stderr": r.stderr.strip()[:200]}
    if r.returncode != 0:
        ev["status"] = "CONTAINER_START_FAILED_STOP"; print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    ready = False
    for _ in range(60):
        if run(["docker", "exec", CONTAINER, "pg_isready", "-U", "postgres"]).returncode == 0:
            ready = True; break
        time.sleep(1)
    ev["pg_isready"] = ready
    if not ready:
        ev["status"] = "PG_NOT_READY_STOP"; print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    ident = {}
    for _ in range(30):  # wait out the entrypoint initdb temporary-server phase
        for key, sql in [("server_version", "SHOW server_version"), ("data_directory", "SHOW data_directory"),
                         ("port", "SHOW port"), ("start_time", "SELECT pg_postmaster_start_time()"),
                         ("inet_server_addr", "SELECT coalesce(inet_server_addr()::text,'null')"),
                         ("databases", "SELECT datname FROM pg_database ORDER BY datname")]:
            ident[key] = psql(sql, db="postgres", csv_out=True).stdout.strip()
        if all(ident.values()):
            break
        time.sleep(1)
    ev["instance_identity"] = ident
    ev["identity_verified_before_write"] = (
        ident["server_version"].startswith("18")
        and ident["data_directory"].startswith("/var/lib/postgresql/")
        and ident["inet_server_addr"] == "null"
        and "xiangrugu_trial" in ident["databases"]
        and "pg32b" not in ident["databases"] and "cbdb" not in ident["databases"]
        and ident["databases"].replace("xiangrugu_trial", "").find("xiangrugu") < 0)
    if not ev["identity_verified_before_write"]:
        ev["status"] = "IDENTITY_CHECK_FAILED_STOP"; print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    # --- minimal load path: DDL + COPY ---
    cols_ddl = ", ".join(f"{t} text NOT NULL" for _, t in COLUMNS)
    ddl = (f"CREATE SCHEMA harv; CREATE TABLE {TRIAL_TABLE} ({cols_ddl}, "
           "__src_rownum bigint NOT NULL PRIMARY KEY);")
    r = psql(ddl)
    ev["ddl_exit"] = r.returncode
    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t", quotechar='"', quoting=csv.QUOTE_ALL, lineterminator="\n")
    for i, row in enumerate(rows):
        w.writerow(list(row) + [i + 1])
    copy_cmd = ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", "xiangrugu_trial",
                "-v", "ON_ERROR_STOP=1", "-c",
                f"\\copy {TRIAL_TABLE} FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '\"')"]
    r = run(copy_cmd, input=buf.getvalue())
    ev["copy_exit"] = r.returncode
    ev["copy_stderr"] = r.stderr.strip()[:200]
    if r.returncode != 0:
        ev["status"] = "COPY_FAILED_STOP"; print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    # --- full readback by source rownum ---
    sel = ", ".join(t for _, t in COLUMNS) + ", __src_rownum"
    r = psql(f"SELECT {sel} FROM {TRIAL_TABLE} ORDER BY __src_rownum", csv_out=True)
    ev["readback_exit"] = r.returncode
    db_rows = [tuple(rec) for rec in csv.reader(io.StringIO(r.stdout))]
    db_rows = [tuple(v for v in rec[:7]) + (int(rec[7]),) for rec in db_rows]
    rb_summary = stream_sha([rec[:7] for rec in db_rows])
    meta = psql("SELECT column_name, data_type, is_nullable, ordinal_position FROM information_schema.columns "
                f"WHERE table_schema='harv' AND table_name='trial_m004812_20261123' ORDER BY ordinal_position", csv_out=True)
    meta_rows = list(csv.reader(io.StringIO(meta.stdout)))
    expected_meta = [[t, "text", "NO", str(i + 1)] for i, (_, t) in enumerate(COLUMNS)] + [["__src_rownum", "bigint", "NO", "8"]]
    cnt = psql(f"SELECT count(*) FROM {TRIAL_TABLE}", csv_out=True).stdout.strip()
    dup = psql(f"SELECT count(*) FROM (SELECT {sel} FROM {TRIAL_TABLE} GROUP BY {sel} HAVING count(*)>1) d", csv_out=True).stdout.strip()
    rownum_ok = [rec[7] for rec in db_rows] == list(range(1, 30))
    ev["readback"] = {"row_count": len(db_rows), "count_query": cnt,
                      "columns_meta_match": meta_rows == expected_meta, "columns_meta": meta_rows,
                      "rownum_sequence_1_29": rownum_ok,
                      "duplicate_row_groups": dup,
                      "stream_sha256_from_db_values": rb_summary.sha256,
                      "matches_approved_expectation": rb_summary.sha256 == EXPECTED_SHA,
                      "stream_bytes": rb_summary.stream_bytes, "field_count": rb_summary.field_count}
    ok = (len(db_rows) == 29 and cnt == "29" and meta_rows == expected_meta and rownum_ok
          and dup == "0" and rb_summary.sha256 == EXPECTED_SHA)
    ev["status"] = "TRIAL_LOAD_READBACK_PASS" if ok else "TRIAL_READBACK_DIFF_STOP"
    ev["first_difference"] = None if ok else "see readback node"
    print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True))
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
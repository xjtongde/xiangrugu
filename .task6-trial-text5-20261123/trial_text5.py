#!/usr/bin/env python3
"""Five approved text objects: isolated trial load + full readback (temporary PG only).

Reads ONLY the verified 32 project snapshot. Reuses the local postgres:18-bookworm
image (actual Id + RepoDigests recorded). One container per run with a unique name,
--network none, no host ports; cleanup targets only this run's container. Per item:
source sha + schema sha + row count gates BEFORE write; canonical XRGVALUE-v1 stream
sha must equal the approved expectation before any write; any reading/digest/identity
mismatch stops THAT item with evidence preserved (others continue). Duplicate counts
use actual value columns only (unique __src_rownum excluded from the duplicate key).
Never touches pg32/pg32b/deploy/formal landing.
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

ROOT = Path("/mnt/wd61workmetadata/usedata")
REL = Path("datamgmt/contracts/releases/2026-10-06-bootstrap")
APPROVED = json.loads((REL / "text-value-contract-approved.draft.json").read_text())
EXPECT = json.loads(Path("docs/superpowers/evidence/2026-10-08-text-source-values/text-source-value-expectations.draft.json").read_text())
READING = {}
for f in ("text-reading-decisions.draft.yaml", "additional-text-reading-decisions.draft.yaml"):
    txt = (REL / f).read_text()
    cur = None
    for line in txt.splitlines():
        s = line.strip()
        if s.startswith("- rule_id:"):
            cur = s.split(":", 1)[1].strip(); READING[cur] = {}
        elif cur and ":" in s:
            k, v = s.split(":", 1); READING[cur][k.strip()] = v.strip()
CONTAINER = "xiangrugu-trial-text5-20261123-173109"
IMAGE = "postgres:18-bookworm"
VC_BY_RULE = {o["rule_id"]: o["value_columns"] for o in EXPECT["objects"]}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def psql(sql, db="xiangrugu_trial", csv_out=False):
    cmd = ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", db, "-v", "ON_ERROR_STOP=1"]
    cmd += (["-t", "--csv", "-c", sql] if csv_out else ["-c", sql])
    return run(cmd)


def parse_rows(raw, rule, ncols):
    rd = READING[rule]
    text = raw.decode(rd["codec"], errors="strict")
    be = rd["backslash_escape"] == "true"
    rdr = csv.reader(io.StringIO(text), delimiter="\t", quotechar='"', doublequote=True,
                     escapechar="\\" if be else None, strict=True)
    allrows = list(rdr)
    header, data = allrows[0], allrows[1:]
    assert len(header) == ncols, f"header field count {len(header)} != {ncols}"
    assert all(len(r) == ncols for r in data), "data field count mismatch"
    return data


def schema_of(rule):
    vc = VC_BY_RULE[rule]
    cols = tuple(canonical.ValueColumn(column_key=c["column_key"], target_name=c["target_name"],
                                       pg_type=c["pg_type"], nullable=c["nullable"]) for c in vc)
    assert cols[-1].column_key == canonical.ROW_KEY
    obj = next(o for o in APPROVED["objects"] if o["rule_id"] == rule)
    return canonical.ValueSchema(source_object_id=obj["source_object_id"], columns=cols), obj


def stream_of(rule, rows):
    schema, _ = schema_of(rule)
    return canonical.summarize_rows(schema, (tuple(r) + (i + 1,) for i, r in enumerate(rows)),
                                    limits=canonical.ValueLimits())


def main():
    ev = {"version": 1, "trial_only": True, "container": CONTAINER, "image": IMAGE,
          "network": "none", "host_port_mapping": "none",
          "pg32_pg32b_deploy_touched": False, "formal_contract_modified": False,
          "cleanup_scope": "only this run's container"}
    insp = run(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}} | {{json .RepoDigests}}"])
    ev["image_identity"] = {"exit": insp.returncode, "id_and_digests": insp.stdout.strip()}
    items = []
    pre = {}
    for obj in APPROVED["objects"]:
        rule = obj["rule_id"]
        it = {"rule_id": rule, "source_object_id": obj["source_object_id"],
              "approved_schema": obj["approved_schema"], "expected": obj["expected"]}
        raw = (ROOT / obj["source"]["path"]).read_bytes()
        it["source_sha256"] = sha(raw)
        it["source_sha_match"] = sha(raw) == obj["source"]["sha256"]
        schema, _ = schema_of(rule)
        it["schema_sha256"] = sha(canonical.schema_bytes(schema))
        it["schema_sha_match"] = it["schema_sha256"] == obj["schema_sha256"]
        ncols = len(VC_BY_RULE[rule]) - 1
        try:
            rows = parse_rows(raw, rule, ncols)
            it["row_count_parsed"] = len(rows)
            it["row_count_match"] = len(rows) == obj["expected"]["row_count"]
            s = stream_of(rule, rows)
            it["source_stream"] = {"sha256": s.sha256, "stream_bytes": s.stream_bytes,
                                   "field_count": s.field_count,
                                   "matches_approved": s.sha256 == obj["expected"]["sha256"],
                                   "bytes_match": s.stream_bytes == obj["expected"]["stream_bytes"]}
            ok = it["source_sha_match"] and it["schema_sha_match"] and it["row_count_match"] \
                and it["source_stream"]["matches_approved"] and it["source_stream"]["bytes_match"]
            it["pre_write_gate"] = "PASS" if ok else "STOP"
            pre[rule] = rows if ok else None
        except Exception as e:
            it["pre_write_gate"] = "STOP"; it["stop_reason"] = f"parse: {e}"; pre[rule] = None
        items.append(it)
    ev["items"] = items
    if not all(pre.values()):
        ev["status"] = "PRE_WRITE_GATE_STOP"
        ev["total_rows"] = None
        print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    # --- one isolated temporary instance, unique identity ---
    run(["docker", "rm", "-f", CONTAINER])
    r = run(["docker", "run", "-d", "--name", CONTAINER, "--network", "none",
             "-e", "POSTGRES_PASSWORD=trial-only-not-production", "-e", "POSTGRES_DB=xiangrugu_trial", IMAGE])
    ev["container_start_exit"] = r.returncode
    if r.returncode != 0:
        ev["status"] = "CONTAINER_START_FAILED_STOP"; print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    ready = False
    for _ in range(60):
        if run(["docker", "exec", CONTAINER, "pg_isready", "-U", "postgres"]).returncode == 0:
            ready = True; break
        time.sleep(1)
    if not ready:
        ev["status"] = "PG_NOT_READY_STOP"; print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    ident = {}
    for _ in range(30):
        for key, sql in [("server_version", "SHOW server_version"), ("data_directory", "SHOW data_directory"),
                         ("start_time", "SELECT pg_postmaster_start_time()"),
                         ("inet_server_addr", "SELECT coalesce(inet_server_addr()::text,'null')"),
                         ("databases", "SELECT datname FROM pg_database ORDER BY datname")]:
            ident[key] = psql(sql, db="postgres", csv_out=True).stdout.strip()
        if all(ident.values()):
            break
        time.sleep(1)
    ev["instance_identity"] = ident
    ev["identity_verified_before_write"] = (
        ident["server_version"].startswith("18") and ident["data_directory"].startswith("/var/lib/postgresql/")
        and ident["inet_server_addr"] == "null" and "xiangrugu_trial" in ident["databases"]
        and "pg32b" not in ident["databases"] and "cbdb" not in ident["databases"]
        and ident["databases"].replace("xiangrugu_trial", "").find("xiangrugu") < 0)
    if not ev["identity_verified_before_write"]:
        ev["status"] = "IDENTITY_CHECK_FAILED_STOP"; print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    psql("CREATE SCHEMA IF NOT EXISTS harv; CREATE SCHEMA IF NOT EXISTS chgis;")
    total = 0
    for it in items:
        rule = it["rule_id"]; rows = pre[rule]
        vc = VC_BY_RULE[rule][:-1]
        table = f'{it["approved_schema"]}.trial_{rule}_20261123'
        it["trial_table"] = table
        ddl = f'CREATE TABLE {table} (' + ", ".join(f'{c["target_name"]} text NOT NULL' for c in vc) \
            + ', __src_rownum bigint NOT NULL PRIMARY KEY);'
        r = psql(ddl); it["ddl_exit"] = r.returncode
        if r.returncode != 0:
            it["status"] = "STOP"; it["stop_reason"] = "ddl: " + r.stderr.strip()[:150]; continue
        buf = io.StringIO()
        w = csv.writer(buf, delimiter="\t", quotechar='"', quoting=csv.QUOTE_ALL, lineterminator="\n")
        for i, row in enumerate(rows):
            w.writerow(list(row) + [i + 1])
        r = run(["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", "xiangrugu_trial",
                 "-v", "ON_ERROR_STOP=1", "-c",
                 f"\\copy {table} FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '\"')"], input=buf.getvalue())
        it["copy_exit"] = r.returncode
        if r.returncode != 0:
            it["status"] = "STOP"; it["stop_reason"] = "copy: " + r.stderr.strip()[:150]; continue
        sel = ", ".join(c["target_name"] for c in vc) + ", __src_rownum"
        r = psql(f"SELECT {sel} FROM {table} ORDER BY __src_rownum", csv_out=True)
        it["readback_exit"] = r.returncode
        db_rows = list(csv.reader(io.StringIO(r.stdout)))
        n = len(vc)
        db_rows = [tuple(rec[:n]) + (int(rec[n]),) for rec in db_rows]
        s = stream_of(rule, [rec[:n] for rec in db_rows])
        meta = list(csv.reader(io.StringIO(psql(
            "SELECT column_name, data_type, is_nullable, ordinal_position FROM information_schema.columns "
            f"WHERE table_schema='{it['approved_schema']}' AND table_name='trial_{rule}_20261123' "
            "ORDER BY ordinal_position", csv_out=True).stdout)))
        exp_meta = [[c["target_name"], "text", "NO", str(i + 1)] for i, c in enumerate(vc)] \
            + [["__src_rownum", "bigint", "NO", str(n + 1)]]
        valcols = ", ".join(c["target_name"] for c in vc)
        dup_groups = psql(f"SELECT count(*) FROM (SELECT {valcols} FROM {table} GROUP BY {valcols} HAVING count(*)>1) d", csv_out=True).stdout.strip()
        dup_rows = psql(f"SELECT coalesce(sum(c)-count(*),0) FROM (SELECT count(*) c FROM {table} GROUP BY {valcols} HAVING count(*)>1) d", csv_out=True).stdout.strip()
        nulls = psql(f"SELECT count(*) FROM {table} WHERE " + " OR ".join(f'{c["target_name"]} IS NULL' for c in vc), csv_out=True).stdout.strip()
        rn = [rec[n] for rec in db_rows]
        ok = (r.returncode == 0 and len(db_rows) == it["expected"]["row_count"]
              and meta == exp_meta and rn == list(range(1, len(db_rows) + 1))
              and nulls == "0" and s.sha256 == it["expected"]["sha256"]
              and s.stream_bytes == it["expected"]["stream_bytes"])
        it["readback"] = {"row_count": len(db_rows), "columns_meta_match": meta == exp_meta,
                          "null_value_semantics": {"all_not_null": all(m[2] == "NO" for m in meta), "null_rows": nulls},
                          "rownum_sequence_ok": rn == list(range(1, len(db_rows) + 1)),
                          "duplicate_groups_value_cols_only": dup_groups,
                          "duplicate_extra_rows_value_cols_only": dup_rows,
                          "duplicate_key_excludes_src_rownum": True,
                          "stream_sha256_from_db_values": s.sha256,
                          "matches_approved_expectation": s.sha256 == it["expected"]["sha256"],
                          "stream_bytes": s.stream_bytes}
        it["status"] = "PASS" if ok else "STOP"
        if not ok:
            it["stop_reason"] = "readback mismatch (see readback node)"
        else:
            total += len(db_rows)
    ev["total_rows_all_pass"] = total
    ev["all_five_pass"] = all(it["status"] == "PASS" for it in items)
    ev["total_matches_47607"] = total == 47607
    ev["status"] = "TRIAL_TEXT5_PASS" if ev["all_five_pass"] and ev["total_matches_47607"] else "TRIAL_TEXT5_PARTIAL_OR_STOP"
    ev["first_difference"] = next(({"rule_id": it["rule_id"], "reason": it.get("stop_reason")}
                                   for it in items if it["status"] != "PASS"), None)
    print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True))
    sys.exit(0 if ev["status"] == "TRIAL_TEXT5_PASS" else 2)


if __name__ == "__main__":
    main()
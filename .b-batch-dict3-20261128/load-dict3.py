#!/usr/bin/env python3
"""Fixed, independent three-table loader entry for the CBDB dictionary tables.

WHY THIS EXISTS AS A SEPARATE ENTRY (not a change to the B-batch loader)
-----------------------------------------------------------------------
The B-batch loader cannot address another table at all: its DDL builder takes the
table name from module constants --

    cbdb_social_addr_loader.py:48   def qtable(): return f'{TARGET_SCHEMA}.{TARGET_TABLE}'
    cbdb_social_addr_loader.py:216  q = f"CREATE TABLE {qtable()} (\\n" + ...

so `ddl_for({"schema_name": "cbdb", "table": "cbdb__extant_u5f_codes", ...})` still
emits `CREATE TABLE cbdb.cbdb__social_u5f_institution_u5f_addr (...)`: the caller's
target is silently ignored. That was proven live in the previous box. Rather than
widen that single-table code path, this entry builds and runs its own DDL/COPY and
REUSES only the transport primitive (`PsqlSession`) plus the adjudicated canonical
digest helpers.

SAFETY MODEL
------------
* Hard whitelist: exactly three target relations are permitted, checked on every
  DDL/COPY/SELECT/INSERT. Anything else raises and nothing is executed. The check is
  in code, not documentation.
* Pre-flight before any write: contract digest, three payload digests, connection
  facts (dbname / instance marker / port / role), and absence of all three targets.
* One transaction for all three tables; SQL failure aborts immediately (no swallow,
  no continue).
* Row counts must be 4/4/6 BEFORE commit, otherwise rollback.
* Never creates the schema: it reuses the pre-built `cbdb`.
"""
import hashlib
import json
import os
import pathlib
import sys

sys.path.insert(0, "/app/datamgmt/src")
from xiangrugu_datamgmt import cbdb_social_addr_loader as L  # noqa: E402
from xiangrugu_datamgmt.unordered_values import (  # noqa: E402
    UnorderedSchema, UnorderedColumn, UnorderedLimits,
    header_bytes, trailer_bytes, encode_unordered_row)

# ------------------------------------------------------------------ fixed inputs
ART_DIR = pathlib.Path("/data-var-bb/dict3")
CONTRACT = ART_DIR / "contract-three-tables.json"
CONTRACT_SHA = "12789a6c7aa0ed82e27cd1457a5d6a97f620d5d7307298eabe2399187fd4b4f7"

# The ONLY permitted targets. Enforced by assert_target() below.
ALLOWED = {
    "EXTANT_CODES":          {"schema": "cbdb", "table": "cbdb__extant_u5f_codes",
                              "rows": 4, "payload_sha": "132686c3cf0a67c5c80e776034fc73315bff991d3b5fcf49d3bba3059ef86b8e"},
    "POSSESSION_ACT_CODES":  {"schema": "cbdb", "table": "cbdb__possession_u5f_act_u5f_codes",
                              "rows": 4, "payload_sha": "52d9b446a42042e805bca18685488bbf8072a19a288e29c05e27bf8abd480dd1"},
    "ASSUME_OFFICE_CODES":   {"schema": "cbdb", "table": "cbdb__assume_u5f_office_u5f_codes",
                              "rows": 6, "payload_sha": "b9e490d409fcac80273e42ece76052b9cdf48638d88cd046f8bafedde167f84f"},
}
ORDER = ["EXTANT_CODES", "POSSESSION_ACT_CODES", "ASSUME_OFFICE_CODES"]
ADJUDICATED = {
    "EXTANT_CODES":          "2e6c0057fde56ea147f05365c47157eb37d41869f375a19b75d06b3dc3c990c2",
    "POSSESSION_ACT_CODES":  "95df512964fa910a1ade063b966c64ad586c4778b6f410ad70358849040318d8",
    "ASSUME_OFFICE_CODES":   "08d7e819d52a34082505cbac6ee98a0bdaf7e8fefed7a3d7fa76a1f874b23f95",
}
EXPECT_DBNAME = "xiangrugu"
EXPECT_PORT = "5432"
EXPECT_ROLE = "xrg_loader"


class GateError(Exception):
    pass


def fail(msg):
    raise GateError(msg)


# ------------------------------------------------------------ whitelist hard check
def assert_target(schema, table, ctx):
    """Refuse anything that is not one of the three fixed targets."""
    if schema != "cbdb":
        fail(f"whitelist_violation[{ctx}]: schema {schema!r} is not 'cbdb'")
    allowed_tables = {v["table"] for v in ALLOWED.values()}
    if table not in allowed_tables:
        fail(f"whitelist_violation[{ctx}]: table {table!r} not in {sorted(allowed_tables)}")
    if not all(c.isalnum() or c == "_" for c in table):
        fail(f"identifier_check[{ctx}]: unsafe table identifier {table!r}")


def qrel(schema, table, ctx):
    assert_target(schema, table, ctx)
    return f'"{schema}"."{table}"'


# --------------------------------------------------------------- build the DDL
def ddl_for_target(e):
    """Own DDL builder -- L.ddl_for() ignores the caller's table name (see header)."""
    defs = []
    for c in e["columns"]:
        defs.append('  "%s" %s%s' % (c["target_column"], c["pg_type"],
                                     "" if c["nullable"] else " NOT NULL"))
    pk = ", ".join('"%s"' % c for c in e["primary_key"]["columns_in_order"])
    defs.append("  PRIMARY KEY (%s)" % pk)
    rel = qrel(e["target_schema"], e["target_table"], "ddl")
    sql = 'CREATE TABLE %s (\n' % rel + ",\n".join(defs) + "\n);"
    if "CREATE SCHEMA" in sql.upper():
        fail("schema_creation_forbidden: built DDL contains CREATE SCHEMA")
    return sql


def canon_digest(schema_obj, rows, cols, count):
    """Adjudicated method: sorted ENCODED FRAMES, real header/trailer helpers."""
    lim = UnorderedLimits()
    frames = [encode_unordered_row(schema_obj, tuple(r), limits=lim) for r in rows]
    h = hashlib.sha256()
    h.update(header_bytes(schema_obj))
    for f in sorted(frames):
        h.update(f)
    h.update(trailer_bytes(count))
    return h.hexdigest()


def main():
    case = sys.argv[1] if len(sys.argv) > 1 else "A"
    host = sys.argv[2]
    pw = pathlib.Path(os.environ.get("DICT3_PW_FILE", "/data-var-bb/dict3/.pw")).read_text().strip()
    env = dict(os.environ, PGPASSWORD=pw)

    art = json.loads(CONTRACT.read_text())["tables"]
    # ---- contract self-binding -----------------------------------------------
    got = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    if got != CONTRACT_SHA:
        fail(f"contract_digest_mismatch: {got} != {CONTRACT_SHA}")
    if sorted(art) != sorted(ALLOWED):
        fail(f"contract_table_set_mismatch: {sorted(art)}")

    # ---- task 2: pre-flight, before ANY write ---------------------------------
    checks = {}
    for t in ORDER:
        pf = ART_DIR / f"{t}.payload.tsv"
        d = hashlib.sha256(pf.read_bytes()).hexdigest()
        if d != ALLOWED[t]["payload_sha"]:
            fail(f"payload_digest_mismatch[{t}]: {d} != {ALLOWED[t]['payload_sha']}")
        n = len(pf.read_bytes().decode().splitlines())
        if n != ALLOWED[t]["rows"]:
            fail(f"payload_line_count_mismatch[{t}]: {n} != {ALLOWED[t]['rows']}")
        checks[f"payload:{t}"] = {"sha256": d, "lines": n, "ok": True}
        if art[t]["source_canonical_sha256"] != ADJUDICATED[t]:
            fail(f"adjudicated_digest_drift[{t}]")

    s = L.PsqlSession(["psql", "-X", "-q", "-tA", "--csv", "-v", "ON_ERROR_STOP=1",
                       "-h", host, "-p", EXPECT_PORT, "-U", EXPECT_ROLE, "-d", EXPECT_DBNAME],
                      env=env)
    db = s.query_csv("SELECT current_database()").strip()
    port = s.query_csv("SHOW port").strip()
    role = s.query_csv("SELECT current_user").strip()
    marker = s.query_csv("SELECT instance_id FROM public.xrg_instance_marker LIMIT 1").strip()
    if db != EXPECT_DBNAME:
        fail(f"dbname_mismatch: {db}")
    if port != EXPECT_PORT:
        fail(f"port_mismatch: {port}")
    if role != EXPECT_ROLE:
        fail(f"role_mismatch: {role}")
    checks["connection"] = {"dbname": db, "port": port, "role": role,
                            "instance_marker": marker, "ok": True}

    for t in ORDER:
        tb = art[t]["target_table"]
        rel = qrel(art[t]["target_schema"], tb, "preflight-absent")
        present = s.query_csv("SELECT coalesce(to_regclass('%s.%s')::text,'ABSENT')"
                              % (art[t]["target_schema"], tb)).strip()
        if "ABSENT" not in present:
            fail(f"target_already_present[{t}]: {present}")
        checks[f"absent:{tb}"] = {"state": present, "ok": True}

    print(json.dumps({"phase": "preflight", "outcome": "PASSED",
                      "checks": checks}, ensure_ascii=False))

    # ---- task 3: ONE transaction for all three -------------------------------
    sent = []
    s.begin()
    try:
        for t in ORDER:
            e = art[t]
            sql = ddl_for_target(e)
            sent.append(sql)
            s.execute(sql)
            rel = qrel(e["target_schema"], e["target_table"], "copy")
            data = (ART_DIR / f"{t}.payload.tsv").read_bytes()
            s.copy_from(rel, data)
            if case == "B":
                # inject a REAL database error after >=1 table has been written
                s.execute('INSERT INTO %s ("%s") VALUES (1),(1)'
                          % (rel, e["primary_key"]["columns_in_order"][0]))
                fail("case_B_expected_no_commit")
        counts = {}
        for t in ORDER:
            e = art[t]
            rel = qrel(e["target_schema"], e["target_table"], "count")
            n = int(s.query_csv("SELECT count(*) FROM %s" % rel).strip())
            counts[t] = n
            if n != ALLOWED[t]["rows"]:
                fail(f"row_count_mismatch[{t}]: {n} != {ALLOWED[t]['rows']}")
        s.commit()
        outcome = "COMMITTED"
        err = None
    except Exception as ex:                       # noqa: BLE001
        s.rollback()
        outcome = "ROLLED_BACK"
        err = str(ex)[:200]
        counts = {}

    print(json.dumps({"phase": "load", "case": case, "outcome": outcome,
                      "pre_commit_counts": counts, "error": err,
                      "statements_sent": len(sent),
                      "create_schema_emitted": any("CREATE SCHEMA" in x.upper() for x in sent)},
                     ensure_ascii=False))

    # ---- independent readback through a FRESH session ------------------------
    r = L.PsqlSession(["psql", "-X", "-q", "-tA", "--csv", "-h", host, "-p", EXPECT_PORT,
                       "-U", EXPECT_ROLE, "-d", EXPECT_DBNAME], env=env)
    ok = True
    detail = {}
    for t in ORDER:
        e = art[t]
        tb = e["target_table"]
        reg = r.query_csv("SELECT coalesce(to_regclass('%s.%s')::text,'ABSENT')"
                          % (e["target_schema"], tb)).strip()
        if case == "B":
            gone = "ABSENT" in reg
            detail[t] = {"absent_after_rollback": gone}
            ok &= gone
            continue
        if "ABSENT" in reg:
            detail[t] = {"present": False}
            ok = False
            continue
        rel = qrel(e["target_schema"], tb, "readback")
        sel = ", ".join('"%s"' % c["target_column"] for c in e["columns"])
        rows = r.query_rows("SELECT %s FROM %s" % (sel, rel))
        cols = tuple(UnorderedColumn(source_ordinal=i, column_key=c["column_identity"],
                                     pg_type=c["pg_type"], allow_null_value=c["nullable"])
                     for i, c in enumerate(e["columns"]))
        sch = UnorderedSchema(source_object_id=e["source_object_id"], columns=cols)
        vals = []
        for row in rows:
            v = []
            for i, c in enumerate(e["columns"]):
                x = row[i] if i < len(row) else ""
                if x == "" or x is None:
                    v.append(None)
                elif c["pg_type"] == "bigint":
                    v.append(int(x))
                else:
                    v.append(x)
            vals.append(tuple(v))
        dig = canon_digest(sch, vals, e["columns"], len(vals))
        match = dig == ADJUDICATED[t]
        pk = r.query_csv("SELECT a.attname FROM pg_index i JOIN pg_attribute a "
                         "ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey) "
                         "WHERE i.indisprimary AND i.indrelid='%s.%s'::regclass "
                         "ORDER BY array_position(i.indkey, a.attnum)"
                         % (e["target_schema"], tb)).strip()
        nn = r.query_csv("SELECT string_agg(column_name,','ORDER BY ordinal_position) "
                         "FROM information_schema.columns WHERE table_schema='%s' "
                         "AND table_name='%s' AND is_nullable='NO'"
                         % (e["target_schema"], tb)).strip()
        good = (len(rows) == ALLOWED[t]["rows"] and match
                and pk == ",".join(e["primary_key"]["columns_in_order"]))
        detail[t] = {"rows": len(rows), "expect": ALLOWED[t]["rows"],
                     "canonical_db": dig, "matches_adjudicated": match,
                     "pk": pk, "notnull_cols": nn, "ok": good}
        ok &= good
    print(json.dumps({"phase": "readback", "case": case, "detail": detail,
                      "verdict": "PASS" if ok else "FAIL"}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        rc = main()
    except GateError as ge:
        print(json.dumps({"phase": "gate", "outcome": "REFUSED", "reason": str(ge)},
                         ensure_ascii=False))
        sys.exit(4)
    except Exception as ex:                       # noqa: BLE001
        print(json.dumps({"phase": "error", "outcome": "ERROR", "detail": str(ex)[:300]},
                         ensure_ascii=False))
        sys.exit(3)
    sys.exit(rc)

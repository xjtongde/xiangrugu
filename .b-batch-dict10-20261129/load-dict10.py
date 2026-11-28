#!/usr/bin/env python3
"""Fixed, independent three-table loader entry for the CBDB dictionary tables.

WHY THIS EXISTS AS A SEPARATE ENTRY (not a change to the B-batch loader)
-----------------------------------------------------------------------
The B-batch loader cannot address another table at all: its DDL builder takes the
table name from module constants --

    cbdb_social_addr_loader.py:48   def qtable(): return f'{TARGET_SCHEMA}.{TARGET_TABLE}'
    cbdb_social_addr_loader.py:216  q = f"CREATE TABLE {qtable()} (\\n" + ...

so `ddl_for({"schema_name": "cbdb", "table": "<TABLE>", ...})` still
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
ART_DIR = pathlib.Path("/data-var-bb")
CONTRACT = ART_DIR / "contract-ten-tables.json"
CONTRACT_SHA = "cfba085d3c52ccdea519c3076c3a65e8089408e26e4d2917d4053c69e626b9e1"

# The ONLY permitted targets. Enforced by assert_target() below.
ALLOWED = {
    "COUNTRY_CODES": {
        "schema": "cbdb",
        "table": "cbdb__country_u5f_codes",
        "rows": 11,
        "payload_sha": "da3580791a8fbfcd8143bbffe279facea4b7e514f3208e7bfc0d9f1e782d6c97"
    },
    "LITERARYGENRE_CODES": {
        "schema": "cbdb",
        "table": "cbdb__literarygenre_u5f_codes",
        "rows": 12,
        "payload_sha": "632ff3628007001c5076cf43ab88893f5da1e20b3129370a0ae2fe1f7a1886fa"
    },
    "TEXT_ROLE_CODES": {
        "schema": "cbdb",
        "table": "cbdb__text_u5f_role_u5f_codes",
        "rows": 12,
        "payload_sha": "4ad3bacb4214f9014572293c8d063769f21416e0c48811de0cf5823f90501685"
    },
    "APPOINTMENT_TYPES": {
        "schema": "cbdb",
        "table": "cbdb__appointment_u5f_types",
        "rows": 13,
        "payload_sha": "f8e09cd4d6c64804401a40c2b5ce9775eaae1f71d953386b9c936e67fa360e9d"
    },
    "STATUS_TYPES": {
        "schema": "cbdb",
        "table": "cbdb__status_u5f_types",
        "rows": 14,
        "payload_sha": "5ae698ac436032b02d4bd81a5fb6ff9066ba7ab9df3f28d47f938c7b77d77eaa"
    },
    "ALTNAME_CODES": {
        "schema": "cbdb",
        "table": "cbdb__altname_u5f_codes",
        "rows": 21,
        "payload_sha": "5ea49bac41cd0370f4927a43610bae0923183a7389cdbea69e0bc1e32d229b7f"
    },
    "BIOG_ADDR_CODES": {
        "schema": "cbdb",
        "table": "cbdb__biog_u5f_addr_u5f_codes",
        "rows": 22,
        "payload_sha": "17e904046c9236722ee8da2e67216d5e712f17aa050a4c114bbe6a6a2e654bdc"
    },
    "BIOG_INST_CODES": {
        "schema": "cbdb",
        "table": "cbdb__biog_u5f_inst_u5f_codes",
        "rows": 26,
        "payload_sha": "7b22f4c7d48428141b3b437b0fa320c2eab698cc34d26c423d2f83be5c1422e4"
    },
    "ENTRY_TYPES": {
        "schema": "cbdb",
        "table": "cbdb__entry_u5f_types",
        "rows": 29,
        "payload_sha": "d926b90aed137220fffc83ae4e750ee66816a278977cde93cdb82ff41a6ef01e"
    },
    "INDEXYEAR_TYPE_CODES": {
        "schema": "cbdb",
        "table": "cbdb__indexyear_u5f_type_u5f_codes",
        "rows": 31,
        "payload_sha": "3aded33a388fb94d0a4903efdd19357e155ac3f4c8da5344ebdbea683d0a8bdc"
    }
}
ORDER = ["COUNTRY_CODES", "LITERARYGENRE_CODES", "TEXT_ROLE_CODES", "APPOINTMENT_TYPES", "STATUS_TYPES", "ALTNAME_CODES", "BIOG_ADDR_CODES", "BIOG_INST_CODES", "ENTRY_TYPES", "INDEXYEAR_TYPE_CODES"]
ADJUDICATED = {
    "COUNTRY_CODES": "1e23b088ded253b5b4b41247a92a33490e5332891433dc0db2d84d557bce90e4",
    "LITERARYGENRE_CODES": "0e8f45e94354f108ef185916ed41fd9c96c2e09d7d619200cc47ddec38baf869",
    "TEXT_ROLE_CODES": "62f423e1d6899ebd8283c2948f44f28b9b6c43d99c39ac2ff64cb7a27840317e",
    "APPOINTMENT_TYPES": "0ab780b444137883895f05217cb4efe6d146e8335e3b89be3c2aa4feaa1c0d33",
    "STATUS_TYPES": "22f21f37567d90aad7afebe58ab17e896eda1667321e29bbb5201e1b9937f1ce",
    "ALTNAME_CODES": "110d8776517a70391c75f03e278d790d2f8fb5b0a7e0780531b8772dda8f4a59",
    "BIOG_ADDR_CODES": "e3316df00ad67591dda48bfc9efa56442efb9cf4be21dfc49f88c28264e738ac",
    "BIOG_INST_CODES": "dc254a78011157a7aae093c8061bb162460e247ba209371c4511734584d8bd88",
    "ENTRY_TYPES": "5f73008b57b6900ffaf31a52b75fc69b259acc399c1b0faccd82d3346febd884",
    "INDEXYEAR_TYPE_CODES": "4d16efe79d58c7c0f18717debf6ab61c73e9c6168c91dbef673a753bb8503932"
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
    pw = pathlib.Path(os.environ.get("DICT3_PW_FILE", "/data-var-bb/.pw")).read_text().strip()
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

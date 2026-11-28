#!/usr/bin/env python3
"""PRODUCTION entry: load the three CBDB dictionary tables into pg32b:5433/xiangrugu.

PHYSICALLY SEPARATE from the isolation harness (load-dict3.py). Deliberately:

  * NO host / dbname / port argument -- the endpoint is hardcoded below and there is no
    CLI surface that can move it. A wrong-instance run is structurally impossible to
    request, not merely discouraged by documentation.
  * NO rollback / fail-after / corrupt / dry-run-injection switch. The only mode flag is
    --preflight-only, which stops BEFORE any DDL and performs no writes; it cannot be
    used to "test a rollback" against production because it never reaches the write path.
  * Does NOT import load-dict3.py, so none of the isolation injection logic is on this
    execution path.

Pre-flight runs INSIDE THE SAME SESSION that will execute the DDL -- a check performed on
a different connection proves nothing about the one that writes. Any mismatch aborts with
a non-zero exit before a single statement is sent.
"""
import argparse
import hashlib
import json
import pathlib
import sys

sys.path.insert(0, "/app/datamgmt/src")
from xiangrugu_datamgmt import cbdb_social_addr_loader as L  # noqa: E402
from xiangrugu_datamgmt.unordered_values import (  # noqa: E402
    UnorderedSchema, UnorderedColumn, UnorderedLimits,
    header_bytes, trailer_bytes, encode_unordered_row)

# ------------------------------------------------------------------ fixed endpoint
# Hardcoded on purpose: the formal entry must not accept an arbitrary instance.
CONNECT_HOST = "pg32b"
CONNECT_PORT = 5433          # host-32 published port for the target instance
IN_SESSION_PORT = "5432"     # what SHOW port must report inside the session
DBNAME = "xiangrugu"
LOAD_ROLE = "xrg_loader"
INSTANCE_MARKER = "3d93fc7741f66f1f01aa250b25c4959addfe4c84df22ecbd0d0f82c13920c1fc"

ART_DIR = pathlib.Path("/data/var/b-batch/dict3")
CONTRACT = ART_DIR / "contract-three-tables.json"
CONTRACT_SHA = "12789a6c7aa0ed82e27cd1457a5d6a97f620d5d7307298eabe2399187fd4b4f7"

ALLOWED = {
    "EXTANT_CODES":         ("cbdb", "cbdb__extant_u5f_codes", 4,
                             "132686c3cf0a67c5c80e776034fc73315bff991d3b5fcf49d3bba3059ef86b8e"),
    "POSSESSION_ACT_CODES": ("cbdb", "cbdb__possession_u5f_act_u5f_codes", 4,
                             "52d9b446a42042e805bca18685488bbf8072a19a288e29c05e27bf8abd480dd1"),
    "ASSUME_OFFICE_CODES":  ("cbdb", "cbdb__assume_u5f_office_u5f_codes", 6,
                             "b9e490d409fcac80273e42ece76052b9cdf48638d88cd046f8bafedde167f84f"),
}
ORDER = ["EXTANT_CODES", "POSSESSION_ACT_CODES", "ASSUME_OFFICE_CODES"]
ADJUDICATED = {
    "EXTANT_CODES":         "2e6c0057fde56ea147f05365c47157eb37d41869f375a19b75d06b3dc3c990c2",
    "POSSESSION_ACT_CODES": "95df512964fa910a1ade063b966c64ad586c4778b6f410ad70358849040318d8",
    "ASSUME_OFFICE_CODES":  "08d7e819d52a34082505cbac6ee98a0bdaf7e8fefed7a3d7fa76a1f874b23f95",
}


class Refused(Exception):
    def __init__(self, code, detail=""):
        self.code, self.detail = code, detail
        super().__init__(code)


def assert_target(schema, table, ctx):
    if schema != "cbdb":
        raise Refused(f"whitelist_violation[{ctx}]", f"schema {schema!r} != 'cbdb'")
    if table not in {v[1] for v in ALLOWED.values()}:
        raise Refused(f"whitelist_violation[{ctx}]", f"table {table!r} not allowlisted")
    if not all(c.isalnum() or c == "_" for c in table):
        raise Refused(f"identifier_check[{ctx}]", f"unsafe identifier {table!r}")


def qrel(schema, table, ctx):
    assert_target(schema, table, ctx)
    return f'"{schema}"."{table}"'


def ddl_for_target(e):
    defs = ['  "%s" %s%s' % (c["target_column"], c["pg_type"],
                             "" if c["nullable"] else " NOT NULL") for c in e["columns"]]
    defs.append("  PRIMARY KEY (%s)" % ", ".join(
        '"%s"' % c for c in e["primary_key"]["columns_in_order"]))
    sql = "CREATE TABLE %s (\n" % qrel(e["target_schema"], e["target_table"], "ddl") \
        + ",\n".join(defs) + "\n);"
    if "CREATE SCHEMA" in sql.upper():
        raise Refused("schema_creation_forbidden", "built DDL contains CREATE SCHEMA")
    return sql


def canon(sch, rows, n):
    lim = UnorderedLimits()
    h = hashlib.sha256()
    h.update(header_bytes(sch))
    for f in sorted(encode_unordered_row(sch, tuple(r), limits=lim) for r in rows):
        h.update(f)
    h.update(trailer_bytes(n))
    return h.hexdigest()


def column_schema(e):
    cols = tuple(UnorderedColumn(source_ordinal=i, column_key=c["column_identity"],
                                 pg_type=c["pg_type"], allow_null_value=c["nullable"])
                 for i, c in enumerate(e["columns"]))
    return UnorderedSchema(source_object_id=e["source_object_id"], columns=cols)


def preflight(session, art):
    """Six checks, executed IN THIS SESSION, before any DDL."""
    obs = {}
    db = session.query_csv("SELECT current_database()").strip()
    obs["current_database"] = db
    if db != DBNAME:
        raise Refused("target_database_mismatch", db)

    port = session.query_csv("SHOW port").strip()
    obs["in_session_port"] = port
    if port != IN_SESSION_PORT:
        raise Refused("in_session_port_mismatch", port)

    su = session.query_csv("SELECT session_user").strip()
    cu = session.query_csv("SELECT current_user").strip()
    obs["session_user"], obs["current_user"] = su, cu
    if su != LOAD_ROLE or cu != LOAD_ROLE:
        raise Refused("role_mismatch", f"session_user={su} current_user={cu}")

    sup = session.query_csv(
        "SELECT rolsuper::int FROM pg_roles WHERE rolname = current_user").strip()
    obs["superuser_flag"] = sup
    if sup != "0":
        raise Refused("role_is_superuser", sup)

    mk = session.query_csv(
        "SELECT count(*) FROM public.xrg_instance_marker").strip()
    obs["marker_rows"] = int(mk)
    if mk != "1":
        raise Refused("instance_marker_not_exactly_one_row", mk)
    val = session.query_csv(
        "SELECT instance_id FROM public.xrg_instance_marker").strip()
    obs["instance_marker"] = val
    if val != INSTANCE_MARKER:
        raise Refused("instance_marker_mismatch", val)

    for t in ORDER:
        sch, tb = art[t]["target_schema"], art[t]["target_table"]
        reg = session.query_csv("SELECT coalesce(to_regclass('%s.%s')::text,'ABSENT')"
                                % (sch, tb)).strip()
        obs[f"absent:{tb}"] = reg
        if "ABSENT" not in reg:
            raise Refused("target_already_present", f"{t}: {reg}")
    return obs


def main():
    ap = argparse.ArgumentParser(description="Formal three-table dictionary loader")
    # ONLY this flag. No --host/--dbname/--port/--rollback/--fail-after by design.
    ap.add_argument("--preflight-only", action="store_true",
                    help="run the six pre-flight checks then stop BEFORE any DDL (no writes)")
    args = ap.parse_args()

    pw = pathlib.Path("/secrets/xrg_loader_password").read_text().strip()
    import os
    env = dict(os.environ, PGPASSWORD=pw)

    raw = CONTRACT.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != CONTRACT_SHA:
        print(json.dumps({"outcome": "REFUSED", "error_code": "contract_digest_mismatch",
                          "detail": got}, ensure_ascii=False))
        return 2
    art = json.loads(raw)["tables"]
    if sorted(art) != sorted(ALLOWED):
        print(json.dumps({"outcome": "REFUSED", "error_code": "contract_table_set_mismatch"},
                         ensure_ascii=False))
        return 2

    # payload digests over the ACTUAL bytes we are about to feed to COPY
    blobs = {}
    for t in ORDER:
        b = (ART_DIR / f"{t}.payload.tsv").read_bytes()
        d = hashlib.sha256(b).hexdigest()
        if d != ALLOWED[t][3]:
            print(json.dumps({"outcome": "REFUSED",
                              "error_code": f"payload_digest_mismatch:{t}",
                              "detail": d}, ensure_ascii=False))
            return 2
        if len(b.decode().splitlines()) != ALLOWED[t][2]:
            print(json.dumps({"outcome": "REFUSED",
                              "error_code": f"payload_line_count_mismatch:{t}"},
                             ensure_ascii=False))
            return 2
        blobs[t] = b

    session = L.PsqlSession(["psql", "-X", "-q", "-tA", "--csv", "-v", "ON_ERROR_STOP=1",
                             "-h", CONNECT_HOST, "-p", str(CONNECT_PORT),
                             "-U", LOAD_ROLE, "-d", DBNAME], env=env)
    try:
        obs = preflight(session, art)
    except Refused as r:
        print(json.dumps({"outcome": "REFUSED_BEFORE_ANY_DDL", "error_code": r.code,
                          "detail": r.detail, "observed": obs if 'obs' in dir() else None},
                         ensure_ascii=False))
        return 2

    print(json.dumps({"phase": "preflight", "outcome": "PASSED", "observed": obs,
                      "endpoint": {"connect_host": CONNECT_HOST, "connect_port": CONNECT_PORT,
                                   "dbname": DBNAME, "role": LOAD_ROLE}},
                     ensure_ascii=False))

    if args.preflight_only:
        print(json.dumps({"phase": "stop", "mode": "preflight_only",
                          "writes_performed": False, "outcome": "NO_WRITE_PREFLIGHT_OK"},
                         ensure_ascii=False))
        return 0

    sent = []
    session.begin()
    try:
        for t in ORDER:
            sql = ddl_for_target(art[t])
            sent.append(sql)
            session.execute(sql)
            session.copy_from(qrel(art[t]["target_schema"], art[t]["target_table"], "copy"),
                              blobs[t])
        counts = {}
        for t in ORDER:
            n = int(session.query_csv("SELECT count(*) FROM %s" % qrel(
                art[t]["target_schema"], art[t]["target_table"], "count")).strip())
            counts[t] = n
            if n != ALLOWED[t][2]:
                raise Refused(f"row_count_mismatch:{t}", str(n))
        session.commit()
        print(json.dumps({"phase": "load", "outcome": "COMMITTED",
                          "pre_commit_counts": counts, "statements_sent": len(sent),
                          "create_schema_emitted": any("CREATE SCHEMA" in s.upper() for s in sent)},
                         ensure_ascii=False))
        return 0
    except Exception as ex:                       # noqa: BLE001
        session.rollback()
        print(json.dumps({"phase": "load", "outcome": "ROLLED_BACK",
                          "error": str(ex)[:200]}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())

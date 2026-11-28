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

ART_DIR = pathlib.Path("/data/var/b-batch/dict10")
CONTRACT = ART_DIR / "contract-ten-tables.json"
CONTRACT_SHA = "cfba085d3c52ccdea519c3076c3a65e8089408e26e4d2917d4053c69e626b9e1"

ALLOWED = {
    "COUNTRY_CODES": [
        "cbdb",
        "cbdb__country_u5f_codes",
        11,
        "da3580791a8fbfcd8143bbffe279facea4b7e514f3208e7bfc0d9f1e782d6c97"
    ],
    "LITERARYGENRE_CODES": [
        "cbdb",
        "cbdb__literarygenre_u5f_codes",
        12,
        "632ff3628007001c5076cf43ab88893f5da1e20b3129370a0ae2fe1f7a1886fa"
    ],
    "TEXT_ROLE_CODES": [
        "cbdb",
        "cbdb__text_u5f_role_u5f_codes",
        12,
        "4ad3bacb4214f9014572293c8d063769f21416e0c48811de0cf5823f90501685"
    ],
    "APPOINTMENT_TYPES": [
        "cbdb",
        "cbdb__appointment_u5f_types",
        13,
        "f8e09cd4d6c64804401a40c2b5ce9775eaae1f71d953386b9c936e67fa360e9d"
    ],
    "STATUS_TYPES": [
        "cbdb",
        "cbdb__status_u5f_types",
        14,
        "5ae698ac436032b02d4bd81a5fb6ff9066ba7ab9df3f28d47f938c7b77d77eaa"
    ],
    "ALTNAME_CODES": [
        "cbdb",
        "cbdb__altname_u5f_codes",
        21,
        "5ea49bac41cd0370f4927a43610bae0923183a7389cdbea69e0bc1e32d229b7f"
    ],
    "BIOG_ADDR_CODES": [
        "cbdb",
        "cbdb__biog_u5f_addr_u5f_codes",
        22,
        "17e904046c9236722ee8da2e67216d5e712f17aa050a4c114bbe6a6a2e654bdc"
    ],
    "BIOG_INST_CODES": [
        "cbdb",
        "cbdb__biog_u5f_inst_u5f_codes",
        26,
        "7b22f4c7d48428141b3b437b0fa320c2eab698cc34d26c423d2f83be5c1422e4"
    ],
    "ENTRY_TYPES": [
        "cbdb",
        "cbdb__entry_u5f_types",
        29,
        "d926b90aed137220fffc83ae4e750ee66816a278977cde93cdb82ff41a6ef01e"
    ],
    "INDEXYEAR_TYPE_CODES": [
        "cbdb",
        "cbdb__indexyear_u5f_type_u5f_codes",
        31,
        "3aded33a388fb94d0a4903efdd19357e155ac3f4c8da5344ebdbea683d0a8bdc"
    ]
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

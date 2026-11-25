"""First-batch seven-object PG loader candidate (stdlib-only).

One entry for isolated tests and the 32 temporary-instance trial. Gates run
BEFORE any write: scope approval, contract/evidence digest bindings, target
instance identity, target-already-exists (fail closed, never overwrite). The
load itself is ONE transaction: BEGIN -> schemas/extension/DDL/COPY x7 ->
full readback verification inside the transaction -> COMMIT only when every
count/column/digest/duplicate expectation matches; any failure ROLLBACKs so
no half-batch data survives. Retry re-runs all gates; nothing is overwritten.

This candidate never flips the global ready_for_import gate: the full
inventory stays ready_for_import=false with 7995 uncovered members. Scope
approval here is isolated-test-only, not a production load authorization.
"""
import csv
import hashlib
import io
import struct
import subprocess
import threading

from . import canonical

FIRST_BATCH_RULES = ("m002709", "m002717", "m004812", "m006642", "m008002", "m008003", "m008004")
ROWNUM = "__src_rownum"


class LoaderGateError(Exception):
    def __init__(self, code, message=""):
        self.code = code
        super().__init__(f"{code}: {message}" if message else code)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def validate_scope(scope, presented):
    """Gate 1: independent first-batch scope approval + digest bindings."""
    for key in ("version", "scope_id", "mode", "approval", "contract_sha256",
                "inventory_sha256", "writeoff_evidence_sha256", "objects",
                "full_ready_for_import", "uncovered_members"):
        if key not in scope:
            raise LoaderGateError("scope_field_missing", key)
    ap = scope["approval"]
    if not all(isinstance(ap.get(k), str) and ap.get(k) for k in ("approved_by", "approved_at", "approval_ref")):
        raise LoaderGateError("approval_missing")
    if scope["mode"] != "isolated-test":
        raise LoaderGateError("scope_mode_not_isolated_test")
    if scope["full_ready_for_import"] is not False:
        raise LoaderGateError("full_ready_gate_flipped")
    if scope["uncovered_members"] != 7995:
        raise LoaderGateError("uncovered_count_drift")
    if scope["contract_sha256"] != presented["contract_sha256"]:
        raise LoaderGateError("contract_digest_mismatch")
    if scope["inventory_sha256"] != presented["inventory_sha256"]:
        raise LoaderGateError("inventory_digest_mismatch")
    for k in ("nul", "chgis"):
        if scope["writeoff_evidence_sha256"].get(k) != presented["evidence_shas"].get(k):
            raise LoaderGateError("writeoff_evidence_digest_mismatch", k)
    if sorted(o["rule_id"] for o in scope["objects"]) != sorted(FIRST_BATCH_RULES):
        raise LoaderGateError("scope_objects_not_first_batch_seven")
    for o in scope["objects"]:
        t = presented["targets"].get(o["rule_id"])
        if t is None or (o["schema_name"], o["table"]) != (t["schema_name"], t["table"]):
            raise LoaderGateError("scope_object_identity_mismatch", o["rule_id"])


def check_instance_identity(observed, expected):
    """Gate 2: the connected instance must be the approved temporary one."""
    if "pg32b" in observed.get("databases", "") or "cbdb" in observed.get("databases", ""):
        raise LoaderGateError("production_database_visible")
    for key in ("container_id", "image_id", "server_version", "inet_server_addr", "databases"):
        if observed.get(key) != expected.get(key):
            raise LoaderGateError("instance_identity_mismatch", key)


def ddl_for(rule):
    t = rule["targets"][0]
    defs = []
    for c in t["columns"]:
        null = "" if c["nullable"] else " NOT NULL"
        defs.append(f'{c["target_column"]} {c["pg_type"]}{null}')
    if t.get("geometry"):
        defs.append("geom geometry(Point,4326) NOT NULL")
    defs.append(f"{ROWNUM} bigint NOT NULL PRIMARY KEY")
    return f'CREATE TABLE {_schema(t)}.{t["table"]} (' + ", ".join(defs) + ")"


def _schema(t):
    return t.get("schema_name", t.get("schema"))


def targets_of(contract):
    return {r["rule_id"]: dict(r["targets"][0], schema_name=_schema(r["targets"][0]))
            for r in contract["rules"] if r["rule_id"] in FIRST_BATCH_RULES}


def check_targets_absent(session, contract):
    """Gate 3: any existing target table refuses the whole batch (no overwrite)."""
    names = [f'{_schema(t)}.{t["table"]}' for t in targets_of(contract).values()]
    sql = "SELECT coalesce(string_agg(n, ',' ORDER BY n), '') FROM (SELECT unnest(ARRAY[" \
        + ",".join("'" + n + "'" for n in names) + "]) AS n) s WHERE to_regclass(n) IS NOT NULL"
    rows = _rows_csv(session.query_csv(sql))
    existing = rows[0][0] if rows and rows[0] else ""
    if existing:
        raise LoaderGateError("target_already_exists", existing)


def _rows_csv(text):
    return list(csv.reader(io.StringIO(text)))


def _text_stream(sid, contract_rule, db_rows):
    t = contract_rule["targets"][0]
    cols = tuple(canonical.ValueColumn(column_key=c["source_column"], target_name=c["target_column"],
                                       pg_type=c["pg_type"], nullable=c["nullable"]) for c in t["columns"]) \
        + (canonical.ValueColumn(column_key=canonical.ROW_KEY,
                                 target_name=t["derived_rownum"]["target_column"], pg_type="bigint", nullable=False),)
    schema = canonical.ValueSchema(source_object_id=sid, columns=cols)
    n = len(t["columns"])
    rows = [tuple(r[:n]) for r in db_rows]
    return canonical.summarize_rows(schema, (tuple(r) + (i + 1,) for i, r in enumerate(rows)),
                                    limits=canonical.ValueLimits())


def _geom_stream(sid, points):
    out = bytearray(b"XRGGEOM\x00\x01" + bytes.fromhex(sid) + struct.pack(">ib", 4326, 2))
    for p in points:
        out += b"\x52" + struct.pack(">Q", p["rownum"]) + bytes.fromhex(p["x_bytes"]) + bytes.fromhex(p["y_bytes"])
    out += b"\x45" + struct.pack(">Q", len(points))
    return bytes(out)


def _reconstruct_n(db_text, field):
    from decimal import Decimal
    width, dec = field["length"], field["decimals"]
    if dec == 0:
        return str(int(Decimal(db_text))).rjust(width)
    return format(Decimal(db_text), f".{dec}f").rjust(width)


def run_first_batch(session, scope, contract, payloads, instance_observed, expected):
    """Single entry: gates -> one transaction -> readback -> COMMIT/ROLLBACK."""
    validate_scope(scope, {"contract_sha256": expected["contract_sha256"],
                           "inventory_sha256": expected["inventory_sha256"],
                           "evidence_shas": expected["evidence_shas"],
                           "targets": targets_of(contract)})
    check_instance_identity(instance_observed, expected["instance_identity"])
    check_targets_absent(session, contract)
    return _load_and_verify(session, contract, payloads, expected, create_prerequisites=True)


def _load_and_verify(session, contract, payloads, expected, create_prerequisites):
    """Shared single-transaction body: DDL+COPY x7 -> in-transaction readback -> COMMIT/ROLLBACK."""
    rules = {r["rule_id"]: r for r in contract["rules"] if r["rule_id"] in FIRST_BATCH_RULES}
    evidence = {"gates": ["scope_approval", "digest_bindings", "instance_identity", "targets_absent"],
                "transaction": "single", "items": {}}
    session.begin()
    committed = False
    try:
        if create_prerequisites:
            session.execute("CREATE SCHEMA IF NOT EXISTS harv; CREATE SCHEMA IF NOT EXISTS chgis; "
                            "CREATE EXTENSION IF NOT EXISTS postgis")
        for rid in FIRST_BATCH_RULES:
            t = rules[rid]["targets"][0]
            session.execute(ddl_for(rules[rid]))
            session.copy_from(f'{_schema(t)}.{t["table"]}', payloads[rid])
        total = 0
        for rid in FIRST_BATCH_RULES:
            rule, t = rules[rid], rules[rid]["targets"][0]
            exp = expected["items"][rid]
            table = f'{_schema(t)}.{t["table"]}'
            nc = len(t["columns"])
            sel = ", ".join(c["target_column"] for c in t["columns"])
            if t.get("geometry"):
                sel += ", ST_X(geom), ST_Y(geom), GeometryType(geom), ST_NDims(geom), ST_SRID(geom)"
            sel += f", {ROWNUM}"
            recs = _rows_csv(session.query_csv(f"SELECT {sel} FROM {table} ORDER BY {ROWNUM}"))
            meta = _rows_csv(session.query_csv(
                "SELECT column_name, data_type, udt_name, is_nullable, ordinal_position "
                "FROM information_schema.columns "
                f"WHERE table_schema='{_schema(t)}' AND table_name='{t['table']}' ORDER BY ordinal_position"))
            valcols = ", ".join(c["target_column"] for c in t["columns"])
            dup_groups = session.query_csv(
                f"SELECT count(*) FROM (SELECT {valcols} FROM {table} GROUP BY {valcols} HAVING count(*)>1) d").strip()
            dup_extra = session.query_csv(
                f"SELECT coalesce(sum(c)-count(*),0) FROM (SELECT count(*) c FROM {table} GROUP BY {valcols} HAVING count(*)>1) d").strip()
            item = {"row_count": len(recs), "row_count_match": len(recs) == exp["row_count"],
                    "columns_meta_match": meta == exp["meta"],
                    "duplicate_groups": int(dup_groups), "duplicate_extra_rows": int(dup_extra),
                    "duplicates_match": (int(dup_groups), int(dup_extra)) == (exp["dup_groups"], exp["dup_extra"])}
            if t.get("geometry"):
                fields = exp["fields"]
                rebuilt, points, geom_meta_ok = [], [], True
                for rec in recs:
                    vals = list(rec[:nc])
                    for j, f in enumerate(fields):
                        if f["type"] == "N":
                            vals[j] = _reconstruct_n(rec[j], f)
                    rebuilt.append(tuple(vals))
                    points.append({"rownum": int(rec[nc + 5]),
                                   "x_bytes": struct.pack("<d", float(rec[nc])).hex(),
                                   "y_bytes": struct.pack("<d", float(rec[nc + 1])).hex()})
                    geom_meta_ok &= (rec[nc + 2] == "POINT" and rec[nc + 3] == "2" and rec[nc + 4] == "4326")
                attr_cols = tuple(canonical.ValueColumn(column_key=c["column_id"], target_name=c["target_name"],
                                                        pg_type="text", nullable=False)
                                  for c in exp["attr_columns"]) \
                    + (canonical.ValueColumn(column_key=canonical.ROW_KEY, target_name=ROWNUM,
                                             pg_type="bigint", nullable=False),)
                attr_schema = canonical.ValueSchema(source_object_id=exp["source_object_id"], columns=attr_cols)
                s = canonical.summarize_rows(attr_schema, (tuple(r) + (i + 1,) for i, r in enumerate(rebuilt)),
                                             limits=canonical.ValueLimits())
                gs = _geom_stream(exp["source_object_id"], points)
                item.update({"attr_sha256": s.sha256, "attr_sha_match": s.sha256 == exp["attr_sha"],
                             "geom_sha256": sha(gs), "geom_sha_match": sha(gs) == exp["geom_sha"],
                             "geom_meta_ok": geom_meta_ok,
                             "xy_bytes_match": all(points[i]["x_bytes"] == exp["points"][i]["x_bytes"]
                                                   and points[i]["y_bytes"] == exp["points"][i]["y_bytes"]
                                                   for i in range(len(points)))})
                ok = (item["row_count_match"] and item["columns_meta_match"] and item["duplicates_match"]
                      and item["attr_sha_match"] and item["geom_sha_match"] and geom_meta_ok and item["xy_bytes_match"])
            else:
                s = _text_stream(exp["source_object_id"], rule, recs)
                item.update({"attr_sha256": s.sha256, "attr_sha_match": s.sha256 == exp["attr_sha"],
                             "stream_bytes": s.stream_bytes})
                ok = (item["row_count_match"] and item["columns_meta_match"] and item["duplicates_match"]
                      and item["attr_sha_match"] and s.stream_bytes == exp["stream_bytes"])
            item["pass"] = ok
            evidence["items"][rid] = item
            if not ok:
                raise LoaderGateError("readback_mismatch", rid)
            total += len(recs)
        evidence["total_rows"] = total
        if total != 47725:
            raise LoaderGateError("total_row_count_mismatch", str(total))
        session.commit()
        committed = True
    except BaseException:
        if not committed:
            session.rollback()
        raise
    evidence["status"] = "FIRST_BATCH_TRIAL_LOAD_PASS"
    evidence["committed"] = True
    return evidence


class PsqlSession:
    """Persistent single psql coprocess; sentinel protocol keeps one transaction."""

    def __init__(self, cmd_prefix):
        self._p = subprocess.Popen(cmd_prefix + ["-X", "-q", "-t", "--csv", "-v", "ON_ERROR_STOP=1"],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, bufsize=1)
        self._seq = 0
        self._err = []
        self._t = threading.Thread(target=self._drain, daemon=True)
        self._t.start()

    def _drain(self):
        for line in self._p.stderr:
            self._err.append(line)

    def _sentinel(self):
        self._seq += 1
        tag = f"XRG_SENT_{self._seq}"
        self._p.stdin.write(f"SELECT '{tag}';\n")
        self._p.stdin.flush()
        lines = []
        while True:
            if self._p.poll() is not None:
                raise LoaderGateError("session_died", "".join(self._err)[-300:])
            line = self._p.stdout.readline()
            if not line:
                raise LoaderGateError("session_eof", "".join(self._err)[-300:])
            if line.rstrip("\n") == tag:
                return lines
            lines.append(line.rstrip("\n"))

    def execute(self, sql):
        self._p.stdin.write(sql.rstrip(";") + ";\n")
        self._p.stdin.flush()
        self._sentinel()

    def begin(self):
        self.execute("BEGIN")

    def commit(self):
        self.execute("COMMIT")

    def rollback(self):
        try:
            self.execute("ROLLBACK")
        except LoaderGateError:
            pass

    def copy_from(self, table, data):
        self._p.stdin.write(f"\\copy {table} FROM STDIN WITH (FORMAT csv, DELIMITER E'\\t', QUOTE '\"')\n")
        self._p.stdin.write(data)
        if not data.endswith("\n"):
            self._p.stdin.write("\n")
        self._p.stdin.write("\\.\n")
        self._p.stdin.flush()
        self._sentinel()

    def query_csv(self, sql):
        self._p.stdin.write(f"\\copy ({sql.rstrip(';')}) TO STDOUT WITH (FORMAT csv)\n")
        self._p.stdin.flush()
        return "\n".join(self._sentinel()) + ("\n" if self._seq else "")

    def close(self):
        try:
            self._p.stdin.close()
        except Exception:
            pass
        self._p.wait(timeout=30)
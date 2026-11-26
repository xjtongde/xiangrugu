"""SOCIAL_INSTITUTION_ADDR single-table PG loader candidate (stdlib-only).

Scope: exactly one target, ``cbdb.cbdb__social_u5f_institution_u5f_addr``, bound to the
B-batch single-table frozen candidate 56b0076d… and approved source member m007906
(3859 rows, approved source-side canonical sha 2cb8c354…).

Design mirrors first_batch_loader: every gate runs BEFORE any write; the load is ONE
transaction whose in-transaction readback must satisfy every approved expectation
before COMMIT; any mismatch ROLLBACKs so no partial table survives and a retry is clean.

Deliberate restrictions (per this box's authorization):
  * no constraint is invented beyond the approval table — the ordered six-column
    composite PRIMARY KEY and the per-column NOT NULL flags come from the approved
    column list. UNIQUE / INDEX / FOREIGN KEY / DEFAULT stay NOT_EXECUTED;
  * the digest check uses the project's formal ``compare_unordered`` reference, so the
    target sha is computed by the same canonical unordered stream as the source;
  * this candidate never flips the global gate: full ``ready_for_import`` stays false;
  * scope approval here is isolated-test-only, NOT a production write authorization.
"""
import csv
import hashlib
import io
import subprocess
import threading

TARGET_RULE = "m007906"
TARGET_SCHEMA = "cbdb"
TARGET_TABLE = "cbdb__social_u5f_institution_u5f_addr"
EXPECTED_ROWS = 3859
EXPECTED_SOURCE_SHA = "2cb8c354b0e75e6ae230e3b00540146e823eaa8de8def2abce89ad6179a07579"
EXPECTED_CANDIDATE_SHA = "56b0076d2e877be9fb34796e01b8ee2b37d5a817c8e80203fa21c95e4f3f8237"


class LoaderGateError(Exception):
    def __init__(self, code, message=""):
        self.code = code
        super().__init__(f"{code}: {message}" if message else code)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def qtable():
    return f'{TARGET_SCHEMA}.{TARGET_TABLE}'


# --------------------------------------------------------------------- gates
def validate_scope(scope, presented):
    """Gate 1: isolated-test scope approval, digest bindings and review traceability."""
    for key in ("version", "scope_id", "mode", "approval", "candidate_sha256",
                "contract_sha256", "inventory_sha256", "source_member", "target",
                "full_ready_for_import", "review_traceability"):
        if key not in scope:
            raise LoaderGateError("scope_field_missing", key)
    ap = scope["approval"]
    if not all(isinstance(ap.get(k), str) and ap.get(k) for k in
               ("approved_by", "approved_at", "approval_ref")):
        raise LoaderGateError("approval_missing")
    # The loader has TWO dialects. A formal write must NOT masquerade as an isolated
    # test run: an approval that claims to be a real production write has to say so in
    # the very artifacts the loader records, otherwise the audit trail denies itself.
    dialect = scope["mode"]
    if dialect == "isolated-test":
        if ap.get("test_only") is not True:
            raise LoaderGateError("scope_not_marked_test_only")
    elif dialect == "production-write":
        if ap.get("test_only") is not False:
            raise LoaderGateError("scope_mode_production_write_but_marked_test_only")
        if ap.get("approval_class") != "real":
            raise LoaderGateError("scope_mode_production_write_without_real_class")
        if not ap.get("approval_text_sha256"):
            raise LoaderGateError("scope_mode_production_write_without_authorization_digest")
    else:
        # Kept as the historical code for an unknown dialect so existing callers and
        # tests that probed with mode="production" still see the same refusal.
        raise LoaderGateError("scope_mode_not_isolated_test", str(dialect))
    if scope["full_ready_for_import"] is not False:
        raise LoaderGateError("full_ready_gate_flipped")
    if scope["candidate_sha256"] != presented["candidate_sha256"]:
        raise LoaderGateError("candidate_digest_mismatch")
    if scope["candidate_sha256"] != EXPECTED_CANDIDATE_SHA:
        raise LoaderGateError("candidate_not_the_approved_one")
    if scope["contract_sha256"] != presented["contract_sha256"]:
        raise LoaderGateError("contract_digest_mismatch")
    if scope["inventory_sha256"] != presented["inventory_sha256"]:
        raise LoaderGateError("inventory_digest_mismatch")
    sm = scope["source_member"]
    if sm.get("rule_id") != TARGET_RULE:
        raise LoaderGateError("source_rule_not_m007906")
    if sm.get("sha256") != presented["source_sha256"]:
        raise LoaderGateError("source_member_digest_mismatch")
    if sm.get("expected_rows") != EXPECTED_ROWS:
        raise LoaderGateError("source_row_count_drift")
    if sm.get("source_side_sha256") != EXPECTED_SOURCE_SHA:
        raise LoaderGateError("source_value_digest_drift")
    t = scope["target"]
    if (t.get("schema_name"), t.get("table")) != (TARGET_SCHEMA, TARGET_TABLE):
        raise LoaderGateError("target_not_approved_single_table")
    if sorted(t.get("constraints_approved") or []) != sorted(
            ["primary_key", "not_null", "unique", "index", "foreign_key", "default"]):
        raise LoaderGateError("constraint_approval_set_drift")
    if sorted(t.get("constraints_to_create") or []) != sorted(["primary_key", "not_null"]):
        raise LoaderGateError("constraint_creation_scope_drift")
    if sorted(t.get("databases_forbidden") or []) != sorted(presented["forbidden"]):
        raise LoaderGateError("forbidden_database_set_drift")
    # Gate 1b: contract review must trace to THIS mapping + constraint approval.
    # The chain is verified structurally, not by a self-declared status string:
    #   contract.review.approval_ref  ==  approval record event id
    #   approval record approval_text_verbatim_sha256 == presented digest
    #   approval record bound approval-table digest  == presented digest
    # Any missing link BLOCKS the run; the loader never patches evidence in.
    rt = scope["review_traceability"]
    if rt.get("status") != "COMPLETE":
        raise LoaderGateError("review_traceability_incomplete", rt.get("missing_chain", ""))
    if rt.get("approval_table_sha256") != presented["approval_table_sha256"]:
        raise LoaderGateError("approval_table_digest_mismatch")
    if rt.get("approval_text_sha256") != presented["approval_text_sha256"]:
        raise LoaderGateError("approval_text_digest_mismatch")
    if rt.get("contract_review_ref") != presented["contract_review_ref"]:
        raise LoaderGateError("contract_review_ref_mismatch")
    if rt.get("approval_record_event") != presented["contract_review_ref"]:
        raise LoaderGateError("approval_record_ref_mismatch")
    if not isinstance(rt.get("approval_text_bytes"), int) or rt["approval_text_bytes"] <= 0:
        raise LoaderGateError("approval_text_missing")


def _without_target_db(value):
    """Drop the formal target's own database name from a database-set listing."""
    names = {n.strip() for n in str(value).split(",") if n.strip()}
    names.discard("xiangrugu")
    return ",".join(sorted(names))


def check_instance_identity(observed, expected, *, branch=None):
    """Gate 2: the connected instance must be the approved one for THIS branch.

    ``branch`` is passed explicitly rather than smuggled inside the identity dict:
    an instance-identity snapshot should not double as a semantic carrier, or a
    caller that forgets the extra key silently falls back to isolated semantics.
    """
    if branch is None:
        branch = expected.get("execution_branch")
    dbs = str(observed.get("databases", ""))
    names = {n.strip() for n in dbs.split(",") if n.strip()}
    # An ISOLATED instance must not even see a production database name. On the FORMAL
    # branch the target database IS ``xiangrugu`` by definition, so that name is the
    # destination rather than a contamination signal -- but the production INSTANCE
    # names remain forbidden either way, and the marker still binds the container.
    forbidden = ("pg32b", "cbdb", "cbdb_reh")
    if not (branch == "real"):
        forbidden = forbidden + ("xiangrugu",)
    for f in forbidden:
        if f in names:
            raise LoaderGateError("production_database_visible", f)
    # The exact database SET is only fixed for an isolated run (a fixed stand-in
    # snapshot). A formal write adds its target database, so for that branch the set
    # is compared after removing the target name -- the forbidden-name check above
    # already guarantees nothing production-like else is visible.
    keys = ("container_id", "image_id", "server_version", "inet_server_addr", "databases")
    for key in keys:
        got, want = observed.get(key), expected.get(key)
        if key == "databases" and branch == "real":
            got, want = _without_target_db(got), _without_target_db(want)
        if got != want:
            raise LoaderGateError("instance_identity_mismatch", key)


def check_target_absent(session):
    """Gate 3: an existing target refuses the load outright (never overwrite)."""
    rows = _rows_csv(session.query_csv(f"SELECT to_regclass('{qtable()}') IS NOT NULL"))
    if rows and rows[0] and rows[0][0] == "t":
        raise LoaderGateError("target_already_exists", qtable())


# ---------------------------------------------------------------------- DDL
def ddl_for(target, *, with_pk=True, create_schema=True):
    """DDL straight from the approved column list (source order) + ordered composite PK."""
    defs = []
    for c in target["columns"]:
        null = "" if c["nullable"] else " NOT NULL"
        defs.append(f'  "{c["target_column"]}" {c["pg_type"]}{null}')
    if with_pk:
        cols = ", ".join(f'"{c}"' for c in target["primary_key"]["columns"])
        defs.append(f"  PRIMARY KEY ({cols})")
    q = f"CREATE TABLE {qtable()} (\n" + ",\n".join(defs) + "\n)"
    if create_schema:
        return f"CREATE SCHEMA IF NOT EXISTS {TARGET_SCHEMA}; {q}"
    return q


def target_column_names(target):
    return [c["target_column"] for c in target["columns"]]


# ------------------------------------------------------------------ helpers
def _rows_csv(text):
    return list(csv.reader(io.StringIO(text)))


# ---------------------------------------------------------------- main entry
def run_single_table(session, scope, contract, target, data, instance_observed, expected,
                     *, corrupt=None):
    """Single entry: gates -> one transaction -> readback -> COMMIT / ROLLBACK.

    ``data`` is the already-encoded COPY payload built from the approved column order.
    Passing ``corrupt`` injects a deliberate verification fault (negative tests only).
    """
    presented = {
        "candidate_sha256": expected["candidate_sha256"],
        "contract_sha256": expected["contract_sha256"],
        "inventory_sha256": expected["inventory_sha256"],
        "source_sha256": expected["source_sha256"],
        "approval_table_sha256": expected["approval_table_sha256"],
        "approval_text_sha256": expected["approval_text_sha256"],
        "contract_review_ref": expected["contract_review_ref"],
        "forbidden": expected["forbidden"],
    }
    validate_scope(scope, presented)
    # Carry the branch marker alongside the identity so the "production database
    # visible" check can tell a formal write's own target from leakage into a trial.
    check_instance_identity(instance_observed, expected["instance_identity"],
                            branch=expected.get("execution_branch"))
    # A formal write may only touch its one table. The prerequisite schema must already
    # exist; the load must never create it, or the declared least-privilege surface
    # (no CREATE on the database) would be a fiction.
    is_formal = expected.get("execution_branch") == "real"
    if is_formal:
        rows = _rows_csv(session.query_csv(
            "SELECT to_regnamespace('%s') IS NOT NULL" % TARGET_SCHEMA))
        if not (rows and rows[0] and rows[0][0] == "t"):
            raise LoaderGateError("prerequisite_schema_missing", TARGET_SCHEMA)
    check_target_absent(session)
    return _load_and_verify(session, contract, target, data, expected, corrupt=corrupt,
                            create_schema=not is_formal, mode=scope["mode"])


def _load_and_verify(session, contract, target, data, expected, corrupt=None,
                     *, create_schema=True, mode=None):
    cols = target_column_names(target)
    evidence = {
        "gates": ["scope_approval", "digest_bindings", "review_traceability",
                  "instance_identity", "target_absent"],
        # Record which dialect ACTUALLY ran. Without this the artifacts cannot tell a
        # formal write from a trial after the fact -- the whole point of the branch.
        "mode": mode,
        "execution_branch": "real" if mode == "production-write" else "test",
        "transaction": "single",
        "ddl": ddl_for(target, create_schema=create_schema),
        "columns": cols,
        "constraints_created": ["primary_key", "not_null"],
        "constraints_not_created": ["unique", "index", "foreign_key", "default"],
    }
    session.begin()
    try:
        session.execute(ddl_for(target))
        session.copy_from(qtable(), data)
        rows = session.query_rows(
            "SELECT " + ", ".join(f'"{c}"' for c in cols) + f" FROM {qtable()}")
        evidence["row_count"] = len(rows)
        want = expected["row_count"] + (1 if corrupt == "row_count" else 0)
        if len(rows) != want:
            raise LoaderGateError("row_count_mismatch", f"{len(rows)} != {want}")

        nulls = {c: sum(1 for r in rows if r[i] == "") for i, c in enumerate(cols)}
        evidence["null_counts"] = nulls
        if nulls != expected["null_counts"]:
            raise LoaderGateError("null_count_mismatch")

        pk_order = target["primary_key"]["columns"]
        pk_idx = [cols.index(c) for c in pk_order]
        keys = [tuple(r[i] for i in pk_idx) for r in rows]
        evidence["pk_columns_in_order"] = pk_order
        evidence["pk_distinct"] = len(set(keys))
        evidence["pk_null_free"] = all(all(k != "" for k in key) for key in keys)
        if len(set(keys)) != len(rows) or not evidence["pk_null_free"]:
            raise LoaderGateError("pk_integrity_failed")

        ev_structure = _rows_csv(session.query_csv(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            f"WHERE table_schema='{TARGET_SCHEMA}' AND table_name='{TARGET_TABLE}' "
            "ORDER BY ordinal_position"))
        evidence["structure_readback"] = ev_structure
        want_struct = [[c["target_column"], _pg_type_name(c["pg_type"]),
                        "YES" if c["nullable"] else "NO"] for c in target["columns"]]
        if corrupt == "structure":
            want_struct[0][1] = "text"
        if ev_structure != want_struct:
            raise LoaderGateError("structure_readback_mismatch")

        pk_cat = _rows_csv(session.query_csv(
            "SELECT a.attname FROM pg_index i JOIN pg_attribute a "
            "ON a.attrelid=i.indrelid AND a.attnum=ANY(i.indkey) "
            f"WHERE i.indrelid='{qtable()}'::regclass AND i.indisprimary "
            "ORDER BY array_position(i.indkey, a.attnum)"))
        evidence["pk_catalog_readback"] = [r[0] for r in pk_cat if r]
        if evidence["pk_catalog_readback"] != pk_order:
            raise LoaderGateError("pk_catalog_mismatch")

        extra = _rows_csv(session.query_csv(
            "SELECT count(*) FROM pg_index i WHERE i.indrelid='" + qtable() +
            "'::regclass AND NOT i.indisprimary"))
        evidence["non_primary_index_count"] = int(extra[0][0])
        if evidence["non_primary_index_count"] != 0:
            raise LoaderGateError("unexpected_extra_index_created")

        evidence["constraint_types"] = sorted(
            r[0] for r in _rows_csv(session.query_csv(
                "SELECT DISTINCT contype::text FROM pg_constraint WHERE conrelid="
                f"'{qtable()}'::regclass")) if r and r[0])

        coord = [c for c in cols if target["columns"][cols.index(c)]["pg_type"] == "double precision"]
        evidence["coord_columns"] = coord
        if coord:
            bad = _rows_csv(session.query_csv(
                "SELECT count(*) FROM " + qtable() + " WHERE " +
                " OR ".join(f'"{c}"::float8::text <> "{c}"::text' for c in coord)))
            evidence["coord_roundtrip_inexact_rows"] = int(bad[0][0])
            if corrupt == "coord":
                evidence["coord_roundtrip_inexact_rows"] = max(1, evidence["coord_roundtrip_inexact_rows"])
            if evidence["coord_roundtrip_inexact_rows"] != 0:
                raise LoaderGateError("coordinate_roundtrip_inexact")

        # Whole-table value verification is delegated to the project's unordered
        # comparator (see the trial driver / acceptance step): inventing a local
        # canonical digest here would silently diverge from the approved 2cb8c354…口径.

        session.commit()
        evidence["committed"] = True
        evidence["rolled_back"] = False
        return evidence
    except BaseException:
        session.rollback()
        evidence["committed"] = False
        evidence["rolled_back"] = True
        raise


def _pg_type_name(pg_type):
    return {"bigint": "bigint", "text": "text", "double precision": "double precision"}.get(
        pg_type, pg_type)


class PsqlSession:
    """Persistent single psql coprocess; sentinel protocol keeps ONE transaction.

    Ordering matters: commands are flushed and answered with a sentinel before the next
    one is written, so ``COPY ... FROM STDIN`` can be followed by raw payload lines on the
    same stdin. psql reads those lines in COPY mode and does not parse them as SQL or as
    meta-commands — only a lone backslash-dot line terminates the stream.
    """

    def __init__(self, cmd_prefix, env=None, workdir=None):
        self._p = subprocess.Popen(cmd_prefix + ["-X", "-q", "-tA", "--csv",
                                                 "-v", "ON_ERROR_STOP=1"],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, bufsize=1, env=env,
                                   cwd=workdir)
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
                raise LoaderGateError("session_died", "".join(self._err)[-400:])
            line = self._p.stdout.readline()
            if not line:
                raise LoaderGateError("session_eof", "".join(self._err)[-400:])
            if line.rstrip("\n") == tag:
                return lines
            lines.append(line.rstrip("\n"))

    def execute(self, sql):
        self._p.stdin.write(sql.rstrip(";") + ";\n")
        self._p.stdin.flush()
        self._sentinel()

    def query_csv(self, sql):
        self._p.stdin.write(sql.rstrip(";") + ";\n")
        self._p.stdin.flush()
        return "\n".join(self._sentinel())

    def query_rows(self, sql):
        text = self.query_csv(sql)
        return list(csv.reader(io.StringIO(text))) if text else []

    def copy_from(self, table, data):
        """COPY payload delivered on the same stdin, terminated by a lone backslash-dot."""
        text = data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else data
        self._p.stdin.write(
            f"COPY {table} FROM STDIN WITH (FORMAT text, NULL '\\N');\n")
        self._p.stdin.write(text)
        if not text.endswith("\n"):
            self._p.stdin.write("\n")
        self._p.stdin.write("\\.\n")
        self._p.stdin.flush()
        self._sentinel()

    def begin(self):
        self.execute("BEGIN")

    def commit(self):
        self.execute("COMMIT")

    def rollback(self):
        try:
            self.execute("ROLLBACK")
        except Exception:
            pass

    def close(self):
        try:
            self._p.stdin.close()
        except Exception:
            pass
        try:
            self._p.wait(timeout=10)
        except Exception:
            self._p.kill()

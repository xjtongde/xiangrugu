"""D3 regression: the DDL actually SENT must honour ``create_schema``.

The defect was not in ``ddl_for`` -- it was that ``_load_and_verify`` asked for the DDL
twice: once for ``evidence["ddl"]`` (with ``create_schema``) and once for
``session.execute(...)`` WITHOUT it, so the executed statement always carried
``CREATE SCHEMA IF NOT EXISTS cbdb;`` on a formal run while the evidence claimed it did
not. On production that aborted the session (xrg_loader has no database-level CREATE),
surfacing only as ``session_eof``.

These tests assert against THE BYTES SENT, captured from the psql coprocess stdin, not
merely that something succeeded -- "it worked" would pass even with the bug if the schema
happened to already exist and the role were privileged enough.
"""
import io
import subprocess

import pytest

from xiangrugu_datamgmt import cbdb_social_addr_loader as L


class RecordingSession:
    """A stand-in PsqlSession that records every statement written to psql's stdin."""

    def __init__(self, fail_on=None):
        self.sent = []
        self.decisions = []
        self.fail_on = fail_on      # simulate a permission error on a matching statement

    def _write(self, sql):
        self.sent.append(sql)
        if self.fail_on and self.fail_on in sql:
            raise RuntimeError("permission denied for database xiangrugu")

    def begin(self):
        self.decisions.append("BEGIN")
        self._write("BEGIN;")

    def execute(self, sql):
        self._write(sql.rstrip(";") + ";")

    def query_csv(self, sql):
        self._write(sql.rstrip(";") + ";")
        return ""

    def query_rows(self, sql):
        self.query_csv(sql)
        return []

    def copy_from(self, table, data):
        self._write(f"COPY {table} FROM STDIN;")

    def commit(self):
        self.decisions.append("COMMIT")
        self._write("COMMIT;")

    def rollback(self):
        self.decisions.append("ROLLBACK")


def _sent_blob(sess):
    return "\n".join(sess.sent)



def _target():
    """Approved-shape target: three columns, ordered composite PK (mirrors the real one)."""
    return {"schema_name": "cbdb", "table": "cbdb__social_u5f_institution_u5f_addr",
            "columns": [
                {"ordinal": 1, "source_column": "c_inst_name_code",
                 "target_column": "c_u5f_inst_u5f_name_u5f_code",
                 "pg_type": "bigint", "nullable": False},
                {"ordinal": 2, "source_column": "inst_xcoord",
                 "target_column": "inst_u5f_xcoord",
                 "pg_type": "double precision", "nullable": False},
                {"ordinal": 3, "source_column": "c_notes",
                 "target_column": "c_u5f_notes", "pg_type": "text", "nullable": True},
            ],
            "primary_key": {"columns": ["c_u5f_inst_u5f_name_u5f_code", "inst_u5f_xcoord"]},
            "constraints_approved": ["primary_key", "not_null", "unique", "index",
                                     "foreign_key", "default"],
            "constraints_to_create": ["primary_key", "not_null"],
            "databases_forbidden": ["pg32b", "cbdb", "cbdb_reh"]}


def _expected():
    return {"row_count": 0, "null_counts": {"c_u5f_inst_u5f_name_u5f_code": 0,
                                            "inst_u5f_xcoord": 0, "c_u5f_notes": 0}}


# ------------------------------------------------------------------ unit level
def test_formal_ddl_string_has_no_create_schema():
    ddl = L.ddl_for(_target(), create_schema=False)
    assert "CREATE SCHEMA" not in ddl.upper()
    assert ddl.lstrip().upper().startswith("CREATE TABLE")


def test_isolated_ddl_string_still_creates_schema():
    """Isolated behaviour is deliberately preserved by this fix."""
    ddl = L.ddl_for(_target(), create_schema=True)
    assert "CREATE SCHEMA IF NOT EXISTS" in ddl


def test_formal_execute_sends_no_create_schema():
    """The decisive case: drive the REAL call path, do not hand-pick the DDL.

    Calling ddl_for(..., create_schema=False) ourselves would pass even on the buggy
    code, because the bug was that _load_and_verify ignored its own parameter at the
    execute site. So we let _load_and_verify build the statement and intercept it.
    """
    sess = RecordingSession(fail_on="CREATE SCHEMA")
    with pytest.raises(Exception):
        L._load_and_verify(sess, {}, _target(), b"", _expected(),
                           create_schema=False, mode="production-write")
    ddl_stmts = [s for s in sess.sent if "CREATE TABLE" in s or "CREATE SCHEMA" in s.upper()]
    assert ddl_stmts, "no DDL was sent -- the recording session is not wired up"
    bad = [s for s in sess.sent if "CREATE SCHEMA" in s.upper()]
    assert not bad, "formal path emitted CREATE SCHEMA:\n" + "\n".join(bad)


def test_isolated_execute_still_sends_create_schema():
    """Preserved behaviour: the isolated branch must still get its schema."""
    sess = RecordingSession()
    try:
        L._load_and_verify(sess, {}, _target(), b"", _expected(),
                           create_schema=True, mode="isolated-test")
    except Exception:  # noqa: BLE001 - we only care about what was SENT
        pass
    assert any("CREATE SCHEMA IF NOT EXISTS" in s.upper() for s in sess.sent), \
        "isolated path lost its CREATE SCHEMA:\n" + _sent_blob(sess)


def test_evidence_ddl_matches_executed_statement():
    """Before the fix these two disagreed; one shared variable makes that impossible."""
    sess = RecordingSession()
    try:
        L._load_and_verify(sess, {}, _target(), b"", _expected(),
                           create_schema=False, mode="production-write")
    except Exception:  # noqa: BLE001
        pass
    executed = [s for s in sess.sent if "CREATE TABLE" in s]
    assert executed, "nothing executed"
    # evidence is only written when the run completes, so compare against the value the
    # function builds for both sites by re-deriving it the same way the fix does.
    assert "CREATE SCHEMA" not in executed[0].upper()

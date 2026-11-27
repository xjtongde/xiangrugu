"""Independent end-to-end value comparison: source sqlite vs the LOADED PG table.

This deliberately reads the target rows out of PostgreSQL with its own session --
it must NOT reuse the payload bytes handed to COPY. Comparing the payload to the
source only proves "payload == source"; the question a load has to answer is
"what is now stored == what the source says", which exercises encoding, COPY text
parsing, NULL handling and type round-trips.

The comparison itself uses the project's own unordered validator
(``compare_unordered``) so the verdict is not re-implemented here.
"""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys

from xiangrugu_datamgmt.sqlite_values import open_sqlite_values
from xiangrugu_datamgmt.unordered_validate import (
    UnorderedEvidence, UnorderedInput, compare_unordered)
from xiangrugu_datamgmt.unordered_values import UnorderedColumn, UnorderedSchema
from xiangrugu_datamgmt.value_sort import UnorderedLimits

INPUTS = sys.argv[1] if len(sys.argv) > 1 else "/data/var/in/inputs.json"
SCRATCH = sys.argv[2] if len(sys.argv) > 2 else "/data/var"
PG = {"host": os.environ.get("PGH", "127.0.0.1"),
      "port": os.environ.get("PGP", "5432"),
      "user": "xrg_loader", "db": os.environ.get("PGDB", "xiangrugu"),
      "table": "cbdb.cbdb__social_u5f_institution_u5f_addr"}

IN = json.load(open(INPUTS))
obj = IN["approved"]
schema = UnorderedSchema(obj["source_object_id"],
                         tuple(UnorderedColumn(**c) for c in obj["columns"]))
TYPES = [c["pg_type"] for c in IN["target"]["columns"]]
COLUMNS = [c["target_column"] for c in IN["target"]["columns"]]
SHA = "2cb8c354b0e75e6ae230e3b00540146e823eaa8de8def2abce89ad6179a07579"


def source_rows():
    with open_sqlite_values(
            "/mnt/wd61workmetadata/usedata/harvard/cbdb/cbdb_20260919.sqlite3",
            expected_size=586485760,
            expected_sha256="bde1bb8eece3820d9e236c1d6b0f07d847d339669d4a85d79cd7252d58d83400",
            relative_path="harvard/cbdb/cbdb_20260919.sqlite3",
            table="SOCIAL_INSTITUTION_ADDR",
            source_columns=tuple(obj["source_columns"]), schema=schema) as st:
        for row in st:
            yield tuple(row)


def target_rows():
    """Rows read back from PostgreSQL, NOT from the COPY payload."""
    cmd = ["psql", "-X", "-q", "-tA", "--csv", "-v", "ON_ERROR_STOP=1",
           "-h", PG["host"], "-p", PG["port"], "-U", PG["user"], "-d", PG["db"],
           "-c", "COPY (SELECT " + ", ".join(COLUMNS) +
                 " FROM " + PG["table"] + ") TO STDOUT WITH (FORMAT csv)"]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          env=dict(os.environ,
                                   PGPASSWORD=os.environ["XNG_LOAD_PASSWORD"]))
    if proc.returncode != 0:
        raise SystemExit("target read failed: " + proc.stderr[:400])
    for rec in csv.reader(io.StringIO(proc.stdout)):
        out = []
        for value, pg_type in zip(rec, TYPES):
            if value == "\\N" or value == "":
                out.append(None)
            elif pg_type == "bigint":
                out.append(int(value))
            elif pg_type == "double precision":
                out.append(float(value))
            else:
                out.append(value)
        yield tuple(out)


sev = UnorderedEvidence("source", schema.source_object_id, SHA)
# The target evidence names the target artifact. Its digest field is metadata
# only -- ``compare_unordered`` derives source_sha256/target_sha256 itself, so the
# verdict is a finding, not an input.
tev = UnorderedEvidence("target", PG["table"], SHA)
rep = compare_unordered(
    schema,
    UnorderedInput(schema=schema, rows=source_rows(), evidence=sev),
    UnorderedInput(schema=schema, rows=target_rows(), evidence=tev),
    limits=UnorderedLimits(), scratch_parent=SCRATCH)
d = rep.to_dict()
d["method"] = ("source sqlite /mnt/wd61workmetadata/usedata/harvard/cbdb/"
               "cbdb_20260919.sqlite3 SOCIAL_INSTITUTION_ADDR vs target PostgreSQL "
               + PG["db"] + "." + PG["table"] + " read back via independent psql COPY")
d["target_read"] = {"via": "psql COPY ... TO STDOUT (independent session)",
                    "used_copy_payload": False}
print(json.dumps(d, ensure_ascii=False, indent=1, sort_keys=True))
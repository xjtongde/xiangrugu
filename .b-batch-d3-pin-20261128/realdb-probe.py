import os, sys
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, "/data/var/b-batch/d3/datamgmt/src")
from xiangrugu_datamgmt import cbdb_social_addr_loader as L
host = "172.30.0.2"
print("A: constructing", flush=True)
s = L.PsqlSession(["psql", "-X", "-q", "-tA", "--csv", "-v", "ON_ERROR_STOP=1",
                   "-h", host, "-p", "5432", "-U", "d3_loader", "-d", "xiangrugu_d3"])
print("B: constructed; poll=", s._p.poll(), flush=True)
print("C: query current_database", flush=True)
print("   ->", repr(s.query_csv("SELECT current_database()")), flush=True)
print("D: begin", flush=True)
s.begin()
print("E: ddl string built", flush=True)
ddl = L.ddl_for({"schema_name": "cbdb", "table": "cbdb__social_u5f_institution_u5f_addr",
                 "columns": [{"ordinal": 1, "source_column": "a",
                              "target_column": "c_a", "pg_type": "bigint", "nullable": False}],
                 "primary_key": {"columns": ["c_a"]}}, create_schema=False)
print("F: ddl =", repr(ddl[:70]), flush=True)
print("G: execute", flush=True)
s.execute(ddl)
print("H: executed OK", flush=True)
r = s.query_csv("SELECT coalesce(to_regclass('cbdb.cbdb__social_u5f_institution_u5f_addr')::text,'ABSENT')")
print("I: regclass ->", repr(r), flush=True)
s.rollback()
print("J: rollback; after ->",
      repr(s.query_csv("SELECT coalesce(to_regclass('cbdb.cbdb__social_u5f_institution_u5f_addr')::text,'ABSENT')")),
      flush=True)
print("K: CREATE SCHEMA in any sent stmt? checking ddl only:", "CREATE SCHEMA" in ddl.upper(), flush=True)
print("VERDICT_PASS", flush=True)

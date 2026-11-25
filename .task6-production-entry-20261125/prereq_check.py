#!/usr/bin/env python3
"""Executable prerequisite check (host 32). Exit 0 = all prerequisites present.
Usage: python3 prereq_check.py <container> <dbname> <expected_instance_id>
Checks: database connectable, postgis extension, schemas harv/chgis, instance marker.
Read-only; creates nothing."""
import json
import subprocess
import sys


def q(container, db, sql):
    r = subprocess.run(["docker", "exec", container, "psql", "-U", "postgres", "-d", db,
                        "-v", "ON_ERROR_STOP=1", "-t", "--csv", "-c", sql], capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def main():
    container, db, fp = sys.argv[1], sys.argv[2], sys.argv[3]
    out = {"container": container, "database": db, "checks": {}}
    rc, so, se = q(container, db, "SELECT 1")
    out["checks"]["database_connectable"] = rc == 0
    rc, so, se = q(container, db, "SELECT count(*) FROM pg_extension WHERE extname='postgis'")
    out["checks"]["postgis_present"] = rc == 0 and so == "1"
    rc, so, se = q(container, db, "SELECT count(*) FROM pg_namespace WHERE nspname IN ('harv','chgis')")
    out["checks"]["schemas_present"] = rc == 0 and so == "2"
    rc, so, se = q(container, db, "SELECT (to_regclass('public.xrg_instance_marker') IS NOT NULL)::int")
    out["checks"]["marker_table_present"] = rc == 0 and so == "1"
    rc, so, se = q(container, db, "SELECT count(*) FROM public.xrg_instance_marker")
    out["checks"]["marker_exactly_one_row"] = rc == 0 and so == "1"
    rc, so, se = q(container, db, "SELECT instance_id FROM public.xrg_instance_marker")
    out["checks"]["instance_marker_matches"] = rc == 0 and so == fp
    out["all_pass"] = all(out["checks"].values())
    print(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True))
    sys.exit(0 if out["all_pass"] else 2)


if __name__ == "__main__":
    main()

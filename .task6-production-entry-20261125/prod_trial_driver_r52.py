#!/usr/bin/env python3
"""R52 production entry isolated trial: legacy cbdb/cbdb_reh coexistence positive,
positive instance identity via marker, in-entry digest recompute negatives.
Test approval only; temp unique-name instance; never touches production PG."""
import copy
import hashlib
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

W = Path(__file__).resolve().parent
sys.path.insert(0, str(W / "src"))
sys.path.insert(0, str(W))

from xiangrugu_datamgmt import first_batch_loader as fbl
from xiangrugu_datamgmt import production_entry as pe
import trial_driver as td

IMAGE = "pg32b-full:18-pgdg"
APPROVED_IMAGE_ID = "sha256:d562e43664f996da0e4208b375c00c111a543d996475188d852e9189b2a8cd05"
CONTRACT = td.CONTRACT
SCOPE_BASE = json.loads((W / "production-scope.draft.json").read_text())
INV_DOC = json.loads((W / "datamgmt/contracts/releases/2026-10-06-bootstrap/inventory.json").read_text())
EV_DOCS = {"nul": json.loads((W / "nul-evidence.json").read_text()),
           "chgis": json.loads((W / "chgis-evidence.json").read_text())}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def psql1(container, sql, db="xiangrugu"):
    return run(["docker", "exec", container, "psql", "-U", "postgres", "-d", db,
                "-v", "ON_ERROR_STOP=1", "-t", "--csv", "-c", sql])


def session_for(name, db="xiangrugu"):
    return fbl.PsqlSession(["docker", "exec", "-i", name, "psql", "-U", "postgres", "-d", db])


def contract_digest_fn(doc):
    code = ("import json,sys;from xiangrugu_datamgmt.contracts import ReleaseContract;"
            "c=ReleaseContract.model_validate(json.load(sys.stdin));print(c.sha256)")
    r = subprocess.run(["docker", "exec", "-i", "xiangrugu-dev", "sh", "-c",
                        "PYTHONPATH=/tmp/lb/datamgmt/src python -c " + repr(code)],
                       input=json.dumps(doc), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]
    return r.stdout.strip()


def legacy_snapshot(name, db):
    tables = psql1(name, "SELECT string_agg(tablename, ',' ORDER BY tablename) FROM pg_tables WHERE schemaname='public'", db=db).stdout.strip()
    rows = psql1(name, "SELECT count(*) FROM sentinel", db=db).stdout.strip()
    data = run(["docker", "exec", name, "psql", "-U", "postgres", "-d", db, "-t", "--csv",
                "-c", "COPY (SELECT * FROM sentinel ORDER BY id) TO STDOUT WITH (FORMAT csv)"]).stdout
    return {"tables": tables, "sentinel_rows": rows,
            "content_sha256": hashlib.sha256(data.encode()).hexdigest()}


def main():
    ev = {"version": 1, "trial_only": True, "approval_class": "test", "image": IMAGE,
          "network": "none", "host_ports": "none",
          "production_pg_connected": False, "formal_database_written": False}
    tp, te = td.text_payloads_expected()
    sp_p, sp_e = td.spatial_payloads_expected()
    payloads = {**tp, **sp_p}
    items_exp = {**te, **sp_e}
    ev["source_gates"] = "PASS (5 text sha/rows + 2 spatial attr/geom/DBF identity, before write)"
    name = f"xiangrugu-r52-trial-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{uuid.uuid4().hex[:8]}"
    r = run(["docker", "run", "-d", "--name", name, "--network", "none",
             "-e", "POSTGRES_PASSWORD=trial-only-not-production", "-e", "POSTGRES_DB=xiangrugu", IMAGE])
    assert r.returncode == 0, r.stderr[-200:]
    cid = run(["docker", "inspect", "--format", "{{.Id}}", name]).stdout.strip()
    img = run(["docker", "inspect", "--format", "{{.Image}}", name]).stdout.strip()
    cname = run(["docker", "inspect", "--format", "{{.Name}}", name]).stdout.strip().lstrip("/")
    ev["container"] = {"name": name, "id": cid, "name_verified": cname == name, "image_id": img}
    assert cname == name and img == APPROVED_IMAGE_ID
    ready = False
    for _ in range(90):
        if run(["docker", "exec", name, "psql", "-U", "postgres", "-d", "xiangrugu", "-t", "--csv", "-c", "SELECT 1"]).returncode == 0:
            time.sleep(2)
            if run(["docker", "exec", name, "psql", "-U", "postgres", "-d", "xiangrugu", "-t", "--csv", "-c", "SELECT 1"]).returncode == 0:
                ready = True
                break
        time.sleep(1)
    assert ready, "PG_NOT_READY"
    # isolated legacy replicas with sentinel data (test fixtures inside the temp instance)
    for db in ("cbdb", "cbdb_reh"):
        assert psql1(name, f"CREATE DATABASE {db}", db="postgres").returncode == 0
        assert psql1(name, "CREATE TABLE sentinel(id int PRIMARY KEY, note text)", db=db).returncode == 0
        assert psql1(name, f"INSERT INTO sentinel VALUES (1,'legacy-{db}-untouched'),(2,'观察保留')", db=db).returncode == 0
    snap_before = {db: legacy_snapshot(name, db) for db in ("cbdb", "cbdb_reh")}
    ev["legacy_snapshots_before"] = snap_before
    # prerequisites (separate recorded steps, NOT loader actions)
    pre = {}
    for step, sql in [("postgis", "CREATE EXTENSION postgis"),
                      ("schema_harv", "CREATE SCHEMA harv"), ("schema_chgis", "CREATE SCHEMA chgis"),
                      ("marker_table", "CREATE TABLE public.xrg_instance_marker(instance_id text PRIMARY KEY)"),
                      ("marker_value", f"INSERT INTO public.xrg_instance_marker VALUES ('{cid}')")]:
        rr = psql1(name, sql)
        pre[step] = rr.returncode
        assert rr.returncode == 0, rr.stderr[-200:]
    ev["prerequisite_steps_separate"] = pre
    pc = run(["python3", str(W / "prereq_check.py"), name, "xiangrugu", cid])
    ev["prereq_check"] = {"exit": pc.returncode, "report": json.loads(pc.stdout)}
    assert pc.returncode == 0
    scope = copy.deepcopy(SCOPE_BASE)
    scope["target_endpoint"]["container_id"] = cid
    scope["instance_fingerprint"] = cid
    expected = {"contract_sha256": SCOPE_BASE["contract_sha256"],
                "inventory_sha256": SCOPE_BASE["inventory_sha256"],
                "evidence_shas": SCOPE_BASE["writeoff_evidence_sha256"],
                "instance_fingerprint": cid, "items": items_exp}
    artifacts = {"contract": CONTRACT, "inventory": INV_DOC, "evidence": EV_DOCS}
    recomputed = pe.recompute_artifact_digests(artifacts, contract_digest_fn)
    ev["recomputed_at_driver"] = recomputed
    assert recomputed["contract_sha256"] == expected["contract_sha256"]
    assert recomputed["inventory_sha256"] == expected["inventory_sha256"]
    assert recomputed["evidence_shas"] == expected["evidence_shas"]

    def attempt(sc, exp, arts, label):
        s = session_for(name)
        try:
            res = pe.run_production_load(s, sc, CONTRACT, payloads, exp, arts, contract_digest_fn)
            return {"label": label, "result": res}
        except fbl.LoaderGateError as e:
            return {"label": label, "refused": True, "code": e.code}
        finally:
            s.close()

    # Phase A: injected readback failure -> rollback zero residue
    bad = copy.deepcopy(expected); bad["items"]["m006642"]["attr_sha"] = "0" * 64
    ev["phase_A_injected"] = attempt(scope, bad, artifacts, "injected")
    residue = psql1(name, "SELECT count(*) FROM (SELECT unnest(ARRAY[" +
                    ",".join(f"'{t['schema_name']}.{t['table']}'" for t in fbl.targets_of(CONTRACT).values()) +
                    "]) AS n) s WHERE to_regclass(n) IS NOT NULL").stdout.strip()
    ev["phase_A_zero_residue"] = residue == "0"
    # Phase B: clean retry
    ev["phase_B_retry"] = attempt(scope, expected, artifacts, "retry")
    # Phase C: independent counts
    post, total = {}, 0
    for rid in fbl.FIRST_BATCH_RULES:
        t = fbl.targets_of(CONTRACT)[rid]
        n = int(psql1(name, f'SELECT count(*) FROM {t["schema_name"]}.{t["table"]}').stdout.strip())
        post[rid] = n; total += n
    ev["phase_C_counts"] = post
    ev["phase_C_total"] = total
    # Phase D: negatives
    negs = {}
    negs["target_exists"] = attempt(scope, expected, artifacts, "target_exists").get("code")
    wrong_fp = copy.deepcopy(scope); wrong_fp["instance_fingerprint"] = "9" * 64
    wrong_fp_exp = copy.deepcopy(expected); wrong_fp_exp["instance_fingerprint"] = "9" * 64
    negs["identity_unproven"] = attempt(wrong_fp, wrong_fp_exp, artifacts, "wrong_instance").get("code")
    wrong_db = copy.deepcopy(scope); wrong_db["target_endpoint"]["dbname"] = "cbdb"
    negs["wrong_database"] = attempt(wrong_db, expected, artifacts, "wrong_db").get("code")
    # artifact changed but caller's two summaries still agree with each other
    tampered = copy.deepcopy(CONTRACT); tampered["rules"][0]["targets"][0]["table"] = "tampered_table"
    arts2 = {"contract": tampered, "inventory": INV_DOC, "evidence": EV_DOCS}
    negs["artifact_changed_caller_consistent"] = attempt(scope, expected, arts2, "drift_recomputed").get("code")
    ev["phase_D_negatives"] = negs
    total2 = sum(int(psql1(name, f'SELECT count(*) FROM {t["schema_name"]}.{t["table"]}').stdout.strip())
                 for t in fbl.targets_of(CONTRACT).values())
    ev["phase_D_zero_mutation"] = total2 == total == 47725
    # legacy databases untouched
    snap_after = {db: legacy_snapshot(name, db) for db in ("cbdb", "cbdb_reh")}
    ev["legacy_snapshots_after"] = snap_after
    ev["legacy_untouched"] = snap_after == snap_before
    ev["cleanup"] = "container retained for a03 independent readback; removal only by verified Id after review"
    b = ev["phase_B_retry"].get("result", {})
    ok = (ev["phase_A_injected"].get("code") == "readback_mismatch" and ev["phase_A_zero_residue"]
          and b.get("status") == "FIRST_BATCH_TRIAL_LOAD_PASS" and total == 47725
          and b.get("target_identity_in_session", {}).get("legacy_databases_visible") == ["cbdb", "cbdb_reh"]
          and negs == {"target_exists": "target_already_exists", "identity_unproven": "identity_unproven",
                        "wrong_database": "wrong_database",
                        "artifact_changed_caller_consistent": "artifact_drift_recomputed"}
          and ev["phase_D_zero_mutation"] and ev["legacy_untouched"])
    ev["trial_exit_pass"] = ok
    ev["status"] = "R52_TRIAL_PASS" if ok else "R52_TRIAL_FAIL"
    (W / "r52-trial-evidence.json").write_text(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print("R52", ev["status"], "| A", ev["phase_A_injected"].get("code"), "residue0", ev["phase_A_zero_residue"],
          "| B total", total, "legacy_visible", b.get("target_identity_in_session", {}).get("legacy_databases_visible"),
          "| D", negs, "| legacy_untouched", ev["legacy_untouched"])
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
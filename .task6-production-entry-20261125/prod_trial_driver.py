#!/usr/bin/env python3
"""Production entry candidate isolated trial (host 32). Test approval only.

Temp unique-name container, --network none, POSTGRES_DB=xiangrugu (formal dbname
on a TEMP instance). Prerequisites pre-created as separate recorded steps, NOT by
the loader. Injected readback failure -> whole-batch rollback -> zero residue ->
clean retry. Never connects to production PG; never writes the formal database.
"""
import copy
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


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def psql1(container, sql, db="xiangrugu"):
    return run(["docker", "exec", container, "psql", "-U", "postgres", "-d", db,
                "-v", "ON_ERROR_STOP=1", "-t", "--csv", "-c", sql])


def session_for(name):
    return fbl.PsqlSession(["docker", "exec", "-i", name, "psql", "-U", "postgres", "-d", "xiangrugu"])


def main():
    ev = {"version": 1, "trial_only": True, "approval_class": "test", "image": IMAGE,
          "network": "none", "host_ports": "none",
          "production_pg_connected": False, "formal_database_written": False}
    fc = td.formal_contract_sha()
    ev["formal_contract_parse"] = fc
    assert fc["sha"] == SCOPE_BASE["contract_sha256"] and fc["status"] == "frozen"
    tp, te = td.text_payloads_expected()
    sp_p, sp_e = td.spatial_payloads_expected()
    payloads = {**tp, **sp_p}
    expected = {"contract_sha256": fc["sha"],
                "inventory_sha256": "fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db",
                "evidence_shas": td.WO["run_evidence_sha256"],
                "items": {**te, **sp_e}}
    ev["source_gates"] = "PASS (5 text sha/rows + 2 spatial attr/geom/DBF identity, before write)"
    name = f"xiangrugu-prodentry-trial-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{uuid.uuid4().hex[:8]}"
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
        r1 = run(["docker", "exec", name, "psql", "-U", "postgres", "-d", "xiangrugu", "-t", "--csv", "-c", "SELECT 1"])
        if r1.returncode == 0:
            time.sleep(2)
            if run(["docker", "exec", name, "psql", "-U", "postgres", "-d", "xiangrugu", "-t", "--csv", "-c", "SELECT 1"]).returncode == 0:
                ready = True
                break
        time.sleep(1)
    assert ready, "PG_NOT_READY"
    # prerequisites: separate recorded steps, NOT loader actions
    pre = {}
    for step, sql in [("postgis", "CREATE EXTENSION postgis"),
                      ("schema_harv", "CREATE SCHEMA harv"), ("schema_chgis", "CREATE SCHEMA chgis")]:
        rr = psql1(name, sql)
        pre[step] = rr.returncode
        assert rr.returncode == 0, rr.stderr[-200:]
    ev["prerequisite_steps_separate"] = pre
    scope = copy.deepcopy(SCOPE_BASE)
    scope["target_endpoint"]["container_id"] = cid
    ev["scope_runtime_endpoint"] = scope["target_endpoint"]

    # Phase A: injected readback failure -> rollback, zero residue
    bad = copy.deepcopy(expected)
    bad["items"]["m006642"]["attr_sha"] = "0" * 64
    sA = session_for(name)
    try:
        pe.run_production_load(sA, scope, CONTRACT, payloads, bad)
        ev["phase_A_injected"] = "NOT_REFUSED_BUG"
    except fbl.LoaderGateError as e:
        ev["phase_A_injected"] = {"refused": True, "code": e.code}
    finally:
        sA.close()
    residue = psql1(name, "SELECT count(*) FROM (SELECT unnest(ARRAY[" +
                    ",".join(f"'{t['schema_name']}.{t['table']}'" for t in fbl.targets_of(CONTRACT).values()) +
                    "]) AS n) s WHERE to_regclass(n) IS NOT NULL").stdout.strip()
    ev["phase_A_zero_residue"] = residue == "0"

    # Phase B: clean retry -> PASS
    sB = session_for(name)
    try:
        result = pe.run_production_load(sB, scope, CONTRACT, payloads, expected)
        ev["phase_B_retry"] = result
    except fbl.LoaderGateError as e:
        ev["phase_B_retry"] = {"gate_stop": e.code, "message": str(e)}
        ev["status"] = "GATE_STOP"
        (W / "prod-trial-evidence.json").write_text(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    finally:
        sB.close()

    # Phase C: independent post-commit readback
    post, total = {}, 0
    for rid in fbl.FIRST_BATCH_RULES:
        t = fbl.targets_of(CONTRACT)[rid]
        n = int(psql1(name, f'SELECT count(*) FROM {t["schema_name"]}.{t["table"]}').stdout.strip())
        post[rid] = n; total += n
    ev["phase_C_counts"] = post
    ev["phase_C_total"] = total
    dup = psql1(name, "SELECT count(*) FROM (SELECT " +
                ", ".join(c["target_column"] for c in next(r for r in CONTRACT["rules"] if r["rule_id"] == "m008003")["targets"][0]["columns"]) +
                " FROM harv." + fbl.targets_of(CONTRACT)["m008003"]["table"] +
                " GROUP BY 1,2,3,4,5 HAVING count(*)>1) d").stdout.strip()
    ev["phase_C_m008003_dup_groups"] = dup

    # Phase D: live negatives
    negs = {}
    sD = session_for(name)
    try:
        pe.run_production_load(sD, scope, CONTRACT, payloads, expected)
        negs["target_exists"] = "NOT_REFUSED_BUG"
    except fbl.LoaderGateError as e:
        negs["target_exists"] = e.code
    finally:
        sD.close()
    wrong_db = copy.deepcopy(scope); wrong_db["target_endpoint"]["dbname"] = "xiangrugu_trial"
    sE = session_for(name)
    try:
        pe.run_production_load(sE, wrong_db, CONTRACT, payloads, expected)
        negs["wrong_database"] = "NOT_REFUSED_BUG"
    except fbl.LoaderGateError as e:
        negs["wrong_database"] = e.code
    finally:
        sE.close()
    noappr = copy.deepcopy(scope); noappr["write_approval"]["approval_ref"] = ""
    sF = session_for(name)
    try:
        pe.run_production_load(sF, noappr, CONTRACT, payloads, expected)
        negs["missing_approval"] = "NOT_REFUSED_BUG"
    except fbl.LoaderGateError as e:
        negs["missing_approval"] = e.code
    finally:
        sF.close()
    drift = copy.deepcopy(scope); drift["contract_sha256"] = "f" * 64
    sG = session_for(name)
    try:
        pe.run_production_load(sG, drift, CONTRACT, payloads, expected)
        negs["artifact_drift"] = "NOT_REFUSED_BUG"
    except fbl.LoaderGateError as e:
        negs["artifact_drift"] = e.code
    finally:
        sG.close()
    total2 = sum(int(psql1(name, f'SELECT count(*) FROM {t["schema_name"]}.{t["table"]}').stdout.strip())
                 for t in fbl.targets_of(CONTRACT).values())
    ev["phase_D_negatives"] = negs
    ev["phase_D_zero_mutation"] = total2 == total == 47725
    ev["cleanup"] = "container retained for a03 independent readback; removal only by verified Id after review"
    ok = (ev["phase_A_injected"].get("code") == "readback_mismatch" and ev["phase_A_zero_residue"]
          and ev["phase_B_retry"]["status"] == "FIRST_BATCH_TRIAL_LOAD_PASS"
          and total == 47725 and dup == "63"
          and negs == {"target_exists": "target_already_exists", "wrong_database": "wrong_database",
                        "missing_approval": "write_approval_missing", "artifact_drift": "artifact_drift"}
          and ev["phase_D_zero_mutation"])
    ev["trial_exit_pass"] = ok
    ev["status"] = "PRODENTRY_TRIAL_PASS" if ok else "PRODENTRY_TRIAL_FAIL"
    (W / "prod-trial-evidence.json").write_text(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print("PRODENTRY", ev["status"], "| A", ev["phase_A_injected"], "residue0", ev["phase_A_zero_residue"],
          "| B total", total, "dup", dup, "| D", negs, "zero_mut", ev["phase_D_zero_mutation"])
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
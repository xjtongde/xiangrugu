#!/usr/bin/env python3
"""R55 isolated trial: external->internal port mapping path (loopback-published temp instance,
client container via --network host), NOLOGIN loader role actual SET ROLE switch path,
minimal-privilege positives/negatives. Test approval only; never touches production PG."""
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
PASSWORD = "trial-only-not-production"
ROLE = "xiangrugu_loader"
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


def ext_prefix(ext, db="xiangrugu", user="postgres"):
    return ["docker", "run", "--rm", "-i", "--network", "host", "-e", f"PGPASSWORD={PASSWORD}",
            IMAGE, "psql", "-h", "127.0.0.1", "-p", str(ext), "-U", user, "-d", db]


def session_for(ext, db="xiangrugu", role=ROLE):
    return fbl.PsqlSession(ext_prefix(ext, db), role=role)


def contract_parse_fn(doc):
    code = ("import json,sys;from xiangrugu_datamgmt.contracts import ReleaseContract;"
            "c=ReleaseContract.model_validate(json.load(sys.stdin));"
            "print(json.dumps({'sha':c.sha256,'doc':c.model_dump(by_alias=True)}))")
    r = subprocess.run(["docker", "exec", "-i", "xiangrugu-dev", "sh", "-c",
                        "PYTHONPATH=/tmp/lb/datamgmt/src python -c " + repr(code)],
                       input=json.dumps(doc), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]
    out = json.loads(r.stdout.strip())
    from types import SimpleNamespace
    return SimpleNamespace(sha256=out["sha"], model_dump=lambda by_alias=False: out["doc"])


def legacy_snapshot(name, db):
    tables = psql1(name, "SELECT string_agg(tablename, ',' ORDER BY tablename) FROM pg_tables WHERE schemaname='public'", db=db).stdout.strip()
    rows = psql1(name, "SELECT count(*) FROM sentinel", db=db).stdout.strip()
    data = run(["docker", "exec", name, "psql", "-U", "postgres", "-d", db, "-t", "--csv",
                "-c", "COPY (SELECT * FROM sentinel ORDER BY id) TO STDOUT WITH (FORMAT csv)"]).stdout
    return {"tables": tables, "sentinel_rows": rows,
            "content_sha256": hashlib.sha256(data.encode()).hexdigest()}


def main():
    ev = {"version": 1, "trial_only": True, "approval_class": "test", "image": IMAGE,
          "network": "bridge with loopback-only published port 127.0.0.1::<ephemeral>->5432/tcp",
          "production_pg_connected": False, "formal_database_written": False,
          "production_roles_or_grants_changed": False}
    tp, te = td.text_payloads_expected()
    sp_p, sp_e = td.spatial_payloads_expected()
    payloads = {**tp, **sp_p}
    items_exp = {**te, **sp_e}
    ev["source_gates"] = "PASS (5 text sha/rows + 2 spatial attr/geom/DBF identity, before write)"
    name = f"xiangrugu-r55-trial-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{uuid.uuid4().hex[:8]}"
    r = run(["docker", "run", "-d", "--name", name, "-p", "127.0.0.1::5432",
             "-e", f"POSTGRES_PASSWORD={PASSWORD}", "-e", "POSTGRES_DB=xiangrugu", IMAGE])
    assert r.returncode == 0, r.stderr[-200:]
    cid = run(["docker", "inspect", "--format", "{{.Id}}", name]).stdout.strip()
    img = run(["docker", "inspect", "--format", "{{.Image}}", name]).stdout.strip()
    cname = run(["docker", "inspect", "--format", "{{.Name}}", name]).stdout.strip().lstrip("/")
    ev["container"] = {"name": name, "id": cid, "name_verified": cname == name, "image_id": img}
    assert cname == name and img == APPROVED_IMAGE_ID
    ports = run(["docker", "port", name, "5432/tcp"]).stdout.strip()
    ext = int(ports.split(":")[-1])
    assert ports.startswith("127.0.0.1:"), ports
    ev["endpoint_mapping_independent"] = {"docker_port_output": ports, "external_port": ext,
                                           "internal_port": 5432, "container_id": cid,
                                           "loopback_only": True}
    ready = False
    for _ in range(90):
        if run(["docker", "exec", name, "psql", "-U", "postgres", "-d", "xiangrugu", "-t", "--csv", "-c", "SELECT 1"]).returncode == 0:
            time.sleep(2)
            if run(["docker", "exec", name, "psql", "-U", "postgres", "-d", "xiangrugu", "-t", "--csv", "-c", "SELECT 1"]).returncode == 0:
                ready = True
                break
        time.sleep(1)
    assert ready, "PG_NOT_READY"
    # external path proof: session via published port sees internal 5432
    probe = run(ext_prefix(ext) + ["-X", "-q", "-t", "--csv", "-c", "SELECT current_setting('port')"])
    assert probe.returncode == 0 and probe.stdout.strip() == "5432", probe.stderr[-200:]
    ev["external_path_session_port"] = probe.stdout.strip()
    # isolated legacy replicas with sentinel data; CONNECT revoked from PUBLIC (isolated demo only)
    for db in ("cbdb", "cbdb_reh"):
        assert psql1(name, f"CREATE DATABASE {db}", db="postgres").returncode == 0
        assert psql1(name, "CREATE TABLE sentinel(id int PRIMARY KEY, note text)", db=db).returncode == 0
        assert psql1(name, f"INSERT INTO sentinel VALUES (1,'legacy-{db}-untouched'),(2,'观察保留')", db=db).returncode == 0
        assert psql1(name, f"REVOKE CONNECT ON DATABASE {db} FROM PUBLIC", db="postgres").returncode == 0
    snap_before = {db: legacy_snapshot(name, db) for db in ("cbdb", "cbdb_reh")}
    ev["legacy_snapshots_before"] = snap_before
    # prerequisites (separate recorded steps, NOT loader actions)
    pre = {}
    for step, sql in [("postgis", "CREATE EXTENSION postgis"),
                      ("schema_harv", "CREATE SCHEMA harv"), ("schema_chgis", "CREATE SCHEMA chgis"),
                      ("marker_table", "CREATE TABLE public.xrg_instance_marker(instance_id text PRIMARY KEY)"),
                      ("marker_value", f"INSERT INTO public.xrg_instance_marker VALUES ('{cid}')"),
                      ("loader_role", f"CREATE ROLE {ROLE} NOLOGIN"),
                      ("grant_harv_chgis", f"GRANT USAGE, CREATE ON SCHEMA harv, chgis TO {ROLE}"),
                      ("grant_public_usage", f"GRANT USAGE ON SCHEMA public TO {ROLE}"),
                      ("grant_marker_select", f"GRANT SELECT ON public.xrg_instance_marker TO {ROLE}")]:
        rr = psql1(name, sql)
        pre[step] = rr.returncode
        assert rr.returncode == 0, rr.stderr[-200:]
    ev["prerequisite_steps_separate"] = pre
    pc = run(["python3", str(W / "prereq_check.py"), name, "xiangrugu", cid])
    ev["prereq_check"] = {"exit": pc.returncode, "report": json.loads(pc.stdout)}
    assert pc.returncode == 0
    scope = copy.deepcopy(SCOPE_BASE)
    scope["target_endpoint"] = {"dbname": "xiangrugu", "port": ext, "internal_port": 5432,
                                 "container_id": cid, "test_only": True}
    scope["endpoint_mapping_verified"] = f"docker port {name} 5432/tcp = {ports}; docker inspect Id verified"
    scope["instance_fingerprint"] = cid
    expected = {"contract_sha256": SCOPE_BASE["contract_sha256"],
                "inventory_sha256": SCOPE_BASE["inventory_sha256"],
                "evidence_shas": SCOPE_BASE["writeoff_evidence_sha256"],
                "instance_fingerprint": cid, "items": items_exp,
                "endpoint_mapping": {"external_port": ext, "internal_port": 5432,
                                      "container_id": cid, "verified": True}}
    artifacts = {"contract": CONTRACT, "inventory": INV_DOC, "evidence": EV_DOCS}
    parsed = contract_parse_fn(CONTRACT)
    recomputed = {"contract_sha256": parsed.sha256,
                  "inventory_sha256": pe._inventory_sha(INV_DOC),
                  "evidence_shas": {k: pe._evidence_sha(v) for k, v in EV_DOCS.items()}}
    ev["recomputed_at_driver"] = recomputed
    assert recomputed["contract_sha256"] == expected["contract_sha256"]
    assert recomputed["inventory_sha256"] == expected["inventory_sha256"]
    assert recomputed["evidence_shas"] == expected["evidence_shas"]
    ev["actual_invocation"] = {
        "external_client": " ".join(ext_prefix(ext)) + " -X -q -t --csv -v ON_ERROR_STOP=1",
        "role_switch": f"SET ROLE {ROLE};  (PsqlSession role parameter; NOLOGIN cannot direct-login)",
        "formal_mapping_reference": "pg32b 0.0.0.0:5433->5432/tcp (production, unchanged this box)"}

    def attempt(sc, exp, arts, label, exec_contract=None, db="xiangrugu", role=ROLE):
        s = session_for(ext, db=db, role=role)
        try:
            res = pe.run_production_load(s, sc, exec_contract or CONTRACT, payloads, exp, arts, contract_parse_fn)
            return {"label": label, "result": res}
        except fbl.LoaderGateError as e:
            return {"label": label, "refused": True, "code": e.code}
        finally:
            s.close()

    # Phase A: injected readback failure under loader role -> rollback zero residue
    bad = copy.deepcopy(expected); bad["items"]["m006642"]["attr_sha"] = "0" * 64
    ev["phase_A_injected"] = attempt(scope, bad, artifacts, "injected")
    residue = psql1(name, "SELECT count(*) FROM (SELECT unnest(ARRAY[" +
                    ",".join(f"'{t['schema_name']}.{t['table']}'" for t in fbl.targets_of(CONTRACT).values()) +
                    "]) AS n) s WHERE to_regclass(n) IS NOT NULL").stdout.strip()
    ev["phase_A_zero_residue"] = residue == "0"
    # Phase B: clean retry under loader role via external mapped port
    ev["phase_B_retry"] = attempt(scope, expected, artifacts, "retry")
    owners = psql1(name, "SELECT string_agg(DISTINCT tableowner, ',') FROM pg_tables WHERE schemaname IN ('harv','chgis')").stdout.strip()
    ev["phase_B_table_owners"] = owners
    # Phase C: independent counts (superuser readback)
    post, total = {}, 0
    for rid in fbl.FIRST_BATCH_RULES:
        t = fbl.targets_of(CONTRACT)[rid]
        n = int(psql1(name, f'SELECT count(*) FROM {t["schema_name"]}.{t["table"]}').stdout.strip())
        post[rid] = n; total += n
    ev["phase_C_counts"] = post
    ev["phase_C_total"] = total
    # Phase D: endpoint / identity / artifact negatives
    negs = {}
    negs["target_exists"] = attempt(scope, expected, artifacts, "target_exists").get("code")
    wrong_fp = copy.deepcopy(scope); wrong_fp["instance_fingerprint"] = "9" * 64
    wrong_fp_exp = copy.deepcopy(expected); wrong_fp_exp["instance_fingerprint"] = "9" * 64
    negs["wrong_instance"] = attempt(wrong_fp, wrong_fp_exp, artifacts, "wrong_instance").get("code")
    negs["wrong_database"] = attempt(scope, expected, artifacts, "wrong_db", db="cbdb", role=None).get("code")
    bad_map_ext = copy.deepcopy(expected); bad_map_ext["endpoint_mapping"]["external_port"] = 9999
    negs["external_mapping_mismatch"] = attempt(scope, bad_map_ext, artifacts, "ext_map").get("code")
    bad_map_int = copy.deepcopy(expected); bad_map_int["endpoint_mapping"]["internal_port"] = 5433
    negs["internal_mapping_mismatch"] = attempt(scope, bad_map_int, artifacts, "int_map").get("code")
    tampered = copy.deepcopy(CONTRACT); tampered["rules"][0]["targets"][0]["table"] = "tampered_table"
    arts2 = {"contract": tampered, "inventory": INV_DOC, "evidence": EV_DOCS}
    negs["artifact_changed_caller_consistent"] = attempt(scope, expected, arts2, "drift_recomputed").get("code")
    exec_bad = copy.deepcopy(CONTRACT); exec_bad["rules"][0]["targets"][0]["table"] = "other_execution_table"
    negs["execution_mismatch"] = attempt(scope, expected, artifacts, "exec_mismatch", exec_contract=exec_bad).get("code")
    arts_missing = copy.deepcopy(artifacts); del arts_missing["evidence"]["chgis"]
    negs["evidence_missing_chgis"] = attempt(scope, expected, arts_missing, "ev_missing").get("code")
    ev["phase_D_negatives"] = negs
    # Phase E: NOLOGIN role switch path + minimal-privilege negatives (live)
    role_ev = {}
    cu = psql1(name, f"SET ROLE {ROLE}; SELECT current_user").stdout.strip().splitlines()[-1]
    role_ev["set_role_current_user"] = cu
    for act, sql in [("marker_update", "UPDATE public.xrg_instance_marker SET instance_id='hacked'"),
                     ("marker_insert", "INSERT INTO public.xrg_instance_marker VALUES ('extra')"),
                     ("marker_delete", "DELETE FROM public.xrg_instance_marker"),
                     ("create_extension", "CREATE EXTENSION pgcrypto")]:
        rr = psql1(name, f"SET ROLE {ROLE}; {sql}")
        role_ev[act] = {"exit": rr.returncode, "denied": rr.returncode != 0 and "permission denied" in rr.stderr,
                        "stderr_tail": rr.stderr.strip().splitlines()[-1] if rr.stderr.strip() else ""}
    for db in ("cbdb", "cbdb_reh"):
        v = psql1(name, f"SELECT has_database_privilege('{ROLE}','{db}','CONNECT')").stdout.strip()
        role_ev[f"connect_{db}"] = v
    priv = psql1(name, f"SELECT has_table_privilege('{ROLE}','public.xrg_instance_marker','SELECT') || ',' || "
                       f"has_table_privilege('{ROLE}','public.xrg_instance_marker','UPDATE')").stdout.strip()
    role_ev["marker_priv_select_update"] = priv
    nologin = run(["docker", "exec", name, "psql", "-U", ROLE, "-d", "xiangrugu",
                   "-X", "-q", "-t", "--csv", "-c", "SELECT 1"])
    role_ev["nologin_direct"] = {"exit": nologin.returncode,
                                  "fatal_not_permitted": "not permitted to log in" in nologin.stderr,
                                  "channel": "local socket trust (docker exec); external host path hits password auth first",
                                  "stderr_tail": nologin.stderr.strip().splitlines()[-1] if nologin.stderr.strip() else ""}
    ev["phase_E_role"] = role_ev
    # Phase F: marker four-state live negatives with recorded restores (fixture-only, as postgres)
    marker_negs, restores = {}, {}
    psql1(name, "DELETE FROM public.xrg_instance_marker")
    marker_negs["empty"] = attempt(scope, expected, artifacts, "marker_empty").get("code")
    restores["reinsert"] = psql1(name, f"INSERT INTO public.xrg_instance_marker VALUES ('{cid}')").returncode
    psql1(name, "INSERT INTO public.xrg_instance_marker VALUES ('second-row')")
    marker_negs["multiple"] = attempt(scope, expected, artifacts, "marker_multiple").get("code")
    restores["del_second"] = psql1(name, "DELETE FROM public.xrg_instance_marker WHERE instance_id='second-row'").returncode
    psql1(name, "UPDATE public.xrg_instance_marker SET instance_id='wrong-value'")
    marker_negs["wrong_value"] = attempt(scope, expected, artifacts, "marker_wrong").get("code")
    restores["restore_value"] = psql1(name, f"UPDATE public.xrg_instance_marker SET instance_id='{cid}'").returncode
    psql1(name, "DROP TABLE public.xrg_instance_marker")
    marker_negs["table_missing"] = attempt(scope, expected, artifacts, "marker_no_table").get("code")
    restores["recreate"] = psql1(name, "CREATE TABLE public.xrg_instance_marker(instance_id text PRIMARY KEY)").returncode
    restores["revalue"] = psql1(name, f"INSERT INTO public.xrg_instance_marker VALUES ('{cid}')").returncode
    restores["regrant"] = psql1(name, f"GRANT SELECT ON public.xrg_instance_marker TO {ROLE}").returncode
    ev["phase_F_marker_negatives"] = marker_negs
    ev["phase_F_restores"] = restores
    total2 = sum(int(psql1(name, f'SELECT count(*) FROM {t["schema_name"]}.{t["table"]}').stdout.strip())
                 for t in fbl.targets_of(CONTRACT).values())
    ev["phase_D_zero_mutation"] = total2 == total == 47725
    snap_after = {db: legacy_snapshot(name, db) for db in ("cbdb", "cbdb_reh")}
    ev["legacy_snapshots_after"] = snap_after
    ev["legacy_untouched"] = snap_after == snap_before
    ev["cleanup"] = "container retained for a03 independent readback; removal only by verified Id after review"
    b = ev["phase_B_retry"].get("result", {})
    ok = (ev["phase_A_injected"].get("code") == "readback_mismatch" and ev["phase_A_zero_residue"]
          and b.get("status") == "FIRST_BATCH_TRIAL_LOAD_PASS" and total == 47725
          and owners == ROLE
          and b.get("target_identity_in_session", {}).get("legacy_databases_visible") == ["cbdb", "cbdb_reh"]
          and ev["external_path_session_port"] == "5432"
          and negs == {"target_exists": "target_already_exists", "wrong_instance": "marker_value_mismatch",
                        "wrong_database": "wrong_database",
                        "external_mapping_mismatch": "endpoint_mapping_mismatch",
                        "internal_mapping_mismatch": "endpoint_mapping_mismatch",
                        "artifact_changed_caller_consistent": "artifact_drift_recomputed",
                        "execution_mismatch": "contract_execution_mismatch",
                        "evidence_missing_chgis": "evidence_set_invalid"}
          and role_ev["set_role_current_user"] == ROLE
          and all(role_ev[a]["denied"] for a in ("marker_update", "marker_insert", "marker_delete", "create_extension"))
          and role_ev["connect_cbdb"] == "f" and role_ev["connect_cbdb_reh"] == "f"
          and role_ev["marker_priv_select_update"].strip('"') == "true,false"
          and role_ev["nologin_direct"]["fatal_not_permitted"]
          and marker_negs == {"empty": "marker_empty", "multiple": "marker_multiple_rows",
                               "wrong_value": "marker_value_mismatch", "table_missing": "marker_table_missing"}
          and all(v == 0 for v in restores.values())
          and ev["phase_D_zero_mutation"] and ev["legacy_untouched"])
    ev["trial_exit_pass"] = ok
    ev["status"] = "R55_TRIAL_PASS" if ok else "R55_TRIAL_FAIL"
    (W / "r55-trial-evidence.json").write_text(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print("R55", ev["status"], "| ext", ext, "->5432 | A", ev["phase_A_injected"].get("code"),
          "residue0", ev["phase_A_zero_residue"], "| B total", total, "owners", owners,
          "| D", negs, "| E role", {k: role_ev[k] for k in ("set_role_current_user", "connect_cbdb", "connect_cbdb_reh", "marker_priv_select_update")},
          "| F", marker_negs, "| legacy_untouched", ev["legacy_untouched"])
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
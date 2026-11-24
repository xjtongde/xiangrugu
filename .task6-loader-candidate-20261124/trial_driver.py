#!/usr/bin/env python3
"""First-batch loader candidate trial driver (host 32, stdlib + project canonical).

Same entry as unit tests: first_batch_loader.run_first_batch. Temporary unique-name
PostGIS container, --network none, no host ports. Source read-only. Never touches
pg32/pg32b/deploy. Cleanup only by verified container Id after the review window.
"""
import csv
import hashlib
import io
import json
import subprocess
import sys
import time
import uuid
import zipfile
from pathlib import Path

W = Path(__file__).resolve().parent
sys.path.insert(0, str(W / "src"))
sys.path.insert(0, str(W / "trial-text5"))
sys.path.insert(0, str(W / "trial-spatial2"))

from xiangrugu_datamgmt import canonical, first_batch_loader as fbl
import trial_text5 as t5
import trial_spatial2 as sp

IMAGE = "pg32b-full:18-pgdg"
APPROVED_IMAGE_ID = "sha256:d562e43664f996da0e4208b375c00c111a543d996475188d852e9189b2a8cd05"
CONTRACT = json.loads((W / "updated-frozen-candidate.json").read_text())
SCOPE = json.loads((W / "first-batch-scope.draft.json").read_text())
SV = json.loads((W / "source-side-expectations.json").read_text())
SV_BY_SID = {o["source_object_id"]: o for o in SV["objects"]}
WO = json.loads((W / "writeoff-result.json").read_text())


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def psql1(container, sql, db="xiangrugu_trial"):
    return run(["docker", "exec", container, "psql", "-U", "postgres", "-d", db,
                "-v", "ON_ERROR_STOP=1", "-t", "--csv", "-c", sql])


def formal_contract_sha():
    code = ("import json,sys;from xiangrugu_datamgmt.contracts import ReleaseContract;"
            "c=ReleaseContract.model_validate(json.load(sys.stdin));"
            "print(json.dumps({'sha':c.sha256,'status':c.status,'rules':len(c.rules)}))")
    r = subprocess.run(["docker", "exec", "-i", "xiangrugu-dev", "sh", "-c",
                        "PYTHONPATH=/tmp/lb/datamgmt/src python -c " + repr(code)],
                       input=json.dumps(CONTRACT), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]
    return json.loads(r.stdout.strip())


def text_payloads_expected():
    payloads, expected = {}, {}
    for obj in t5.APPROVED["objects"]:
        rid = obj["rule_id"]
        raw = (t5.ROOT / obj["source"]["path"]).read_bytes()
        assert sha(raw) == obj["source"]["sha256"], rid
        ncols = len(t5.VC_BY_RULE[rid]) - 1
        rows = t5.parse_rows(raw, rid, ncols)
        s = t5.stream_of(rid, rows)
        assert s.sha256 == obj["expected"]["sha256"] and len(rows) == obj["expected"]["row_count"], rid
        buf = io.StringIO()
        w = csv.writer(buf, delimiter="\t", quotechar='"', quoting=csv.QUOTE_ALL, lineterminator="\n")
        for i, r in enumerate(rows):
            w.writerow(list(r) + [i + 1])
        payloads[rid] = buf.getvalue()
        vc = t5.VC_BY_RULE[rid][:-1]
        meta = [[c["target_name"], "text", "text", "NO", str(i + 1)] for i, c in enumerate(vc)] \
            + [["__src_rownum", "bigint", "int8", "NO", str(len(vc) + 1)]]
        dup = (63, 74) if rid == "m008003" else (0, 0)
        expected[rid] = {"row_count": obj["expected"]["row_count"], "meta": meta,
                         "attr_sha": obj["expected"]["sha256"], "stream_bytes": obj["expected"]["stream_bytes"],
                         "source_object_id": obj["source_object_id"],
                         "dup_groups": dup[0], "dup_extra": dup[1]}
    return payloads, expected


def spatial_payloads_expected():
    payloads, expected = {}, {}
    inv = json.loads((t5.REL / "inventory.json").read_text())
    dbf_full = {e["archive_chain"][0]: e["sha256"] for e in inv["entries"]
                if e["relative_path"] == "harvard-full/doi_10_7910/DVN/E7HDYD/1884route.zip" and e["archive_chain"]}
    with zipfile.ZipFile(sp.ZIP) as zf:
        for obj in sp.OBJECTS:
            rid = obj["rule_id"]
            shp_raw, dbf_raw = zf.read(obj["stem"] + ".shp"), zf.read(obj["stem"] + ".dbf")
            assert sha(dbf_raw) == dbf_full[obj["stem"] + ".dbf"], rid
            columns = sp.ATTRS_BY_SID[obj["source_object_id"]]["source_columns"]
            points = sp.parse_shp(shp_raw)
            rows, fields, numrecords, deleted, blank = sp.parse_dbf(dbf_raw, columns, obj["codec"])
            assert len(points) == numrecords == len(rows) == 59 and deleted == 0 and not blank, rid
            s = sp.attr_stream(obj["source_object_id"], columns, rows)
            gs = sp.geom_stream(obj["source_object_id"], points)
            sv = SV_BY_SID[obj["source_object_id"]]
            assert s.sha256 == sv["attribute_expectation"]["sha256"], rid
            assert sha(gs) == sv["geometry_expectation"]["sha256"], rid
            buf = io.StringIO()
            w = csv.writer(buf, delimiter="\t", quotechar='"', quoting=csv.QUOTE_ALL, lineterminator="\n")
            for i, r in enumerate(rows):
                w.writerow(list(r) + [sp.ewkb_hex(points[i]["x_bytes"], points[i]["y_bytes"]), i + 1])
            payloads[rid] = buf.getvalue()
            meta = [[c["target_name"],
                     {"text": "text", "numeric(19,5)": "numeric", "bigint": "bigint"}[c["target_type_proposal"]],
                     {"text": "text", "numeric(19,5)": "numeric", "bigint": "int8"}[c["target_type_proposal"]],
                     "YES", str(i + 1)] for i, c in enumerate(columns)] \
                + [["geom", "USER-DEFINED", "geometry", "NO", str(len(columns) + 1)],
                   ["__src_rownum", "bigint", "int8", "NO", str(len(columns) + 2)]]
            expected[rid] = {"row_count": 59, "meta": meta,
                             "attr_sha": sv["attribute_expectation"]["sha256"],
                             "geom_sha": sv["geometry_expectation"]["sha256"],
                             "source_object_id": obj["source_object_id"],
                             "fields": fields, "points": points,
                             "attr_columns": [{"column_id": c["column_id"], "target_name": c["target_name"]}
                                               for c in columns],
                             "dup_groups": 0, "dup_extra": 0}
    return payloads, expected


def main():
    ev = {"version": 1, "trial_only": True, "image": IMAGE, "network": "none", "host_ports": "none",
          "pg32_pg32b_deploy_touched": False, "production_pg_connected": False}
    fc = formal_contract_sha()
    ev["formal_contract_parse"] = fc
    assert fc["sha"] == SCOPE["contract_sha256"] and fc["status"] == "frozen"
    tp, te = text_payloads_expected()
    sp_p, sp_e = spatial_payloads_expected()
    payloads = {**tp, **sp_p}
    items_exp = {**te, **sp_e}
    ev["source_gates"] = "PASS (text 5 sha/rows + spatial 2 attr/geom/DBF identity, all before write)"
    name = f"xiangrugu-loader-trial-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{uuid.uuid4().hex[:8]}"
    r = run(["docker", "run", "-d", "--name", name, "--network", "none",
             "-e", "POSTGRES_PASSWORD=trial-only-not-production", "-e", "POSTGRES_DB=xiangrugu_trial", IMAGE])
    ev["container_start_exit"] = r.returncode
    assert r.returncode == 0, r.stderr[-200:]
    cid = run(["docker", "inspect", "--format", "{{.Id}}", name]).stdout.strip()
    cname = run(["docker", "inspect", "--format", "{{.Name}}", name]).stdout.strip().lstrip("/")
    img = run(["docker", "inspect", "--format", "{{.Image}}", name]).stdout.strip()
    ev["container"] = {"name": name, "id": cid, "name_verified": cname == name, "image_id": img}
    assert cname == name and len(cid) == 64 and img == APPROVED_IMAGE_ID
    ready = False
    for _ in range(90):
        r1 = run(["docker", "exec", name, "psql", "-U", "postgres", "-d", "postgres", "-t", "--csv", "-c", "SELECT 1"])
        if r1.returncode == 0:
            time.sleep(2)
            r2 = run(["docker", "exec", name, "psql", "-U", "postgres", "-d", "postgres", "-t", "--csv", "-c", "SELECT 1"])
            if r2.returncode == 0:
                ready = True
                break
        time.sleep(1)
    assert ready, "PG_NOT_READY"
    ident = {}
    for key, sql in [("server_version", "SHOW server_version"),
                     ("inet_server_addr", "SELECT coalesce(inet_server_addr()::text,'null')"),
                     ("databases", "SELECT string_agg(datname, ',' ORDER BY datname) FROM pg_database")]:
        ident[key] = psql1(name, sql, db="postgres").stdout.strip()
    ev["instance_identity_observed"] = ident
    expected_identity = {"container_id": cid, "image_id": img, "server_version": ident["server_version"],
                          "inet_server_addr": "null", "databases": ident["databases"]}
    assert ident["server_version"].startswith("18") and ident["inet_server_addr"] == "null"
    assert "cbdb" not in ident["databases"] and "pg32b" not in ident["databases"]
    expected = {"contract_sha256": fc["sha"],
                "inventory_sha256": "fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db",
                "evidence_shas": WO["run_evidence_sha256"],
                "instance_identity": expected_identity, "items": items_exp}
    session = fbl.PsqlSession(["docker", "exec", "-i", name, "psql", "-U", "postgres", "-d", "xiangrugu_trial"])
    try:
        result = fbl.run_first_batch(session, SCOPE, CONTRACT, payloads, expected_identity, expected)
        ev["load_result"] = result
        ev["status"] = result["status"]
    except fbl.LoaderGateError as e:
        ev["status"] = "GATE_STOP"; ev["gate_code"] = e.code; ev["gate_message"] = str(e)
        (W / "trial-evidence.json").write_text(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
        print(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True)); sys.exit(2)
    finally:
        session.close()
    # independent post-commit readback (separate psql invocations)
    total = 0
    post = {}
    for rid in fbl.FIRST_BATCH_RULES:
        t = fbl.targets_of(CONTRACT)[rid]
        n = int(psql1(name, f'SELECT count(*) FROM {t["schema_name"]}.{t["table"]}').stdout.strip())
        post[rid] = n; total += n
    ev["post_commit_counts"] = post
    ev["post_commit_total"] = total
    ev["total_matches_47725"] = total == 47725
    # live negative 1: re-run must refuse (targets exist), zero mutation
    session2 = fbl.PsqlSession(["docker", "exec", "-i", name, "psql", "-U", "postgres", "-d", "xiangrugu_trial"])
    try:
        fbl.run_first_batch(session2, SCOPE, CONTRACT, payloads, expected_identity, expected)
        ev["negative_target_exists"] = "NOT_REFUSED_BUG"
    except fbl.LoaderGateError as e:
        ev["negative_target_exists"] = {"refused": True, "code": e.code}
    finally:
        session2.close()
    total2 = sum(int(psql1(name, f'SELECT count(*) FROM {t["schema_name"]}.{t["table"]}').stdout.strip())
                 for t in fbl.targets_of(CONTRACT).values())
    ev["negative_zero_mutation"] = total2 == total == 47725
    # live negative 2: wrong instance identity refused before write
    bad_identity = dict(expected_identity); bad_identity["container_id"] = "9" * 64
    session3 = fbl.PsqlSession(["docker", "exec", "-i", name, "psql", "-U", "postgres", "-d", "xiangrugu_trial"])
    try:
        fbl.run_first_batch(session3, SCOPE, CONTRACT, payloads, bad_identity, expected)
        ev["negative_instance"] = "NOT_REFUSED_BUG"
    except fbl.LoaderGateError as e:
        ev["negative_instance"] = {"refused": True, "code": e.code}
    finally:
        session3.close()
    ev["cleanup"] = "container retained for a03 independent readback; removal only by verified Id after review"
    ok = (ev["status"] == "FIRST_BATCH_TRIAL_LOAD_PASS" and ev["total_matches_47725"]
          and ev["negative_target_exists"].get("refused") and ev["negative_target_exists"].get("code") == "target_already_exists"
          and ev["negative_zero_mutation"] and ev["negative_instance"].get("code") == "instance_identity_mismatch")
    ev["trial_exit_pass"] = ok
    (W / "trial-evidence.json").write_text(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print("TRIAL", ev["status"], "total", total, "neg1", ev["negative_target_exists"],
          "neg2", ev["negative_instance"], "zero_mutation", ev["negative_zero_mutation"])
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""首批七表正式执行命令（单会话单连接，禁切库禁重连）。

正式目标固定 pg32b:5433/xiangrugu（外部映射）→ 会话内 5432。
运行要求：CWD = 受控 repo 根（deploy 或隔离试装树）；源件只读。
  第一阶段隔离验证: python3 formal_first_batch.py --isolated --port <EXT> \
      --instance-id <容器Id> --password-container <临时容器名> --out ev.json
  第二阶段正式执行: python3 formal_first_batch.py --real --port 5433 \
      --instance-id <pg32b Id> --password-container pg32b \
      --approval-ref <审批原文路径> --out ev.json
安全定点（R57）：
  - --real 审批原文完整 SHA-256 钉死 88f4f1ac…；任意/篡改/测试审批连接前拒。
  - 正式模式固定 pg32b 实例+外部 5433；隔离模式拒绝正式实例与端点。
  - 禁止正式模式注入测试故障。
  - 合同解析用受控接收版本（--parse-src，默认 deploy），逐文件 sha 绑定入证；无 /tmp/lb 默认。
  - 凭据仅经进程 env 传递（docker run -e PGPASSWORD 无值形式），不入 argv/日志/证据。
  - 空间几何事务内 ST_AsEWKB 字节重算摘要（geom_ewkb_sha）后再决定提交。
"""
import argparse
import copy
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "datamgmt/src"))
sys.path.insert(0, str(ROOT / ".task6-trial-text5-20261123"))
sys.path.insert(0, str(ROOT / ".task6-trial-spatial2-20261123"))
from xiangrugu_datamgmt import first_batch_loader as fbl
from xiangrugu_datamgmt import production_entry as pe
import trial_text5 as t5
import trial_spatial2 as sp

EXC = ROOT / ".task6-exception-integration-20261124"
CONTRACT = json.loads((EXC / "updated-frozen-candidate.json").read_text())
INV_DOC = json.loads((ROOT / "datamgmt/contracts/releases/2026-10-06-bootstrap/inventory.json").read_text())
EV_DOCS = {"nul": json.loads((EXC / "nul-evidence.json").read_text()),
           "chgis": json.loads((EXC / "chgis-evidence.json").read_text())}
WO = json.loads((EXC / "writeoff-result.json").read_text())
SV = json.loads((ROOT / ".task6-spatial-values-20261123/source-side-expectations.json").read_text())
SV_BY_SID = {o["source_object_id"]: o for o in SV["objects"]}
SCOPE_BASE = json.loads((ROOT / ".task6-production-entry-20261125/production-scope.draft.json").read_text())
ANCHOR_CONTRACT = "ba8118fb5188478c7a891c37a0ae9d84687910c472946fe44709f3533843bd62"
ANCHOR_INVENTORY = "fb5e6b334b898d62dc0e5c77094fdb50e0946300e6e3009f447b2ecd1bc216db"
APPROVAL_SHA256 = "88f4f1acebbf03536a386d16d13ba8c229253a31eb02db11b56cef34170753b5"
SEVEN = ["m002709", "m002717", "m004812", "m006642", "m008002", "m008003", "m008004"]
ROLE = "xiangrugu_loader"
IMAGE = "pg32b-full:18-pgdg"
FORMAL_CONTAINERS = ("pg32b", "pg32")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(cmd, env=None, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, env=env, **kw)


def stop(ev, out, status, code=2):
    ev["status"], ev["exit"] = status, code
    Path(out).write_text(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print(status, "exit", code)
    sys.exit(code)


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
            ewkb_expected = sha(b"".join(bytes.fromhex(sp.ewkb_hex(p["x_bytes"], p["y_bytes"])) for p in points))
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
                             "geom_ewkb_sha": ewkb_expected,
                             "source_object_id": obj["source_object_id"],
                             "fields": fields, "points": points,
                             "attr_columns": [{"column_id": c["column_id"], "target_name": c["target_name"]}
                                               for c in columns],
                             "dup_groups": 0, "dup_extra": 0}
    return payloads, expected


def contract_parse_fn(doc, parse_pp):
    code = ("import json,sys;from xiangrugu_datamgmt.contracts import ReleaseContract;"
            "c=ReleaseContract.model_validate(json.load(sys.stdin));"
            "print(json.dumps({'sha':c.sha256,'doc':c.model_dump(by_alias=True)}))")
    r = subprocess.run(["docker", "exec", "-i", "xiangrugu-dev", "sh", "-c",
                        f"PYTHONPATH={parse_pp} python -c " + repr(code)],
                       input=json.dumps(doc), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]
    out = json.loads(r.stdout.strip())
    return SimpleNamespace(sha256=out["sha"], model_dump=lambda by_alias=False: out["doc"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--instance-id", required=True)
    ap.add_argument("--password-container", required=True)
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--isolated", action="store_true")
    ap.add_argument("--approval-ref")
    ap.add_argument("--inject-failure")
    ap.add_argument("--out", required=True)
    ap.add_argument("--parse-src", default="/opt/mydocker/xiangrugu/deploy/datamgmt/src")
    a = ap.parse_args()
    ev = {"version": 1, "command": "formal_first_batch.py", "cwd": str(ROOT),
          "single_session_single_connection": True, "database_switch_forbidden": True,
          "source_read_only": True, "role": ROLE, "credentials_in_argv_or_evidence": False}
    # ---- pre-connection gates (no PG connection, docker metadata only) ----
    if a.real == a.isolated:
        stop(ev, a.out, "MODE_MUTUALLY_EXCLUSIVE")
    pg32b_id = run(["docker", "inspect", "--format", "{{.Id}}", "pg32b"]).stdout.strip()
    if a.real:
        if a.inject_failure:
            stop(ev, a.out, "INJECTION_FORBIDDEN_IN_REAL")
        if a.password_container != "pg32b" or a.port != 5433:
            stop(ev, a.out, "REAL_MODE_FIXED_TO_PG32B_5433")
        if a.instance_id != pg32b_id:
            stop(ev, a.out, "REAL_INSTANCE_ID_MISMATCH")
        if not a.approval_ref or not Path(a.approval_ref).exists():
            stop(ev, a.out, "APPROVAL_FILE_MISSING")
        approval_sha = sha(Path(a.approval_ref).read_bytes())
        ev["approval_sha256"] = approval_sha
        ev["approval_sha256_pinned"] = APPROVAL_SHA256
        if approval_sha != APPROVAL_SHA256:
            stop(ev, a.out, "APPROVAL_SHA_MISMATCH")
        ev["approval_verified_before_connect"] = True
    else:
        if a.password_container in FORMAL_CONTAINERS or a.port == 5433 or a.instance_id == pg32b_id:
            stop(ev, a.out, "FORMAL_INSTANCE_OR_ENDPOINT_IN_ISOLATED_MODE")
    cid = run(["docker", "inspect", "--format", "{{.Id}}", a.password_container]).stdout.strip()
    if cid != a.instance_id:
        stop(ev, a.out, "INSTANCE_ID_MISMATCH")
    ports = run(["docker", "port", a.password_container, "5432/tcp"]).stdout.strip()
    if not any(line.endswith(f":{a.port}") for line in ports.splitlines()):
        ev["ports"] = ports
        stop(ev, a.out, "ENDPOINT_MAPPING_MISMATCH")
    ev["endpoint_mapping_independent"] = {"docker_port_output": ports, "external_port": a.port,
                                           "internal_port": 5432, "container_id": cid}
    # ---- parse version binding: controlled received src, per-file sha verified ----
    parse_src = Path(a.parse_src)
    if not (parse_src / "xiangrugu_datamgmt/contracts.py").exists():
        stop(ev, a.out, "PARSE_SRC_NOT_RECEIVED_TREE")
    run(["docker", "exec", "xiangrugu-dev", "rm", "-rf", "/tmp/formal-parse-src"])
    tar_p = subprocess.Popen(["tar", "cf", "-", "-C", str(parse_src.parent), parse_src.name],
                             stdout=subprocess.PIPE)
    cp = subprocess.run(["docker", "exec", "-i", "xiangrugu-dev", "sh", "-c",
                         "mkdir -p /tmp/formal-parse-src && tar xf - -C /tmp/formal-parse-src --strip-components=1"],
                        stdin=tar_p.stdout, capture_output=True, text=True)
    tar_p.stdout.close()
    tar_p.wait()
    if cp.returncode != 0 or tar_p.returncode != 0:
        stop(ev, a.out, "PARSE_SRC_COPY_FAILED")
    host_sum = run(["sh", "-c", f"cd {parse_src} && find . -name '*.py' | LC_ALL=C sort | xargs sha256sum"]).stdout
    cont_sum = run(["docker", "exec", "xiangrugu-dev", "sh", "-c",
                    "cd /tmp/formal-parse-src && find . -name '*.py' | LC_ALL=C sort | xargs sha256sum"]).stdout
    if host_sum != cont_sum or not host_sum:
        stop(ev, a.out, "PARSE_VERSION_BINDING_MISMATCH")
    ev["parse_version_binding"] = {"source": str(parse_src), "container_path": "/tmp/formal-parse-src",
                                    "files_verified": len(host_sum.splitlines()), "mismatch": 0,
                                    "contracts_py_sha256": sha((parse_src / "xiangrugu_datamgmt/contracts.py").read_bytes())}
    parse_pp = "/tmp/formal-parse-src"
    # ---- runtime credential: process env only, never argv ----
    pw = run(["docker", "inspect", "--format", "{{range .Config.Env}}{{println .}}{{end}}",
              a.password_container]).stdout
    pw = next(l.split("=", 1)[1] for l in pw.splitlines() if l.startswith("POSTGRES_PASSWORD="))
    cred_env = {**os.environ, "PGPASSWORD": pw}
    ev["auth"] = {"method": "scram-sha-256 via published port",
                  "password_channel": "process env only (docker run -e PGPASSWORD valueless)",
                  "password_committed": False}

    def prefix(db="xiangrugu"):
        return ["docker", "run", "--rm", "-i", "--network", "host", "-e", "PGPASSWORD",
                IMAGE, "psql", "-h", "127.0.0.1", "-p", str(a.port), "-U", "postgres", "-d", db]

    probe = run(prefix() + ["-X", "-q", "-t", "--csv", "-c",
                            "SELECT current_database() || '|' || current_setting('port') || '|' || "
                            "coalesce(inet_server_addr()::text,'null')"], env=cred_env)
    assert probe.returncode == 0, probe.stderr[-200:]
    pdb, pport, paddr = probe.stdout.strip().split("|")
    ev["probe_via_external_path"] = {"dbname": pdb, "internal_port": pport, "inet_server_addr": paddr}
    assert pdb == "xiangrugu" and pport == "5432"
    tp, te = text_payloads_expected()
    sp_p, sp_e = spatial_payloads_expected()
    payloads = {**tp, **sp_p}
    items = {**te, **sp_e}
    assert sorted(items) == sorted(SEVEN)
    ev["source_gates"] = "PASS (source sha/rows/attr/geom/DBF/EWKB-expected identity asserted before write)"
    scope = copy.deepcopy(SCOPE_BASE)
    scope["instance_fingerprint"] = cid
    scope["endpoint_mapping_verified"] = f"docker port {a.password_container} 5432/tcp = {ports}; inspect Id=={cid[:12]}"
    expected = {"contract_sha256": ANCHOR_CONTRACT, "inventory_sha256": ANCHOR_INVENTORY,
                "evidence_shas": WO["run_evidence_sha256"], "instance_fingerprint": cid, "items": items,
                "endpoint_mapping": {"external_port": a.port, "internal_port": 5432,
                                      "container_id": cid, "verified": True},
                "server_addr": paddr}
    assert scope["contract_sha256"] == ANCHOR_CONTRACT and scope["inventory_sha256"] == ANCHOR_INVENTORY
    assert scope["writeoff_evidence_sha256"] == WO["run_evidence_sha256"]
    if a.real:
        scope["target_endpoint"] = {"host": "pg32b", "port": 5433, "internal_port": 5432, "dbname": "xiangrugu"}
        scope["write_approval"] = {"approved_by": "茶香", "approved_at": "2026-11-25T16:09:11Z",
                                    "approval_ref": f"real-write-approval-20261125.txt sha256:{APPROVAL_SHA256}",
                                    "approval_class": "real", "bound_object_rule_ids": SEVEN}
        scope["real_authority_ref"] = f"sha256:{APPROVAL_SHA256} (茶香授权原文，禁止测试审批代替)"
    else:
        scope["target_endpoint"] = {"dbname": "xiangrugu", "port": a.port, "internal_port": 5432,
                                     "container_id": cid, "test_only": True}
        scope["write_approval"]["approval_class"] = "test"
        scope["write_approval"]["bound_object_rule_ids"] = SEVEN
    if a.inject_failure:
        items[a.inject_failure]["attr_sha"] = "0" * 64
        ev["injected_failure"] = a.inject_failure
    artifacts = {"contract": CONTRACT, "inventory": INV_DOC, "evidence": EV_DOCS}
    session = fbl.PsqlSession(prefix(), role=ROLE, env=cred_env)
    try:
        cu = fbl._rows_csv(session.query_csv("SELECT current_user"))[0][0]
        ev["same_session_current_user"] = cu
        if cu != ROLE:
            stop(ev, a.out, "ROLE_SWITCH_FAILED")
        res = pe.run_production_load(session, scope, CONTRACT, payloads, expected, artifacts,
                                     lambda d: contract_parse_fn(d, parse_pp))
        ev["result"] = res
        ev["status"] = res.get("status")
        ev["exit"] = 0 if res.get("status") == "FIRST_BATCH_TRIAL_LOAD_PASS" else 3
    except fbl.LoaderGateError as e:
        ev["refused"], ev["gate_code"], ev["exit"] = True, e.code, 2
        ev["status"] = "REFUSED_" + e.code
    finally:
        session.close()
    Path(a.out).write_text(json.dumps(ev, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print(ev["status"], "exit", ev["exit"], "| port", a.port, "->5432 | current_user", ev.get("same_session_current_user"),
          "| total", (ev.get("result") or {}).get("total_rows"))
    sys.exit(ev["exit"])


if __name__ == "__main__":
    main()
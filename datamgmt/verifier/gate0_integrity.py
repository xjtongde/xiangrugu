#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
闸0 源件完整性（阶段一起步件）

对权威源 usedata/ 逐件 sha256，对照三份校验账（我方两账＋发布方一账）。
只读源件、不写库、不改源件。结果打印 JSON 并落 datamgmt/recon/gate0_integrity.json。

数字纪律（P-20）：每账记录 checked/passed/failed/missing 四处，路径基与缺陷均注明。
"""
import hashlib
import json
import os
import re
import sys
import time

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
_DM_DIR = os.path.dirname(_MODULE_DIR)          # datamgmt/
_RECON_DIR = os.path.join(_DM_DIR, "recon")
_ROOTS = os.path.join(_DM_DIR, "config", "roots.yaml")


def load_usedata_root():
    """P-17：根只许出自 config/roots.yaml，代码不硬编码绝对路径。

    优先 yaml.safe_load；无 pyyaml 时按本文件稳定结构做最小提取
    （找 "  usedata:" 块内紧跟的 "path:" 行）。
    """
    txt = open(_ROOTS, encoding="utf-8").read()
    try:
        import yaml  # type: ignore
        d = yaml.safe_load(txt)
        return d["roots"]["usedata"]["path"]
    except ImportError:
        lines = txt.splitlines()
        for i, ln in enumerate(lines):
            if re.match(r"^  usedata:\s*(#.*)?$", ln):
                for ln2 in lines[i + 1:i + 3]:
                    m = re.match(r"^\s+path:\s*(\S+)\s*(#.*)?$", ln2)
                    if m:
                        return m.group(1)
        sys.exit("gate0: 无法从 config/roots.yaml 提取 roots.usedata.path")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_account(path):
    """解析校验账：每行 '<sha256>  <path>'；跳过空行与 '#' 注记。"""
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) == 2 and re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
                out.append((parts[0].lower(), parts[1].strip()))
    return out


def main():
    root = load_usedata_root()
    accounts = [
        ("我方二批账(b2)",      os.path.join(root, "SHA256SUMS-b2"),           root,
         "路径相对 usedata/"),
        ("我方首批账(harvard)", os.path.join(root, "harvard", "SHA256SUMS"),   os.path.join(root, "harvard"),
         "路径相对 harvard/（'./'前缀）"),
        ("发布方账(chgis)",     os.path.join(root, "harvard", "chgis", "SHA256SUMS.txt"),
         os.path.join(root, "harvard", "chgis"),
         "发布方原档；自身缺陷：缺 v6_time_pref_pgn 多边形件、且列表含 China_Periods_ReignDates.zip（实居 chgis-v6/，本账以其在 chgis/ 路径列出）"),
    ]

    t0 = time.time()
    report = {"root": root, "as_of_computed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "accounts": [], "totals": {"checked": 0, "passed": 0, "failed": 0, "missing": 0}}

    for label, sums_path, base, note in accounts:
        acc = {"label": label, "base": base, "note": note,
               "checked": 0, "passed": 0, "failed": [], "missing": []}
        for digest, rel in parse_account(sums_path):
            rel = rel.lstrip("./")
            p = os.path.join(base, rel)
            acc["checked"] += 1
            if not os.path.exists(p):
                acc["missing"].append(rel)
                continue
            got = sha256_of(p)
            if got == digest:
                acc["passed"] += 1
            else:
                acc["failed"].append(rel)
        report["accounts"].append(acc)
        report["totals"]["checked"] += acc["checked"]
        report["totals"]["passed"] += acc["passed"]
        report["totals"]["failed"] += len(acc["failed"])
        report["totals"]["missing"] += len(acc["missing"])

    report["elapsed_sec"] = round(time.time() - t0, 1)
    os.makedirs(_RECON_DIR, exist_ok=True)
    out = os.path.join(_RECON_DIR, "gate0_integrity.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""check_decode.py —— 全量扫 705 shapefile，找按 decoding.yaml 严格解码会失败的列，并给出候选正确编码。

方法（§5.4 判定法落地）：每 C 列抽样 ≤50 条非删除记录，用判表定的编码 strict 试解；
首个失败即记 (target, col, assigned, 样本字节 hex)。对失败列再按候选编码全列扫，确认无替解码之候选。
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DM = os.path.dirname(_HERE)
sys.path.insert(0, _DM)

import decode  # noqa: E402
from truth import dbf  # noqa: E402
from truth import srcopen  # noqa: E402

CFG = os.path.join(_DM, "config", "sources.yaml")
CANDIDATES = ("utf-8", "gb18030", "big5", "gbk", "cp1251", "cp1252", "cp1253", "cp932")


def _entries():
    out = []
    for line in open(CFG, encoding="utf-8"):
        s = line.strip()
        if s.startswith("- "):
            out.append(json.loads(s[2:]))
    return out


def _col_field_index(fields, name):
    return next(i for i, f in enumerate(fields) if f["name"] == name)


def main():
    fams = decode.load_decoding()
    issues = []
    checked = 0
    for e in _entries():
        if e["carrier"] != "shapefile" or e.get("geometry_only"):
            continue
        fam = fams.get(e.get("decoding"))
        b = srcopen.read_member(e["key"], ".dbf", required=True)
        fields = dbf.parse_dbf(b)["fields"]
        for f in fields:
            if f["type"] not in ("C", "D", "L", "M"):
                continue
            enc = decode.col_encoding(fam, f["name"])
            if enc is None:
                continue
            fi = _col_field_index(fields, f["name"])
            # 抽样 ≤50 条找首个失败
            sample = None
            seen = 0
            for vals, deleted in dbf.iter_records(b):
                if deleted:
                    continue
                raw = vals[fi].rstrip(b" \x00")
                if not raw:
                    continue
                seen += 1
                try:
                    raw.decode(enc)
                except UnicodeDecodeError:
                    sample = raw
                    break
                if seen >= 50:
                    break
            if sample is None:
                continue
            # 候选编码全列扫（确认能 100% 解）
            good = []
            for c in CANDIDATES:
                ok = True
                for vals, deleted in dbf.iter_records(b):
                    if deleted:
                        continue
                    raw = vals[fi].rstrip(b" \x00")
                    if not raw:
                        continue
                    try:
                        raw.decode(c)
                    except UnicodeDecodeError:
                        ok = False
                        break
                if ok:
                    good.append(c)
            checked += 1
            issues.append({
                "target": e["target"], "col": f["name"], "assigned": enc,
                "sample_hex": sample.hex(), "sample_char": sample.decode("cp1252", "replace"),
                "decodes_fully": good,
            })
    out = os.path.join(_DM, "recon", "check_decode.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"n_issues": len(issues), "issues": issues}, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("失败列数:", len(issues))
    for it in issues:
        print(f"  {it['target']:40s} {it['col']:16s} assigned={it['assigned']:7s} sample={it['sample_char'][:14]!r} -> {it['decodes_fully']}")
    print("结果落:", out)


if __name__ == "__main__":
    main()
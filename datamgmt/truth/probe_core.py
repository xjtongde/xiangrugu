# -*- coding: utf-8 -*-
"""truth.probe_core —— 阶段一体检：非 shapefile 直载件（CBDB sqlite、tab、xls）真值基线。

产出（落 datamgmt/recon/）：
  - cbdb_baseline.json   两版 CBDB（20260919 权威 vs 20240208 旧档）表/行/列 + 关键表差异
  - tab_baseline.json    五份 .tab 的行/列/编码
  - xls_baseline.json    两份 .xls 的魔数与可读性（无 xlrd 时留待阶段二）
"""
import json
import os

from . import read_text, sqlite as sqlite_mod, roots as roots_mod

RECON = os.path.join(os.path.dirname(__file__), "..", "recon")


def _dump(name, obj):
    os.makedirs(RECON, exist_ok=True)
    p = os.path.join(RECON, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
    return p


def probe_cbdb():
    root = roots_mod.usedata()
    versions = {
        "20260919（权威源 harvard/cbdb）":
            os.path.join(root, "harvard", "cbdb", "cbdb_20260919.sqlite3"),
        "20240208（harvard-full 旧档）":
            os.path.join(root, "harvard-full", "doi_10_7910", "DVN", "PAGGQS",
                         "CBDB_20240208_sqlite.db"),
    }
    out = {"versions": {}}
    for label, p in versions.items():
        entry = {"path": p}
        if not os.path.exists(p):
            entry["error"] = "missing"
        else:
            head = open(p, "rb").read(16)
            if head[:16] != b"SQLite format 3\x00":
                entry["error"] = f"not sqlite: magic={head[:16]!r}"
                entry["magic"] = head[:16].hex()
            else:
                try:
                    tables = sqlite_mod.probe_sqlite(p)
                    entry["tables"] = tables
                    entry["n_tables"] = sum(1 for t in tables if t["kind"] == "table")
                    entry["total_rows"] = sum(t["rows"] or 0 for t in tables if t["kind"] == "table")
                except Exception as e:  # noqa: BLE001
                    entry["error"] = str(e)
        out["versions"][label] = entry
    # 关键表交叉
    def bio_main(lbl):
        v = out["versions"].get(lbl, {})
        for t in (v.get("tables") or []):
            if t.get("name") == "BIOG_MAIN" and t.get("kind") == "table":
                return {"rows": t["rows"], "n_cols": len(t["columns"])}
        key = [t["name"] for t in (v.get("tables") or []) if "BIOG" in t.get("name", "")]
        return {"rows": None, "n_cols": None, "note": f"BIOG 系表={key}"}
    out["BIOG_MAIN_compare"] = {lbl: bio_main(lbl) for lbl in out["versions"]}
    return _dump("cbdb_baseline.json", out)


def probe_tabs():
    root = roots_mod.usedata()
    tabfiles = [
        "harvard/tab/ACADEMY_Data.tab",
        "harvard/tab/Index_of_the_Complete_Prose_of_the_Yuan_Dynasty_vol_1-60.tab",
        "harvard/tab/writings of the 19c missionaries in China.tab",
        "harvard-full/doi_10_7910/DVN/MI56KU/2001_Shanghai_0_INDEX_OF_PRESENTATIONS.tab",
        "harvard-full/doi_10_7910/DVN/SK7KGK/GB_91_HZ_040201_UTF8.tab",
    ]
    rows = []
    for rel in tabfiles:
        p = os.path.join(root, rel)
        if os.path.exists(p):
            rows.append(read_text.probe_dsv(p))
        else:
            rows.append({"path": rel, "error": "missing"})
    return _dump("tab_baseline.json", rows)


def probe_xls():
    root = roots_mod.usedata()
    xlsfiles = [
        "harvard-full/doi_10_7910/DVN/EOH3FV/1999_gb_pop_uce.xls",
        "harvard-full/doi_10_7910/DVN/PRCLTU/THDL_ADMareas_rev022401.xls",
    ]
    rows = []
    for rel in xlsfiles:
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            rows.append({"path": rel, "error": "missing"})
            continue
        head = open(p, "rb").read(8)
        ole2 = head == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        rows.append({
            "path": rel,
            "magic": head.hex(),
            "is_ole2_xls": ole2,
            "readable_now": False,
            "note": "无 xlrd/openpyxl/libreoffice；BIFF 直读留待阶段二判定表（列/行数届时补）",
        })
    return _dump("xls_baseline.json", rows)


def main():
    p1 = probe_cbdb()
    p2 = probe_tabs()
    p3 = probe_xls()
    print(json.dumps({"cbdb": p1, "tab": p2, "xls": p3}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
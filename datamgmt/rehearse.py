# -*- coding: utf-8 -*-
"""rehearse.py —— 段B 全量彩排驱动：遍历 sources.yaml 逐源「落 staging → 过闸 → 通过则换名」。

尽收结果（verdict/行数/耗时/错误）写 recon/rehearse_b.json。正式库 cbdb 不在此列；彩排靶=临时库。
"""
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
RECON = os.path.join(_HERE, "recon")

from importer import load  # noqa: E402
from verifier import verify  # noqa: E402


def _entry_rows(entry):
    return entry.get("truth_rows")


def run_sqlite(db="cbdb_reh", only=None, promote=True):
    results = []
    entries = [e for e in load.load_entries() if e["carrier"] == "sqlite"]
    for i, e in enumerate(entries):
        if only and only not in e["target"]:
            continue
        t0 = time.time()
        rec = {"target": e["target"], "carrier": "sqlite", "rows": _entry_rows(e)}
        try:
            stg, cols, types, nrows = load.load_sqlite_staging(db, e)
            r = verify.verify_sqlite(db, e)
            rec["verdict"] = r["verdict"]
            rec["rows"] = nrows
            if r["verdict"] == "CONFORMS" and promote:
                load.promote(db, e)
        except Exception as ex:  # noqa: BLE001
            rec["verdict"] = "ERROR"
            rec["err"] = str(ex)[:300]
        rec["sec"] = round(time.time() - t0, 1)
        results.append(rec)
        print(f"[{i+1}/{len(entries)}] {rec['target']:42s} {rec.get('rows', '?')!s:>8} 行  -> {rec['verdict']}  {rec['sec']}s", flush=True)
    return results


def run_shapefile(db="cbdb_reh", only=None, promote=True):
    results = []
    entries = [e for e in load.load_entries() if e["carrier"] == "shapefile"]
    for i, e in enumerate(entries):
        if only and only not in e["target"]:
            continue
        t0 = time.time()
        rec = {"target": e["target"], "carrier": "shapefile", "rows": _entry_rows(e),
               "srid": e["geom"]["srid"], "geom_only": bool(e.get("geometry_only"))}
        try:
            if rec["geom_only"]:
                gtab, n = load.load_shapefile_geom(db, e)
                r = verify.verify_shapefile_geom(db, e)
                rec["rows"], rec["verdict"] = n, r["verdict"]
                if r["verdict"] == "CONFORMS" and promote:
                    load.promote_geom_only(db, e)
            else:
                stg, cols, types, n = load.load_shapefile_staging(db, e)
                r = verify.verify_shapefile(db, e)
                rec["rows"] = n
                if r["verdict"] != "CONFORMS":
                    rec["verdict"] = r["verdict"]
                else:
                    load.load_shapefile_geom(db, e)
                    rg = verify.verify_shapefile_geom(db, e)
                    if rg["verdict"] != "CONFORMS":
                        rec["verdict"] = "FAIL_geom"
                        rec["geom"] = {k: v for k, v in rg.items() if k.startswith("g")}
                    else:
                        rec["verdict"] = "CONFORMS"
                        if promote:
                            load.assemble_shapefile(db, e)
        except Exception as ex:  # noqa: BLE001
            rec["verdict"] = "ERROR"
            rec["err"] = str(ex)[:300]
        rec["sec"] = round(time.time() - t0, 1)
        results.append(rec)
        print(f"[{i+1}/{len(entries)}] {rec['target'][6:]:44s} {str(rec.get('rows', '?')):>8} srid={rec['srid']:>4} -> {rec['verdict']}  {rec['sec']}s", flush=True)
    return results


def run_text(db, carrier, only=None, promote=True):
    results = []
    entries = [e for e in load.load_entries() if e["carrier"] == carrier]
    for i, e in enumerate(entries):
        if only and only not in e["target"]:
            continue
        t0 = time.time()
        rec = {"target": e["target"], "carrier": carrier, "rows": _entry_rows(e)}
        try:
            if carrier == "tsv":
                stg, cols, types, nrows = load.load_tsv_staging(db, e)
                r = verify.verify_tsv(db, e)
            else:
                stg, cols, types, nrows = load.load_xls_staging(db, e)
                r = verify.verify_xls(db, e)
            rec["verdict"] = r["verdict"]
            rec["rows"] = nrows
            if r["verdict"] == "CONFORMS" and promote:
                load.promote(db, e)
        except Exception as ex:  # noqa: BLE001
            rec["verdict"] = "ERROR"
            rec["err"] = str(ex)[:300]
        rec["sec"] = round(time.time() - t0, 1)
        results.append(rec)
        print(f"[{i+1}/{len(entries)}] {rec['target'][5:]:46s} {str(rec.get('rows', '?')):>8} 行  -> {rec['verdict']}  {rec['sec']}s", flush=True)
    return results


def run_mapinfo(db="cbdb_reh", only=None, promote=True):
    results = []
    entries = [e for e in load.load_entries() if e["carrier"] == "mapinfo" and not e.get("status")]
    for i, e in enumerate(entries):
        if only and only not in e["target"]:
            continue
        t0 = time.time()
        rec = {"target": e["target"], "carrier": "mapinfo", "rows": _entry_rows(e)}
        try:
            stg, cols, types, nrows = load.load_mapinfo_staging(db, e)
            r = verify.verify_mapinfo(db, e)
            rec["verdict"] = r["verdict"]
            rec["rows"] = nrows
            if r["verdict"] == "CONFORMS" and promote:
                load.promote(db, e)
        except Exception as ex:  # noqa: BLE001
            rec["verdict"] = "ERROR"
            rec["err"] = str(ex)[:300]
        rec["sec"] = round(time.time() - t0, 1)
        results.append(rec)
        print(f"[{i+1}/{len(entries)}] {rec['target'][5:]:46s} {str(rec.get('rows', '?')):>8} 行  -> {rec['verdict']}  {rec['sec']}s", flush=True)
    return results


def _summary(results):
    from collections import Counter
    return dict(Counter(r["verdict"] for r in results))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="cbdb_reh")
    ap.add_argument("--carrier", default="sqlite")
    ap.add_argument("--only", default=None)
    ap.add_argument("--no-promote", action="store_true")
    args = ap.parse_args()

    fn = {"sqlite": run_sqlite, "shapefile": run_shapefile, "mapinfo": run_mapinfo,
          "tsv": (lambda db, only=None, promote=True: run_text(db, "tsv", only, promote)),
          "xls": (lambda db, only=None, promote=True: run_text(db, "xls", only, promote))}.get(args.carrier)
    if fn is None:
        raise SystemExit("本次彩排支持 sqlite/shapefile/mapinfo/tsv/xls")
    results = fn(args.db, only=args.only, promote=not args.no_promote)

    os.makedirs(RECON, exist_ok=True)
    out = os.path.join(RECON, f"rehearse_b_{args.carrier}.json")
    json.dump({"carrier": args.carrier, "summary": _summary(results), "results": results},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n== 汇总 ==", _summary(results))
    print("结果落:", out)
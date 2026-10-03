# -*- coding: utf-8 -*-
"""retry_shapefile.py —— 段B 收口：对 rehearse_b_shapefile.json 中 ERROR/FAIL 层重跑一次。

psql-over-ssh 偶发网络抖动会把个别层记成 ERROR（实测重跑即 CONFORMS）。本脚本只重跑非 CONFORMS 层，
产出 retry 结果，供收口报告确认「无真 FAIL、仅暂态闪断」。
"""
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_DM = os.path.dirname(_HERE)
sys.path.insert(0, _DM)

from importer import load  # noqa: E402
from verifier import verify  # noqa: E402

DB = os.environ.get("REH_DB", "cbdb_reh")


def main():
    res_path = os.path.join(_DM, "recon", "rehearse_b_shapefile.json")
    res = json.load(open(res_path, encoding="utf-8"))
    items = res if isinstance(res, list) else res.get("results", [])
    todo = [r for r in items if r.get("verdict") != "CONFORMS"]
    print(f"重跑 {len(todo)} 个非 CONFORMS 层")
    entries = {e["target"]: e for e in load.load_entries()}
    out = []
    for r in todo:
        t = r["target"]
        e = entries.get(t)
        if e is None:
            out.append({"target": t, "verdict": "NO_SOURCE"}); continue
        t0 = time.time()
        rec = {"target": t, "first": r.get("verdict"), "first_err": r.get("err")}
        try:
            load.load_shapefile_staging(DB, e)
            a = verify.verify_shapefile(DB, e)
            if a["verdict"] == "CONFORMS":
                load.load_shapefile_geom(DB, e)
                g = verify.verify_shapefile_geom(DB, e)
                v = "CONFORMS" if (a["verdict"] == "CONFORMS" and g["verdict"] == "CONFORMS") else "FAIL"
                if v == "CONFORMS":
                    load.assemble_shapefile(DB, e)
                rec.update({"verdict": v, "attr": a["verdict"], "geom": g["verdict"]})
            else:
                rec.update({"verdict": "FAIL", "attr": a["verdict"], "g3": a.get("g3_value")})
        except Exception as ex:  # noqa: BLE001
            rec.update({"verdict": "ERROR", "err": str(ex)[:300]})
        rec["sec"] = round(time.time() - t0, 1)
        out.append(rec)
        print(f"  {t}: {r.get('verdict')} → {rec['verdict']}  {rec['sec']}s", flush=True)
    p = os.path.join(_DM, "recon", "retry_shapefile.json")
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("重跑结果落:", p)


if __name__ == "__main__":
    main()
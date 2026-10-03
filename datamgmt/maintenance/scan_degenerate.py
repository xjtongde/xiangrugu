# -*- coding: utf-8 -*-
"""scan_degenerate.py —— 盘点 shapefile 源件退变几何（闸4 语义哨兵，只读源、不写库）。

逐图层统计：Null 形(hdr type=0) 与「PostGIS 不可表示」的退变几何
(线 <2 顶点 / 环 <4 顶点 / MultiPoint 空)。这些在装载时按 NULL geom 落(已装载侧同样跳过)，
此处仅作逐案裁决清单的数量来源。
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DM = os.path.dirname(_HERE)
sys.path.insert(0, _DM)

from truth import dbf, shp, srcopen  # noqa: E402

CFG = os.path.join(_DM, "config", "sources.yaml")
OUT = os.path.join(_DM, "recon", "degenerate_geometry.json")


def _is_degenerate(feat):
    t = feat["type"]
    if t == "Null":
        return True
    g = feat["geom"]
    if t == "Point":
        return False
    if t == "MultiPoint":
        return len(g) == 0
    if t == "MultiLineString":
        return len(g) == 0 or any(len(line) < 2 for line in g)
    if t == "MultiPolygon":
        return len(g) == 0 or any(len(poly) == 0 or any(len(ring) < 4 for ring in poly) for poly in g)
    return False


def main():
    entries = [json.loads(l.strip()[2:]) for l in open(CFG, encoding="utf-8")
               if l.strip().startswith("- ")]
    rows = []
    for e in entries:
        if e["carrier"] != "shapefile":
            continue
        b = srcopen.read_member(e["key"], ".shp")
        if b is None:
            continue
        dbytes = srcopen.read_member(e["key"], ".dbf")
        delidx = ({i for i, (_, de) in enumerate(dbf.iter_records(dbytes)) if de}
                  if dbytes is not None else set())
        nd = 0
        for i, f in enumerate(shp.iter_features(b)):
            if i in delidx:
                continue
            if _is_degenerate(f):
                nd += 1
        if nd:
            rows.append({"target": e["target"], "degenerate": nd})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"n_layers": len(rows), "total_degenerate": sum(r["degenerate"] for r in rows),
               "layers": rows}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("含退变几何的图层数:", len(rows), "| 退变要素总数:", sum(r["degenerate"] for r in rows))
    for r in rows[:40]:
        print(f"  {r['target']:50s} {r['degenerate']}")


if __name__ == "__main__":
    main()
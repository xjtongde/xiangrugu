# -*- coding: utf-8 -*-
"""truth.probe —— 对单个源件产出真值基线（阶段一）。

用法（开发期自测，后续并入 verifier 统一入口）：
  python3 -m truth.probe sqlite  <path>
  python3 -m truth.probe shapefile <zip> <inner.dbf> [<inner.shp> <inner.prj>]
  python3 -m truth.probe dbf <path>
"""
import json
import os
import sys
import zipfile

from . import dbf as dbf_mod
from . import shp as shp_mod
from . import sqlite as sqlite_mod


def read_from_zip(zpath, member):
    with zipfile.ZipFile(zpath) as z:
        return z.read(member)


def probe_shapefile_zip(zpath, inner_base):
    """inner_base 例 'v6_time_cnty_pts_utf_wgs84'；在 zip 内找配套 .dbf/.shp/.prj。"""
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        def pick(ext):
            cands = [n for n in names if n.rstrip("/") == inner_base + "." + ext
                     or n == inner_base + "." + ext]
            return cands[0] if cands else None
        dbf_m = pick("dbf")
        shp_m = pick("shp")
        prj_m = pick("prj")
        out = {"source_key": f"{zpath}::{inner_base}", "kind": "shapefile"}
        if dbf_m:
            out["dbf"] = dbf_mod.parse_dbf(z.read(dbf_m))
        if shp_m:
            out["shp"] = shp_mod.parse_shp(z.read(shp_m))
        if prj_m:
            out["prj"] = z.read(prj_m).decode("utf-8", errors="replace")
        return out


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "sqlite":
        out = sqlite_mod.probe_sqlite(argv[1])
    elif cmd == "dbf":
        with open(argv[1], "rb") as f:
            out = dbf_mod.parse_dbf(f.read())
    elif cmd == "shapefile":
        out = probe_shapefile_zip(argv[1], argv[2])
    else:
        print(__doc__)
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
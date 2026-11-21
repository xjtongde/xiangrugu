#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定点修复：仅重跑 43 件 geo_raster 的 gdal 探针段，回填 noData 真值。

- 读现有 probe_evidence.json（含阶段 B 全部绑定/世界文件回填结果）。
- 对 raster_meta.gdalinfo_rc==0 的记录重新执行 osgeo 探针（GetNoDataValue 无参版）。
- noData：源未声明=None 且不得残留 noData_error；有值=数值。
- geotransform/CRS/checksum/世界文件回填等其余字段以新探针结果整体覆盖（同源同法），
  world_file_declared 保留原值不动。
- 其余 2479 件记录逐字节保留（不重排、不改写）。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

SNAP = "/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap"
BASE = "/opt/mydocker/xiangrugu/build-candidates/raster-other-20261121"
EVIDENCE = os.path.join(BASE, "probe_evidence.json")
IMAGE = "xiangrugu:runtime-spatial-mapinfo-20261120-a"

sys.path.insert(0, BASE)
from bindings_gdal_block5 import PROBE_PY, extract_member  # noqa: E402


def run_probe(mount_src: str, container_path: str, do_cs: bool):
    cmd = ["docker", "run", "--rm", "--network", "none",
           "-v", f"{mount_src}:/probe:ro", IMAGE,
           "python3", "-c", PROBE_PY, container_path, "1" if do_cs else "0"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout, p.stderr


def main():
    recs = json.load(open(EVIDENCE))
    targets = [r for r in recs if (r.get("raster_meta") or {}).get("gdalinfo_rc") == 0]
    print(f"geo_raster 重探件数: {len(targets)}")
    assert len(targets) == 43, f"预期 43，实际 {len(targets)}"

    work = tempfile.mkdtemp(prefix="blk5-nodata-")
    ok = fail = 0
    t0 = time.time()
    try:
        for i, m in enumerate(targets):
            idn = m["identity"]
            rm_old = m["raster_meta"]
            direct = not idn["archive_chain"]
            sub = None
            if direct:
                mount_src = SNAP
                cpath = "/probe/" + idn["relative_path"]
            else:
                sub = os.path.join(work, f"c{i}")
                os.makedirs(sub, exist_ok=True)
                top = os.path.join(SNAP, idn["relative_path"])
                lp, _note = extract_member(top, idn["archive_ordinals"], sub)
                os.chmod(sub, 0o755)
                mount_src = sub
                cpath = "/probe/" + os.path.basename(lp)
            do_cs = m["declared"]["size"] <= 20 * 1024 * 1024
            rc, out, err = run_probe(mount_src, cpath, do_cs)
            if rc == 0 and out:
                g = json.loads(out)
                cs = g.get("coordinateSystem") or {}
                rm_new = {**rm_old}
                rm_new.update({
                    "gdalinfo_rc": 0,
                    "probe_via": "python osgeo.gdal（镜像无 gdalinfo CLI，披露）",
                    "size_px": [g["rasterSize"]["x"], g["rasterSize"]["y"]],
                    "bands": g["bands"],
                    "geotransform": g["geoTransform"],
                    "gcp_count": g["gcp_count"],
                    "driver": g["driverShortName"],
                    "crs_source_declared": cs,
                    "md": g["metadata_dataset"],
                    "tiff_tags": g.get("tiff_tags", {}),
                    "file_list": g["file_list"],
                    "checksum_ran": do_cs,
                })
                if not do_cs:
                    rm_new["checksum_method"] = "gdal Band.Checksum()（大件本轮不跑，登记方法）"
                m["raster_meta"] = rm_new
                ok += 1
            else:
                print(f"[FAIL] {idn['leaf']}: rc={rc} {err[:200]}")
                fail += 1
            if sub is not None:
                shutil.rmtree(sub, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # ---- 校验面 ----
    nodata_valued = nodata_none = err_keys = 0
    for r in targets:
        for b in (r["raster_meta"].get("bands") or []):
            if b.get("noData") is not None:
                nodata_valued += 1
            else:
                nodata_none += 1
            if "noData_error" in b:
                err_keys += 1
    untouched = sum(1 for r in recs if not r.get("raster_meta"))
    print(json.dumps({
        "reprobe_ok": ok, "reprobe_fail": fail,
        "bands_noData_valued": nodata_valued, "bands_noData_null": nodata_none,
        "noData_error_residual": err_keys,
        "records_untouched": untouched, "total": len(recs),
        "elapsed_s": round(time.time() - t0, 1),
    }, ensure_ascii=False))
    if fail or err_keys:
        print("NOT WRITING — 存在失败或错误键残留", file=sys.stderr)
        sys.exit(1)

    tmp = EVIDENCE + ".nodata-fix"
    json.dump(recs, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, EVIDENCE)
    print("WROTE", EVIDENCE)


if __name__ == "__main__":
    main()

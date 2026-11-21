#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段 B：绑定回填 + 栅格 gdalinfo（现有镜像，只读）。

输入 : probe_evidence_stageA.json（阶段 A 输出）+ candidates.json
输出 : probe_evidence.json（终态）

- 世界文件/伴随件同 stem 兄弟查找：同一外层容器（relative_path）内比较 leaf stem（大小写不敏感）。
- tif 与有世界文件绑定的 jpg/png/gif → docker run --rm --network none -v SNAP:ro IMAGE gdalinfo -json <提取件路径>。
  嵌套成员先流式提取到隔离目录，再以该隔离目录 :ro 挂载。
- 逐件记录尺寸/波段/像素类型/NoData/geotransform/源 CRS 逐字；缺失 null+原因。
- 小件（<=20MB）加跑 gdalinfo -checksum；大件只登记方法。
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

SNAP = "/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap"
CAND = "/opt/mydocker/xiangrugu/build-candidates/raster-other-20261121/candidates.json"
STAGE_A = "/opt/mydocker/xiangrugu/build-candidates/raster-other-20261121/probe_evidence_stageA.json"
OUT = "/opt/mydocker/xiangrugu/build-candidates/raster-other-20261121/probe_evidence.json"
IMAGE = "xiangrugu:runtime-spatial-mapinfo-20261120-a"

WORLD_EXTS = {"tfw", "tifw", "jgw", "jgwx", "wld", "pw"}
RASTER_AUX = {"aux", "rrd", "ovr"}
SIDECAR_BIND_EXTS = WORLD_EXTS | RASTER_AUX | {"prj", "qpj", "cpg", "cst", "csvt", "sbn", "sbx", "shx", "shp", "qml", "qgs", "qgz", "qgd", "lyr"}


def stem_of(leaf: str) -> str:
    s = leaf.rsplit("/", 1)[-1]
    i = s.find(".")
    return (s[:i] if i > 0 else s).lower()


def ext_of(leaf: str) -> str:
    s = leaf.lower()
    if s.endswith(".aux.xml"):
        return "aux.xml"
    i = s.rfind(".")
    return s[i + 1:] if i >= 0 else ""


def key_of(rec) -> tuple:
    idn = rec["identity"]
    return (idn["relative_path"], tuple(idn["archive_chain"][:-1]) if idn["archive_chain"] else ())


def extract_member(zip_path, ordinals, dest_dir):
    cur = zip_path
    seq = []
    for depth, ordinal in enumerate(ordinals):
        out = os.path.join(dest_dir, f"L{depth}_{ordinal}.bin")
        with zipfile.ZipFile(cur) as zf:
            names = zf.namelist()
            info = zf.getinfo(names[ordinal])
            with zf.open(info) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
        seq.append({"layer": depth, "member_index": ordinal,
                    "member_name": names[ordinal], "member_size": info.file_size})
        cur = out
    return cur, seq


def locate(rec, work):
    """返回 (可 gdalinfo 的宿主路径 or None, 注记)。"""
    idn = rec["identity"]
    top = os.path.join(SNAP, idn["relative_path"])
    if not idn["archive_chain"]:
        return top, {"access": "snapshot_direct_ro"}
    local, note = extract_member(top, idn["archive_ordinals"], work)
    return local, {"access": "isolated_extract", "extract_chain": note}


def run_gdal(path_in_container: str, extra=None):
    cmd = ["docker", "run", "--rm", "--network", "none",
           "-v", f"{MOUNT_SRC}:/probe:ro", IMAGE,
           "gdalinfo"] + (extra or []) + ["-json", path_in_container]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    return p.returncode, p.stdout, p.stderr


# 镜像内无 gdalinfo CLI（python3-gdal=iU 半装态、GDAL CLI 包未装，如实披露），
# 但 /usr/lib/python3/dist-packages/osgeo 绑定可用 ⇒ 用 python3 -c 调 gdal.Open。
PROBE_PY = r'''
import json, sys
sys.path.insert(0, "/usr/lib/python3/dist-packages")
from osgeo import gdal, gdalconst
gdal.UseExceptions()
p = sys.argv[1]
do_checksum = sys.argv[2] == "1"
ds = gdal.Open(p, gdalconst.GA_ReadOnly)
gt = ds.GetGeoTransform(can_return_null=True)
bands = []
for bi in range(1, ds.RasterCount + 1):
    b = ds.GetRasterBand(bi)
    d = {
        "band": bi,
        "type": gdal.GetDataTypeName(b.DataType),
        "colorInterpretation": gdal.GetColorInterpretationName(b.GetColorInterpretation()),
        "block_size": list(b.GetBlockSize()),
    }
    try:
        d["noData"] = b.GetNoDataValue()  # 无参调用：源未声明返回 None
    except Exception as e:
        d["noData"] = None
        d["noData_error"] = str(e)
    if do_checksum:
        try:
            d["checksum"] = b.Checksum()
        except Exception as e:
            d["checksum_error"] = str(e)
    md = b.GetMetadata()
    if md:
        d["band_metadata"] = md
    bands.append(d)
wkt = ds.GetProjectionRef() or None
out = {
    "driverShortName": ds.GetDriver().ShortName,
    "driverLongName": ds.GetDriver().LongName,
    "rasterSize": {"x": ds.RasterXSize, "y": ds.RasterYSize},
    "geoTransform": list(gt) if gt else None,
    "gcp_count": len(ds.GetGCPs()),
    "coordinateSystem": {
        "wkt_verbatim_from_source": wkt,
        "srs_is_null": wkt is None,
        "note": "GetProjectionRef 逐字转录；无内部声明=null，不推导不转换",
    },
    "metadata_dataset": ds.GetMetadata() or {},
    "tiff_tags": {k: v for k, v in (ds.GetMetadata("TIFF") or {}).items()},
    "bands": bands,
    "file_list": [f.rsplit("/", 1)[-1] for f in (ds.GetFileList() or [])],
}
print(json.dumps(out, ensure_ascii=False))
'''


def run_gdal_py(container_path: str, do_checksum: bool):
    cmd = ["docker", "run", "--rm", "--network", "none",
           "-v", f"{MOUNT_SRC}:/probe:ro", IMAGE,
           "python3", "-c", PROBE_PY, container_path, "1" if do_checksum else "0"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout, p.stderr


def main():
    global MOUNT_SRC
    recs = json.load(open(STAGE_A))
    by_index = list(enumerate(recs))

    # 索引：外层文件 -> {parent_chain -> {stem -> [rec]}}（大小写不敏感 stem）
    stems = {}
    for r in recs:
        idn = r["identity"]
        if idn["kind"] == "directory":
            continue
        parent = tuple(c.lower() for c in idn["archive_chain"][:-1])
        stems.setdefault((idn["relative_path"].lower(), parent), {}) \
             .setdefault(stem_of(idn["leaf"]), []).append(r)

    def ext_of_rec(r):
        return ext_of(r["identity"]["leaf"])

    raster_targets = []
    for key, group in stems.items():
        for st, members in group.items():
            worlds = [m for m in members if ext_of_rec(m) in WORLD_EXTS and m is not None]
            auxes = [m for m in members if ext_of_rec(m) in (RASTER_AUX | {"aux.xml"})]
            for m in members:
                e = ext_of_rec(m)
                magic = m.get("magic") or ""
                is_aux_like = e in (RASTER_AUX | {"aux.xml"}) or m["class"] == "sidecar_companion"
                is_img = magic in ("JPEG", "PNG", "GIF87a", "GIF89a") or e in ("jpg", "jpeg", "png", "gif")
                is_tif = magic.startswith("TIFF") or e in ("tif", "tiff")
                if is_aux_like and not (e in ("tif", "tiff")):
                    # ovr/rrd/aux 等伴随件本身不送 gdalinfo，只登记绑定
                    own_world = [w for w in worlds if w is not m]
                    m["binding"] = {"role": "raster_companion",
                                    "bound_rasters": [x["identity"]["leaf"] for x in members
                                                      if x is not m and ((x.get("magic") or "").startswith("TIFF")
                                                                         or ext_of_rec(x) in ("tif", "tiff", "jpg", "jpeg", "png", "gif"))],
                                    "world_files_siblings": [w["identity"]["leaf"] for w in own_world]}
                    continue
                if not (is_img or is_tif):
                    continue
                binding = {"world_files": [w["identity"]["leaf"] for w in worlds if w is not m],
                           "companion_files": [a["identity"]["leaf"] for a in auxes if a is not m]}
                m["binding"] = binding
                has_world = bool(binding["world_files"])
                if is_tif or has_world:
                    if m["class"] != "geo_raster":
                        m["class"] = "geo_raster"
                        m["purpose"] = ("TIFF 栅格" if is_tif else "带世界文件绑定的图像＝地理配准栅格") + "（CRS 依源声明）"
                    raster_targets.append(m)

    # ---- 2. gdalinfo ----
    work = tempfile.mkdtemp(prefix="blk5-gdal-")
    iso_mode = False
    done = fail = 0
    t0 = time.time()
    try:
        for i, m in enumerate(raster_targets):
            idn = m["identity"]
            direct = not idn["archive_chain"]
            sub = None
            # 直读件挂快照 :ro；嵌套件提取到隔离目录挂 :ro
            if direct:
                MOUNT_SRC = SNAP
                container_path = "/probe/" + idn["relative_path"]
                access = {"access": "snapshot_direct_ro"}
            else:
                sub = os.path.join(work, f"c{i}")
                os.makedirs(sub, exist_ok=True)
                lp, note = locate(m, sub)
                os.chmod(sub, 0o755)
                MOUNT_SRC = sub
                container_path = "/probe/" + os.path.basename(lp)
                access = note
            meta = {"mount": "snapshot:ro" if direct else "isolated_extract:ro", **access}
            do_cs = m["declared"]["size"] <= 20 * 1024 * 1024
            meta["checksum_ran"] = do_cs
            if not do_cs:
                meta["checksum_method"] = "gdal Band.Checksum()（大件本轮不跑，登记方法）"
            rc, out, err = -1, "", ""
            try:
                rc, out, err = run_gdal_py(container_path, do_cs)
            except Exception as e:  # noqa: BLE001
                meta["gdal_error"] = f"{type(e).__name__}:{e}"
            if rc == 0 and out:
                try:
                    g = json.loads(out)
                    cs = g.get("coordinateSystem") or {}
                    meta.update({
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
                    })
                    done += 1
                except (json.JSONDecodeError, KeyError):
                    meta["gdal_error"] = "json_parse_failed"; fail += 1
            else:
                meta["gdalinfo_rc"] = rc
                meta["gdal_error"] = (err or "")[:400]
                fail += 1
            m["raster_meta"] = meta
            if (i + 1) % 10 == 0:
                print(f"[gdal] {i+1}/{len(raster_targets)} ok={done} fail={fail} {time.time()-t0:.0f}s", flush=True)
            if sub is not None:
                shutil.rmtree(sub, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # ---- 2b. 世界文件原声明回填（源声明转录，非推导）：仅当内部无 GT 时读取同 stem .jgw/.tifw/.tfw
    def read_world(rec):
        idn = rec["identity"]
        top = os.path.join(SNAP, idn["relative_path"])
        try:
            if not idn["archive_chain"]:
                txt = open(top, "r", encoding="utf-8", errors="strict").read()
            else:
                w2 = tempfile.mkdtemp(prefix="blk5-wf-")
                try:
                    lp, _ = extract_member(top, idn["archive_ordinals"], w2)
                    txt = open(lp, "r", encoding="utf-8", errors="strict").read()
                finally:
                    shutil.rmtree(w2, ignore_errors=True)
            vals = [float(x) for x in txt.split()]
            if len(vals) != 6:
                return {"raw": txt.strip(), "note": "字段数!=6，逐字保留不解释"}
            return {"x_resolution": vals[0], "rot_2": vals[1], "rot_3": vals[2],
                    "y_resolution": vals[3], "x_origin_upper_left": vals[4],
                    "y_origin_upper_left": vals[5], "verbatim": txt.strip()}
        except Exception as e:  # noqa: BLE001
            return {"error": f"{type(e).__name__}:{e}"}

    by_leaf = {}
    for r in recs:
        idn = r["identity"]
        if idn["kind"] == "directory":
            continue
        parent = tuple(c.lower() for c in idn["archive_chain"][:-1])
        by_leaf[(idn["relative_path"].lower(), parent, idn["leaf"].lower())] = r

    wf_backfilled = 0
    for m in raster_targets:
        rm = m.get("raster_meta") or {}
        # 修正：世界文件原声明一律逐字转录（不再以内部 GT 存在为跳过条件）；
        # 与内部 geotransform 并存时由消费方按源声明面各自引用，不做取舍推断。
        idn = m["identity"]
        parent = tuple(c.lower() for c in idn["archive_chain"][:-1])
        st = stem_of(idn["leaf"])
        worlds = (m.get("binding") or {}).get("world_files", [])
        for wleaf in worlds:
            wrec = by_leaf.get((idn["relative_path"].lower(), parent, wleaf.lower()))
            if wrec is None:
                continue
            wf = read_world(wrec)
            # 仅当世界文件六参数可解析时才登记为原声明证据；
            # 非六参数语法（如 .jgwx XML 变体）不冒充世界文件绑定，留 sidecar 显式登记。
            if "x_resolution" not in wf:
                continue
            rm["world_file_declared"] = {"file": wleaf, **wf}
            wf_backfilled += 1
            break
        m["raster_meta"] = rm
    print(f"[worldfiles] geotransform 缺失件世界文件回填: {wf_backfilled}", flush=True)

    # ---- 3. xml/sidecar 细分标注（xref block3 / aux.xml / 内容判用途）----
    for r in recs:
        idn = r["identity"]
        if idn["kind"] == "directory":
            continue
        e = ext_of(idn["leaf"])
        parent = tuple(c.lower() for c in idn["archive_chain"][:-1])
        siblings = stems.get((idn["relative_path"].lower(), parent), {})
        st = stem_of(idn["leaf"])
        if e == "xml" and idn["leaf"].lower().endswith(".aux.xml"):
            base_stem = stem_of(st)  # 去掉最后一段 .aux ⇒ 栅格 stem
            bound = [x["identity"]["leaf"] for x in siblings.get(base_stem, [])
                     if x is not r and ((x.get("magic") or "").startswith("TIFF")
                                        or ext_of(x["identity"]["leaf"]) in ("tif", "tiff", "jpg", "jpeg", "png", "gif"))]
            r["class"] = "sidecar_companion"
            r["purpose"] = "ESRI .aux.xml 栅格伴随（金字塔/统计）"
            r["binding"] = {"role": "raster_aux_xml", "bound_rasters": bound}
        elif e == "xml":
            has_shp = any(ext_of(x["identity"]["leaf"]) == "shp" for x in siblings.get(st, []) if x is not r)
            if has_shp:
                r["class"] = "sidecar_companion"
                r["purpose"] = "spatial sidecar（同 stem .shp 存在）⇒xref 第 3 块，不重复认领"
                r.setdefault("binding", {})["xref"] = "block3_spatial"
        elif e in SIDECAR_BIND_EXTS - WORLD_EXTS and r.get("binding") is None:
            # qpj/cpg/cst/csvt/qml/lyr/qgs…：登记绑定候选（同 stem 目标），不确证语义
            targets = [x["identity"]["leaf"] for x in siblings.get(st, [])
                       if x is not r and ext_of(x["identity"]["leaf"]) not in SIDECAR_BIND_EXTS | {""}]
            r["class"] = "sidecar_companion"
            r["purpose"] = f".{e} 伴随件（同 stem 绑定候选见 binding）"
            r["binding"] = {"role": "gis_sidecar", "bind_candidates": targets}
        elif e in WORLD_EXTS:
            targets = [x["identity"]["leaf"] for x in siblings.get(st, [])
                       if x is not r and (ext_of(x["identity"]["leaf"]) in
                                          ("tif", "tiff", "jpg", "jpeg", "png", "gif")
                                          or (x.get("magic") or "").startswith(("TIFF", "JPEG", "PNG", "GIF")))]
            r["class"] = "sidecar_companion"
            r["purpose"] = "世界文件（地理参考原声明载体）"
            r["binding"] = {"role": "world_file", "bound_rasters": targets}

    json.dump(recs, open(OUT, "w"), ensure_ascii=False, indent=1)
    import collections
    summary = {
        "total": len(recs),
        "by_class": dict(collections.Counter(r["class"] for r in recs)),
        "raster_targets": len(raster_targets),
        "gdalinfo_ok": done,
        "gdalinfo_fail": fail,
        "sha_mismatch": sum(1 for r in recs if r["sha_verified"] is False),
        "unknown": sum(1 for r in recs if r["class"] == "unknown"),
        "elapsed_s": round(time.time() - t0, 1),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

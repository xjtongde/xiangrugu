# -*- coding: utf-8 -*-
"""truth.enumerate —— 对权威源全部 zip 内 shapefile 图层产出真值基线（阶段一）。

做法：递归枚举 usedata/ 下每个 .zip（含 zip 套 zip，深度≤3），按 (目录, 基名) 配对
.dbf/.shp/.prj/.cpg，逐图层直读字节产出：
  - dbf：行数 + 字段集（名/类型/长度/小数位）
  - shp：几何类型 + 要素数
  - prj：CRS 文本（逐字保真）
  - cpg：编码声明（原样）
  - 编码嗅探：对记录区样本做 utf8/gbk 判别（仅普查，不替代 .cpg 权威）
并逐图层核对 dbf 行数 == shp 要素数（源内自洽，闸2 前身）；不一致记 flags，不判错。

输出：datamgmt/recon/truth_baseline.jsonl（每图层一行）＋ truth_baseline_summary.json。
只读源件，不写库、不改源件。
"""
import json
import os
import posixpath
import zipfile

from . import dbf as dbf_mod
from . import shp as shp_mod

USEDATA = "/mnt/wd61workmetadata/usedata"  # 阶段一占位：后续挂 roots.yaml（同 gate0 读法）
RECON = os.path.join(os.path.dirname(__file__), "..", "recon")
MAX_DEPTH = 3
SAMPLE_BYTES = 8192


def sniff_encoding(raw: bytes):
    """对样本字节做粗粒度编码判别：utf8 / gbk / latin1(含纯ascii)。仅普查提示。

    注意：按整体字节判定；纯 ASCII 样本判为 utf8（因 ASCII⊂UTF-8）。"""
    if not raw:
        return "empty"
    s = raw[:SAMPLE_BYTES]
    # 依序试解，取首个成功者（仅普查提示，非权威；gbk/big5 字节区间重叠，可能存在
    # 一种字节两种都能解出的情况——此时取先试到的 gbk，阶段二逐列复核）。
    for name in ("utf-8", "gbk", "big5", "gb18030", "cp1251", "cp932"):
        try:
            s.decode(name)
            return "utf8" if name == "utf-8" else name
        except UnicodeDecodeError:
            pass
    return "latin1_or_binary"


def field_encoding_survey(dbf_bytes, fields, n_records, record_size, max_records=12):
    """读前 max_records 条记录的 C 型字段**完整值**做编码判别（免截断）。"""
    header = 32 + 32 * len(fields) + 1
    samples = []
    has_non_ascii = False
    for i in range(min(n_records, max_records)):
        off = header + i * record_size
        if off + record_size > len(dbf_bytes):
            break
        for f in fields:
            if f["type"] == "C":
                v = dbf_bytes[off + f["offset"]: off + f["offset"] + f["length"]]
                v = v.rstrip(b"\x00").rstrip(b" ")
                if any(b2 >= 0x80 for b2 in v):
                    has_non_ascii = True
                samples.append(v)
    return {"sniff": sniff_encoding(b"".join(samples)), "has_non_ascii": has_non_ascii}


def _walk_zip(zbytes, path_label, depth, out):
    """在 zip 字节内配对图层；发现嵌套 .zip 则递归（depth≤MAX_DEPTH）。"""
    from io import BytesIO
    z = zipfile.ZipFile(BytesIO(zbytes))
    names = [n for n in z.namelist() if not n.endswith("/")]
    groups = {}
    for n in names:
        d, f = posixpath.split(n)
        base, ext = posixpath.splitext(f)
        ext = ext.lower()
        if ext in (".dbf", ".shp", ".prj", ".cpg"):
            groups.setdefault((d, base), {})[ext] = n
    for (d, base), parts in groups.items():
        rec = {"zip": path_label, "dir": d, "layer": base,
               "kind": "shapefile", "flags": []}
        if ".dbf" in parts:
            dbf_bytes = z.read(parts[".dbf"])
            drec = dbf_mod.parse_dbf(dbf_bytes)
            rec["dbf_rows"] = drec["records"]
            rec["fields"] = drec["fields"]
            enc = field_encoding_survey(dbf_bytes, drec["fields"],
                                        drec["records"], drec["record_size"])
            rec["encoding_sniff"] = enc["sniff"]
            rec["has_non_ascii"] = enc["has_non_ascii"]
            rec["language_driver"] = drec["language_driver"]
        if ".shp" in parts:
            srec = shp_mod.parse_shp(z.read(parts[".shp"]))
            rec["shp_rows"] = srec["records"]
            rec["shape_type"] = srec["shape_type_name"]
        if ".prj" in parts:
            rec["crs"] = z.read(parts[".prj"]).decode("utf-8", errors="replace").strip()
        if ".cpg" in parts:
            rec["cpg_declared"] = z.read(parts[".cpg"]).decode("utf-8", errors="replace").strip()
        if ".dbf" in parts and ".shp" in parts and rec.get("dbf_rows") != rec.get("shp_rows"):
            rec["flags"].append(f"dbf={rec.get('dbf_rows')} != shp={rec.get('shp_rows')}")
        out.append(rec)
    # 嵌套 zip
    if depth < MAX_DEPTH:
        for n in names:
            if n.lower().endswith(".zip"):
                inner = z.read(n)
                try:
                    _walk_zip(inner, f"{path_label}::{n}", depth + 1, out)
                except Exception as e:  # noqa: BLE001
                    out.append({"zip": path_label, "nested_zip": n,
                                "kind": "nested_zip_error", "error": str(e)})


def enumerate_all():
    import glob
    zips = sorted(glob.glob(USEDATA + "/**/*.zip", recursive=True) +
                  glob.glob(USEDATA + "/**/*.ZIP", recursive=True))
    out = []
    for zp in zips:
        try:
            with open(zp, "rb") as f:
                _walk_zip(f.read(), posixpath.relpath(zp, USEDATA), 1, out)
        except Exception as e:  # noqa: BLE001
            out.append({"zip": posixpath.relpath(zp, USEDATA),
                        "kind": "zip_error", "error": str(e)})
    return out


def summary(records):
    layers = [r for r in records if r.get("kind") == "shapefile"]
    mism = [r for r in layers if r.get("flags")]
    enc_dist = dict(__import__("collections").Counter(r.get("encoding_sniff") for r in layers))
    non_ascii = sum(1 for r in layers if r.get("has_non_ascii"))
    cpg_utf = sum(1 for r in layers if r.get("cpg_declared") in ("UTF-8", "utf8", "utf-8"))
    cpg_gbk = sum(1 for r in layers if r.get("cpg_declared") in ("936", "GBK", "gbk", "CP936"))
    return {
        "layers": len(layers),
        "total_dbf_rows": sum(r.get("dbf_rows", 0) for r in layers),
        "dbf_shp_mismatch": len(mism),
        "encoding_sniff": enc_dist,
        "layers_with_non_ascii": non_ascii,
        "cpg_declared": {"utf8": cpg_utf, "gbk936": cpg_gbk},
        "has_crs": sum(1 for r in layers if r.get("crs")),
        "non_layer_entries": [r for r in records if r.get("kind") != "shapefile"],
    }


def main():
    records = enumerate_all()
    os.makedirs(RECON, exist_ok=True)
    jl = os.path.join(RECON, "truth_baseline.jsonl")
    with open(jl, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    sm = summary(records)
    sp = os.path.join(RECON, "truth_baseline_summary.json")
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(sm, f, ensure_ascii=False, indent=2, default=str)
    print(json.dumps(sm, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""verifier.verify —— 六道闸之 闸1/2/3（腿A sqlite + 腿B shapefile 属性），与 importer.load **零共用代码**。

独立性（§6.1）：期望值由 truth/ 直读源件字节现算，绝不取自装载之库；解码判表读同一份
decoding.yaml，但「字节→字符」之列级解码在本文件独立实现一遍（load.py 也各自写一遍）。
闸3：类型感知多重集差集；null 显式化哨兵 '␀'(U+2400)；numeric/bigint 按 Decimal 归约禁 float；
double/real 按 float.hex() 逐位。库侧读值经 COPY TO STDOUT csv（robust 于 | 与换行）。"""
import csv
import io
import json
import os
import struct
import sys
from collections import Counter
from decimal import Decimal

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATAMGMT = os.path.dirname(_HERE)
if _DATAMGMT not in sys.path:
    sys.path.insert(0, _DATAMGMT)

import decode  # noqa: E402  判表读取（config 层）
from db import rows, copy_to, quote_ident  # noqa: E402
from truth import roots, sqlite, dbf, shp, mapinfo  # noqa: E402
from truth import srcopen  # noqa: E402

USEDATA = roots.usedata()
CFG = os.path.join(_DATAMGMT, "config", "sources.yaml")
NULL_SENT = "\u2400"  # ␀ SYMBOL FOR NULL


def load_entries():
    out = []
    with open(CFG, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s.startswith("- "):
                out.append(json.loads(s[2:]))
    return out


def _canon_num(s):
    d = Decimal(str(s))
    t = format(d, "f")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return "0" if t == "-0" else t


def _canon_typed(v, pg_type):
    """源/库两端口径统一：None 与哨兵→NULL；数值→Decimal 归约；浮点→float.hex()（逐位）；其余 str。"""
    if v is None or v == NULL_SENT:
        return NULL_SENT
    if pg_type in ("bigint", "integer", "smallint") or pg_type.startswith("numeric"):
        return _canon_num(str(v))
    if pg_type in ("double precision", "real"):
        return float(v).hex()
    return str(v)


def _dbf_cell(raw, f, fam):
    """verifier 侧列级解码（独立实现）：raw 字段字节 → str|None。"""
    if f["type"] == "N":
        s = raw.strip(b" \x00").decode("ascii", "strict")
        return None if (s == "" or "*" in s) else s
    body = raw.rstrip(b" \x00")
    enc = decode.col_encoding(fam, f["name"])
    if enc is None:
        return None
    return body.decode(enc, "replace")


def _gates(db, schema, tname, colnames, pg_types, src_cells):
    """闸1 结构 / 闸2 计数 / 闸3 值级，不过即停（§6.1.5）。src_cells 已按口径归一。"""
    expect_names = [c.lower() for c in colnames]
    dbcols = rows(db, (
        "SELECT column_name FROM information_schema.columns "
        f"WHERE table_schema='{schema}' AND table_name='{tname}__stg' ORDER BY ordinal_position;"
    ))
    got_names = [r[0] for r in dbcols if r[0] != "__rid"]  # __rid 系内部对齐列，不入结构比对
    if got_names != expect_names:
        return {"table": f"{schema}.{tname}", "verdict": "FAIL", "stopped_at": "g1",
                "g1_structure": {"pass": False, "expect": expect_names, "got": got_names}}

    cnt = int(rows(db, f"SELECT count(*) FROM {quote_ident(schema)}.{quote_ident(tname + '__stg')};")[0][0])
    if cnt != len(src_cells):
        return {"table": f"{schema}.{tname}", "verdict": "FAIL", "stopped_at": "g2",
                "g2_count": {"pass": False, "expect": len(src_cells), "got": cnt}}

    src_multi = Counter(src_cells)
    selexpr = ", ".join(
        f"COALESCE({quote_ident(c.lower())}::text,'{NULL_SENT}')" for c in colnames
    )
    csv_out = copy_to(db, (
        f"COPY (SELECT {selexpr} FROM {quote_ident(schema)}.{quote_ident(tname + '__stg')}) "
        "TO STDOUT WITH (FORMAT csv);"
    ))
    db_rows = list(csv.reader(io.StringIO(csv_out)))  # csv.reader 原位处理 | 与引号内换行
    db_multi = Counter(
        tuple(_canon_typed(r[i], pg_types[i]) for i in range(len(r))) for r in db_rows
    )

    d1 = src_multi - db_multi   # 源有库无（欠装）
    d2 = db_multi - src_multi   # 库有源无（多装/改写）
    g3 = (not d1 and not d2)
    return {
        "table": f"{schema}.{tname}",
        "g1_structure": {"pass": True, "expect": expect_names, "got": got_names},
        "g2_count": {"pass": True, "expect": len(src_cells), "got": cnt},
        "g3_value": {"pass": g3, "diff_src_only": len(d1), "diff_db_only": len(d2),
                     "samples_src_only": list(d1)[:5], "samples_db_only": list(d2)[:5]},
        "verdict": "CONFORMS" if g3 else "FAIL",
    }


def verify_sqlite(db, entry):
    schema, tname = entry["target"].split(".", 1)
    tname = tname.lower()
    nas_path, table = entry["key"].split("::", 1)
    path = os.path.join(USEDATA, nas_path)
    colnames, srows = sqlite.read_values(path, table)
    pg_types = [entry["columns"][c] for c in colnames]
    src_cells = [tuple(_canon_typed(v, pt) for v, pt in zip(r, pg_types)) for r in srows]
    return _gates(db, schema, tname, colnames, pg_types, src_cells)


def verify_text(db, entry, colnames, rows):
    """纯属性源(tsv/xls) 闸1-3：源侧现读字节，类型感知归一后与库比较多重集。"""
    schema, tname = entry["target"].split(".", 1)
    tname = tname.lower()
    pg_types = [entry["columns"][c] for c in colnames]
    src_cells = [tuple(_canon_typed(v, pt) for v, pt in zip(r, pg_types)) for r in rows]
    return _gates(db, schema, tname, colnames, pg_types, src_cells)


def verify_tsv(db, entry):
    from truth import read_text
    colnames, rows = read_text.read_tsv(entry["key"], entry.get("encoding", "utf-8"))
    return verify_text(db, entry, colnames, rows)


def verify_xls(db, entry):
    import sys as _s
    if "/tmp/xlsdeps" not in _s.path:
        _s.path.insert(0, "/tmp/xlsdeps")
    import xlrd
    from truth import read_xls
    colnames, rows = read_xls.read_cells(entry["key"], xlrd)
    return verify_text(db, entry, colnames, rows)


def _mapinfo_cell_v(raw, tf, fam):
    """verifier 侧独立实现：raw 字段字节 + .tab 真型 → 值|None（Char 列级解码独立实现）。"""
    t = tf["type"]
    if t == "Char":
        body = raw.rstrip(b" \x00")
        enc = decode.col_encoding(fam, tf["name"])
        if enc is None:
            return None
        return body.decode(enc, "replace")
    if t == "Decimal":
        s = raw.strip(b" \x00").decode("ascii", "strict")
        return None if (s == "" or "*" in s) else s
    if t == "Smallint":
        return struct.unpack("<h", raw[:2])[0]
    if t == "Integer":
        return struct.unpack("<i", raw[:4])[0]
    if t == "Float":
        return struct.unpack("<d", raw[:8])[0]
    if t == "Logical":
        s = raw[:1].decode("ascii", "replace")
        return None if s.strip() == "" else s
    s = raw.rstrip(b" \x00").decode("ascii", "replace")
    return None if s == "" else s


def verify_mapinfo(db, entry):
    """腿A MapInfo 属性闸：.tab 真型 + .dat 定宽字节现读，逐列解码，闸1-3（属性-only）。"""
    schema, tname = entry["target"].split(".", 1)
    tname = tname.lower()
    fam = decode.load_decoding().get(entry.get("decoding"))
    tab_fields, dat = mapinfo.read_table(entry["key"])
    if dat is None:
        return {"table": f"{schema}.{tname}", "verdict": "ERROR", "stopped_at": "g1",
                "err": "MapInfo 缺 .dat"}
    colnames = dbf.disambiguate([f["name"] for f in tab_fields])
    pg_types = [entry["columns"][c] for c in colnames]
    src_cells = []
    for vals, deleted in dbf.iter_records(dat):
        if deleted:
            continue
        cells = [_mapinfo_cell_v(v, tf, fam) for v, tf in zip(vals, tab_fields)]
        src_cells.append(tuple(_canon_typed(c, pt) for c, pt in zip(cells, pg_types)))
    return _gates(db, schema, tname, colnames, pg_types, src_cells)


def _feat_vertices_v(feat):
    """verifier 侧独立实现：规范化几何 → 顶点扁平序列（canonical 顺序，含 Z）。退化/Null → []。"""
    t = feat["type"]
    if t == "Null":
        return []
    if t == "Point":
        return [feat["geom"]]
    g = feat["geom"]
    if t == "MultiPoint":
        return [] if len(g) == 0 else list(g)
    if t == "MultiLineString":
        if len(g) == 0 or any(len(line) < 2 for line in g):
            return []
        return [v for line in g for v in line]
    if t == "MultiPolygon":
        if len(g) == 0 or any(len(poly) == 0 or any(len(ring) < 4 for ring in poly) for poly in g):
            return []
        return [v for poly in g for ring in poly for v in ring]
    return []


_EXPECT_GEOM_TYPES = {
    1: {"ST_Point"}, 8: {"ST_MultiPoint"},
    3: {"ST_MultiLineString"}, 5: {"ST_MultiPolygon"},
    11: {"ST_Point", "ST_PointZ"}, 13: {"ST_MultiLineString", "ST_MultiLineStringZ"},
}


def verify_shapefile_geom(db, entry):
    """腿B 几何闸：计数 / SRID / 类型 / 顶点多重集（与源 .shp 双精度原值逐点全等，含 Z）。"""
    schema, tname = entry["target"].split(".", 1)
    tname = tname.lower()
    srid = str(entry["geom"]["srid"])
    shp_bytes = srcopen.read_member(entry["key"], ".shp", required=True)
    dbf_bytes = srcopen.read_member(entry["key"], ".dbf")
    delidx = ({i for i, (_, deleted) in enumerate(dbf.iter_records(dbf_bytes)) if deleted}
              if dbf_bytes is not None else set())   # 无属性层（geometry_only）无 .dbf

    header_type = struct.unpack_from("<I", shp_bytes, 32)[0]
    feats = [f for i, f in enumerate(shp.iter_features(shp_bytes)) if i not in delidx]
    src_multi = Counter()
    for f in feats:
        for v in _feat_vertices_v(f):
            src_multi[tuple(c.hex() for c in v)] += 1

    sq, gtab = quote_ident(schema), quote_ident(tname + "__geom_stg")
    cnt = int(rows(db, f"SELECT count(*) FROM {sq}.{gtab};")[0][0])
    if cnt != len(feats):
        return {"table": f"{schema}.{tname}.geom", "verdict": "FAIL", "stopped_at": "g2_geom",
                "g2_count": {"pass": False, "expect": len(feats), "got": cnt}}

    srids = [r[0] for r in rows(db, f"SELECT DISTINCT ST_SRID(geom)::text FROM {sq}.{gtab} WHERE geom IS NOT NULL;")]
    gtypes = [r[0] for r in rows(db, f"SELECT DISTINCT ST_GeometryType(geom) FROM {sq}.{gtab} WHERE geom IS NOT NULL;")]
    expect_types = _EXPECT_GEOM_TYPES.get(header_type, set())
    type_ok = srids == [srid] and (not gtypes or all(g in expect_types for g in gtypes))
    if not type_ok:
        return {"table": f"{schema}.{tname}.geom", "verdict": "FAIL", "stopped_at": "g_geom_meta",
                "srid": {"pass": srids == [srid], "expect": [srid], "got": srids},
                "type": {"pass": type_ok, "expect": sorted(expect_types), "got": gtypes}}

    zflag = header_type in (11, 13)
    q = (f"SELECT g.__rid, ST_X((d).geom)::text, ST_Y((d).geom)::text, ST_Z((d).geom)::text "
         f"FROM {sq}.{gtab} g, LATERAL ST_DumpPoints(g.geom) d "
         f"ORDER BY g.__rid, (d).path;")
    db_multi = Counter()
    for r in rows(db, q):
        x, y = float(r[1]).hex(), float(r[2]).hex()
        key = (x, y, float(r[3]).hex()) if zflag else (x, y)
        db_multi[key] += 1

    d1, d2 = src_multi - db_multi, db_multi - src_multi
    g3 = (not d1 and not d2)
    return {"table": f"{schema}.{tname}.geom", "verdict": "CONFORMS" if g3 else "FAIL",
            "g2_count": {"pass": True, "expect": len(feats), "got": cnt},
            "geom_meta": {"srid": srids, "type": gtypes, "z": zflag},
            "g3_vertex": {"pass": g3, "diff_src_only": len(d1), "diff_db_only": len(d2),
                          "samples_src_only": list(d1)[:5], "samples_db_only": list(d2)[:5]}}


def verify_shapefile(db, entry):
    schema, tname = entry["target"].split(".", 1)
    tname = tname.lower()
    fam = decode.load_decoding().get(entry.get("decoding"))
    dbf_bytes = srcopen.read_member(entry["key"], ".dbf", required=True)
    fields = dbf.parse_dbf(dbf_bytes)["fields"]
    colnames = dbf.disambiguate([f["name"] for f in fields])
    pg_types = [entry["columns"][c] for c in colnames]
    src_cells = []
    for vals, deleted in dbf.iter_records(dbf_bytes):
        if deleted:
            continue
        cells = [_dbf_cell(v, f, fam) for v, f in zip(vals, fields)]
        src_cells.append(tuple(_canon_typed(c, pt) for c, pt in zip(cells, pg_types)))
    return _gates(db, schema, tname, colnames, pg_types, src_cells)


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "cbdb_reh"
    want = sys.argv[2] if len(sys.argv) > 2 else "NIAN_HAO"
    entries = load_entries()
    e = next(x for x in entries if want in (x.get("target") or x.get("key")) and x["carrier"] in ("sqlite", "shapefile"))
    fn = verify_sqlite if e["carrier"] == "sqlite" else verify_shapefile
    print(json.dumps(fn(db, e), ensure_ascii=False, indent=2))
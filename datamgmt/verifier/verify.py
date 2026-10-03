# -*- coding: utf-8 -*-
"""verifier.verify —— 六道闸之 闸1/2/3（腿A sqlite + 腿B shapefile 属性），与 importer.load **零共用代码**。

独立性（§6.1）：期望值由 truth/ 直读源件字节现算，绝不取自装载之库；解码判表读同一份
decoding.yaml，但「字节→字符」之列级解码在本文件独立实现一遍（load.py 也各自写一遍）。
闸3：类型感知多重集差集；null 显式化哨兵 '␀'(U+2400)；numeric/bigint 按 Decimal 归约禁 float。
库侧读值经 -F'|'——段A 源表值不含 | 或换行（违者 assert 即停，另行换 COPY TO csv）。"""
import json
import os
import sys
import zipfile
from collections import Counter
from decimal import Decimal

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATAMGMT = os.path.dirname(_HERE)
if _DATAMGMT not in sys.path:
    sys.path.insert(0, _DATAMGMT)

import decode  # noqa: E402  判表读取（config 层）
from db import rows, quote_ident  # noqa: E402
from truth import roots, sqlite, dbf, shp  # noqa: E402

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
    """源/库两端口径统一：None 与哨兵→NULL；数值→Decimal 归约；其余 str。"""
    if v is None or v == NULL_SENT:
        return NULL_SENT
    if pg_type.startswith("numeric") or pg_type in ("bigint", "integer", "smallint"):
        return _canon_num(str(v))
    return str(v)


def _dbf_cell(raw, f, fam):
    """verifier 侧列级解码（独立实现）：raw 字段字节 → str|None。"""
    if f["type"] == "N":
        s = raw.strip(b" \x00").decode("ascii", "strict")
        return None if s == "" else s
    body = raw.rstrip(b" \x00")
    enc = decode.col_encoding(fam, f["name"])
    if enc is None:
        return None
    return body.decode(enc, "strict")


def _gates(db, schema, tname, colnames, pg_types, src_cells):
    """闸1 结构 / 闸2 计数 / 闸3 值级，不过即停（§6.1.5）。src_cells 已按口径归一。"""
    expect_names = [c.lower() for c in colnames]
    dbcols = rows(db, (
        "SELECT column_name FROM information_schema.columns "
        f"WHERE table_schema='{schema}' AND table_name='{tname}__stg' ORDER BY ordinal_position;"
    ))
    got_names = [r[0] for r in dbcols]
    if got_names != expect_names:
        return {"table": f"{schema}.{tname}", "verdict": "FAIL", "stopped_at": "g1",
                "g1_structure": {"pass": False, "expect": expect_names, "got": got_names}}

    cnt = int(rows(db, f"SELECT count(*) FROM {quote_ident(schema)}.{quote_ident(tname + '__stg')};")[0][0])
    if cnt != len(src_cells):
        return {"table": f"{schema}.{tname}", "verdict": "FAIL", "stopped_at": "g2",
                "g2_count": {"pass": False, "expect": len(src_cells), "got": cnt}}

    for cell in src_cells:
        for v in cell:
            assert "\n" not in v and "|" not in v, \
                f"{tname} 值含 '|' 或换行：段A -F'|' 读法不适用（须换 COPY TO csv）"

    src_multi = Counter(src_cells)
    selexpr = ", ".join(
        f"COALESCE({quote_ident(c.lower())}::text,'{NULL_SENT}')" for c in colnames
    )
    db_rows = rows(db, f"SELECT {selexpr} FROM {quote_ident(schema)}.{quote_ident(tname + '__stg')};")
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


def verify_shapefile_geom(db, entry):
    """腿B 几何闸：计数 / SRID / 类型 / 顶点多重集（与源 .shp 双精度原值逐点全等）。"""
    schema, tname = entry["target"].split(".", 1)
    tname = tname.lower()
    zip_path, member = entry["key"].split("::", 1)
    zp = os.path.join(USEDATA, zip_path)
    srid = str(entry["geom"]["srid"])
    with zipfile.ZipFile(zp) as z:
        shp_bytes = z.read(member + ".shp")
    pts = list(shp.iter_points(shp_bytes))
    src_multi = Counter((repr(x), repr(y)) for x, y in pts)

    sq, gtab = quote_ident(schema), quote_ident(tname + "__geom_stg")
    cnt = int(rows(db, f"SELECT count(*) FROM {sq}.{gtab};")[0][0])
    if cnt != len(pts):
        return {"table": f"{schema}.{tname}.geom", "verdict": "FAIL", "stopped_at": "g2_geom",
                "g2_count": {"pass": False, "expect": len(pts), "got": cnt}}

    srids = [r[0] for r in rows(db, f"SELECT DISTINCT ST_SRID(geom)::text FROM {sq}.{gtab};")]
    gtypes = [r[0] for r in rows(db, f"SELECT DISTINCT ST_GeometryType(geom) FROM {sq}.{gtab};")]
    if srids != [srid] or gtypes != ["ST_Point"]:
        return {"table": f"{schema}.{tname}.geom", "verdict": "FAIL", "stopped_at": "g_geom_meta",
                "srid": {"pass": srids == [srid], "expect": [srid], "got": srids},
                "type": {"pass": gtypes == ["ST_Point"], "expect": ["ST_Point"], "got": gtypes}}

    db_pts = rows(db, f"SELECT ST_X(geom)::text, ST_Y(geom)::text FROM {sq}.{gtab};")
    db_multi = Counter(tuple(r) for r in db_pts)
    d1, d2 = src_multi - db_multi, db_multi - src_multi
    g3 = (not d1 and not d2)
    return {"table": f"{schema}.{tname}.geom", "verdict": "CONFORMS" if g3 else "FAIL",
            "g2_count": {"pass": True, "expect": len(pts), "got": cnt},
            "geom_meta": {"srid": srids, "type": gtypes},
            "g3_vertex": {"pass": g3, "diff_src_only": len(d1), "diff_db_only": len(d2),
                          "samples_src_only": list(d1)[:5], "samples_db_only": list(d2)[:5]}}


def verify_shapefile(db, entry):
    schema, tname = entry["target"].split(".", 1)
    tname = tname.lower()
    zip_path, member = entry["key"].split("::", 1)
    zp = os.path.join(USEDATA, zip_path)
    fam = decode.load_decoding().get(entry.get("decoding"))
    with zipfile.ZipFile(zp) as z:
        dbf_bytes = z.read(member + ".dbf")
    fields = dbf.parse_dbf(dbf_bytes)["fields"]
    colnames = [f["name"] for f in fields]
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
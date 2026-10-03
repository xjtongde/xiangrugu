# -*- coding: utf-8 -*-
"""importer.load —— 照 sources.yaml 装载（§5.5）。段A 先实现腿 A（sqlite）。

命名规则（单一决定，两端同用）：目标 schema/表/列 一律**小写**（PG 未引用标识符惯例）；
源名仅作 sources.yaml 之映射键。CBDB 列本已小写，表名大写→小写。
值根：sqlite 原生类型 int/float/str/bytes/None 忠实搬运；CSV 全字段加引号（NULL=空字段）。
"""
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATAMGMT = os.path.dirname(_HERE)
if _DATAMGMT not in __import__("sys").path:
    __import__("sys").path.insert(0, _DATAMGMT)

import decode  # noqa: E402  解码判表读取（config 层）
from db import execute, copy_stream, quote_ident, ensure_schemas  # noqa: E402
from truth import roots, sqlite, dbf, shp  # noqa: E402
from truth.srcopen import read_member  # noqa: E402

USEDATA = roots.usedata()
CFG = os.path.join(_DATAMGMT, "config", "sources.yaml")


def load_entries():
    out = []
    with open(CFG, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s.startswith("- "):
                out.append(json.loads(s[2:]))
    return out


def _csv_field(v):
    """CSV 段编：None→空字段(NULL)；其余 str() 后全加引号、内引号翻倍。"""
    if v is None:
        return ""
    s = str(v)
    return '"' + s.replace('"', '""') + '"'


def _target_parts(entry):
    schema, tname = entry["target"].split(".", 1)
    return schema, tname.lower()


def load_sqlite_staging(db, entry):
    """读 sqlite 源表 → 落 <schema>.<table>__stg。返回 (staging表名, colnames, pg_types, 行数)。"""
    nas_path, table = entry["key"].split("::", 1)
    path = os.path.join(USEDATA, nas_path)
    schema, tname = _target_parts(entry)
    ensure_schemas(db)

    colnames, rows = sqlite.read_values(path, table)
    pg_types = [entry["columns"][c] for c in colnames]

    stg = tname + "__stg"
    sq, st = quote_ident(schema), quote_ident(stg)
    execute(db, f"DROP TABLE IF EXISTS {sq}.{st};")
    coldefs = ", ".join(
        f"{quote_ident(c.lower())} {t}" for c, t in zip(colnames, pg_types)
    )
    execute(db, f"CREATE TABLE {sq}.{st} ({coldefs});")

    csv_lines = [",".join(_csv_field(v) for v in row) for row in rows]
    copy_cmd = (
        f"COPY {sq}.{st} ({', '.join(quote_ident(c.lower()) for c in colnames)}) "
        "FROM STDIN WITH (FORMAT csv);"
    )
    copy_stream(db, copy_cmd, "\n".join(csv_lines))

    return stg, colnames, pg_types, len(rows)


def promote(db, entry):
    """原子换名 __stg → 正表（先 DROP 旧正表再 RENAME）。"""
    schema, tname = _target_parts(entry)
    sq, stg, t = quote_ident(schema), quote_ident(tname + "__stg"), quote_ident(tname)
    execute(db, f"DROP TABLE IF EXISTS {sq}.{t};")
    execute(db, f"ALTER TABLE {sq}.{stg} RENAME TO {t};")


def _shapefile_cell(raw, f, fam):
    """importer 侧列级解码（独立实现，§6.1）：raw 字段字节 → str|None。

    N 字段按 ASCII 原样保真（禁 float）；C/D/L/M 按判表定编码解码，
    非法/截断字节 → U+FFFD（每处一个，两端一致）；判不定 → None（该列不装）。"""
    if f["type"] == "N":
        s = raw.strip(b" \x00").decode("ascii", "strict")
        return None if s == "" else s
    body = raw.rstrip(b" \x00")
    enc = decode.col_encoding(fam, f["name"])
    if enc is None:
        return None
    return body.decode(enc, "replace")


def _deleted_indices(dbf_bytes):
    return {i for i, (_, deleted) in enumerate(dbf.iter_records(dbf_bytes)) if deleted}


def _feat_wkt(feat):
    """规范化几何 → WKT（repr 双精度原样；含 Z；PolyLine/Polygon 一律 MULTI）。Null → None。"""
    t = feat["type"]
    if t == "Null":
        return None
    z = " Z" if feat.get("z") else ""
    g = feat["geom"]
    if t == "Point":
        return f"POINT{z}({' '.join(repr(c) for c in g)})"
    if t == "MultiPoint":
        return "MULTIPOINT(" + ",".join("(" + " ".join(repr(c) for c in p) + ")" for p in g) + ")"
    if t == "MultiLineString":
        return (f"MULTILINESTRING{z}("
                + ",".join("(" + ",".join(" ".join(repr(c) for c in v) for v in line) + ")" for line in g)
                + ")")
    if t == "MultiPolygon":
        def ring(r):
            return "(" + ",".join(" ".join(repr(c) for c in v) for v in r) + ")"
        return "MULTIPOLYGON(" + ",".join("(" + ",".join(ring(r) for r in poly) + ")" for poly in g) + ")"
    raise ValueError(f"未知几何类型 {t}")


def _feat_vertices(feat):
    """规范化几何 → 顶点扁平序列（canonical 顺序，含 Z；供校验器与 ST_DumpPoints 对齐）。"""
    t = feat["type"]
    if t in ("Null",):
        return []
    if t == "Point":
        return [feat["geom"]]
    if t == "MultiPoint":
        return list(feat["geom"])
    if t == "MultiLineString":
        return [v for line in feat["geom"] for v in line]
    if t == "MultiPolygon":
        return [v for poly in feat["geom"] for ring in poly for v in ring]
    return []


def load_shapefile_staging(db, entry):
    """读 shapefile .dbf 属性 → 落 <schema>.<table>__stg（首列 __rid = 源记录原始序号，跳过删除标记者）。"""
    schema, tname = _target_parts(entry)
    fam = decode.load_decoding().get(entry.get("decoding"))
    ensure_schemas(db)

    dbf_bytes = read_member(entry["key"], ".dbf", required=True)
    fields = dbf.parse_dbf(dbf_bytes)["fields"]
    colnames = [f["name"] for f in fields]
    pg_types = [entry["columns"][c] for c in colnames]

    stg = tname + "__stg"
    sq, st = quote_ident(schema), quote_ident(stg)
    execute(db, f"DROP TABLE IF EXISTS {sq}.{st};")
    coldefs = "__rid bigint, " + ", ".join(
        f"{quote_ident(c.lower())} {t}" for c, t in zip(colnames, pg_types)
    )
    execute(db, f"CREATE TABLE {sq}.{st} ({coldefs});")

    csv_lines, nrows = [], 0
    for i, (vals, deleted) in enumerate(dbf.iter_records(dbf_bytes)):
        if deleted:
            continue
        cells = [_shapefile_cell(v, f, fam) for v, f in zip(vals, fields)]
        csv_lines.append(f"{i}," + ",".join(_csv_field(v) for v in cells))
        nrows += 1
    copy_cmd = (
        f"COPY {sq}.{st} (__rid, {', '.join(quote_ident(c.lower()) for c in colnames)}) "
        "FROM STDIN WITH (FORMAT csv);"
    )
    copy_stream(db, copy_cmd, "\n".join(csv_lines))
    return stg, colnames, pg_types, nrows


def load_shapefile_geom(db, entry):
    """读 .shp 全类型要素 → <table>__geom_stg(__rid, geom)。__rid=源记录序号，跳过删除标记。CRS 照存不转。
    几何类型照源（Point/ MultiPoint/ MultiLineString(PolyLine)/ MultiPolygon(Polygon)，Z 保留）。"""
    schema, tname = _target_parts(entry)
    srid = int(entry["geom"]["srid"])
    ensure_schemas(db)

    shp_bytes = read_member(entry["key"], ".shp", required=True)
    dbf_bytes = read_member(entry["key"], ".dbf")
    delidx = _deleted_indices(dbf_bytes) if dbf_bytes is not None else set()

    rows = []
    for i, feat in enumerate(shp.iter_features(shp_bytes)):
        if i in delidx:
            continue
        wkt = _feat_wkt(feat)
        rows.append(f"{i}," + ("NULL" if wkt is None else _csv_field(wkt)))

    sq, gtab = quote_ident(schema), quote_ident(tname + "__geom_stg")
    execute(db, f"DROP TABLE IF EXISTS {sq}.{gtab};")
    execute(db, f"CREATE TABLE {sq}.{gtab} (__rid bigint, geom geometry);")
    scratch = quote_ident("_g_scratch")
    execute(db, f"DROP TABLE IF EXISTS {sq}.{scratch};")
    execute(db, f"CREATE TABLE {sq}.{scratch}(__rid bigint, wkt text);")
    copy_stream(db, f"COPY {sq}.{scratch}(__rid,wkt) FROM STDIN WITH (FORMAT csv);", "\n".join(rows))
    execute(db, f"INSERT INTO {sq}.{gtab} "
                f"SELECT __rid, CASE WHEN wkt IS NULL THEN NULL ELSE ST_GeomFromText(wkt, {srid}) END "
                f"FROM {sq}.{scratch};")
    execute(db, f"DROP TABLE IF EXISTS {sq}.{scratch};")
    return gtab, len(rows)


def assemble_shapefile(db, entry):
    """几何并入正表：__stg 加 geom 列（无 typmod，SRID 已烘焙于值）→按 __rid 回填→去 __rid→删 __geom_stg→换名正表。§5.5。"""
    schema, tname = _target_parts(entry)
    sq, stg = quote_ident(schema), quote_ident(tname + "__stg")
    gtab = quote_ident(tname + "__geom_stg")
    execute(db, f"ALTER TABLE {sq}.{stg} ADD COLUMN geom geometry;")
    execute(db, f"UPDATE {sq}.{stg} a SET geom = g.geom FROM {sq}.{gtab} g WHERE g.__rid = a.__rid;")
    execute(db, f"ALTER TABLE {sq}.{stg} DROP COLUMN __rid;")
    execute(db, f"DROP TABLE IF EXISTS {sq}.{gtab};")
    promote(db, entry)


def promote_geom_only(db, entry):
    """无属性层（geometry_only）：几何 staging 去 __rid 后换名正表。"""
    schema, tname = _target_parts(entry)
    sq, gtab = quote_ident(schema), quote_ident(tname + "__geom_stg")
    execute(db, f"ALTER TABLE {sq}.{gtab} DROP COLUMN __rid;")
    execute(db, f"DROP TABLE IF EXISTS {sq}.{quote_ident(tname)};")
    execute(db, f"ALTER TABLE {sq}.{gtab} RENAME TO {quote_ident(tname)};")


if __name__ == "__main__":
    import sys
    db = sys.argv[1] if len(sys.argv) > 1 else "cbdb_reh"
    entries = load_entries()
    # 段A 源1：CBDB NIAN_HAO
    e = next(x for x in entries if x["carrier"] == "sqlite" and x["target"].endswith("NIAN_HAO"))
    stg, cols, types, n = load_sqlite_staging(db, e)
    print(f"staging {stg}: {n} 行, {len(cols)} 列 已装载（未换名）")
    print("列:", list(zip(cols, types)))
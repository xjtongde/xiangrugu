# -*- coding: utf-8 -*-
"""importer.load —— 照 sources.yaml 装载（§5.5）。段A 先实现腿 A（sqlite）。

命名规则（单一决定，两端同用）：目标 schema/表/列 一律**小写**（PG 未引用标识符惯例）；
源名仅作 sources.yaml 之映射键。CBDB 列本已小写，表名大写→小写。
值根：sqlite 原生类型 int/float/str/bytes/None 忠实搬运；CSV 全字段加引号（NULL=空字段）。
"""
import json
import os
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATAMGMT = os.path.dirname(_HERE)
if _DATAMGMT not in __import__("sys").path:
    __import__("sys").path.insert(0, _DATAMGMT)

import decode  # noqa: E402  解码判表读取（config 层）
from db import execute, copy_stream, quote_ident, ensure_schemas  # noqa: E402
from truth import roots, sqlite, dbf, shp  # noqa: E402

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

    N 字段按 ASCII 原样保真（禁 float）；C/D/L/M 按判表定编码 strict 解码；
    判不定 → None（该列不装）。"""
    if f["type"] == "N":
        s = raw.strip(b" \x00").decode("ascii", "strict")
        return None if s == "" else s
    body = raw.rstrip(b" \x00")
    enc = decode.col_encoding(fam, f["name"])
    if enc is None:
        return None
    return body.decode(enc, "strict")


def load_shapefile_staging(db, entry):
    """读 shapefile 之 .dbf（属性列）→ 落 <schema>.<table>__stg。段A腿B 先只装属性，几何另步。"""
    zip_path, member = entry["key"].split("::", 1)
    zp = os.path.join(USEDATA, zip_path)
    schema, tname = _target_parts(entry)
    fam = decode.load_decoding().get(entry.get("decoding"))
    ensure_schemas(db)

    with zipfile.ZipFile(zp) as z:
        dbf_bytes = z.read(member + ".dbf")
    fields = dbf.parse_dbf(dbf_bytes)["fields"]
    colnames = [f["name"] for f in fields]
    pg_types = [entry["columns"][c] for c in colnames]

    stg = tname + "__stg"
    sq, st = quote_ident(schema), quote_ident(stg)
    execute(db, f"DROP TABLE IF EXISTS {sq}.{st};")
    coldefs = ", ".join(f"{quote_ident(c.lower())} {t}" for c, t in zip(colnames, pg_types))
    execute(db, f"CREATE TABLE {sq}.{st} ({coldefs});")

    csv_lines, nrows = [], 0
    for vals, deleted in dbf.iter_records(dbf_bytes):
        if deleted:
            continue
        cells = [_shapefile_cell(v, f, fam) for v, f in zip(vals, fields)]
        csv_lines.append(",".join(_csv_field(v) for v in cells))
        nrows += 1
    copy_cmd = (
        f"COPY {sq}.{st} ({', '.join(quote_ident(c.lower()) for c in colnames)}) "
        "FROM STDIN WITH (FORMAT csv);"
    )
    copy_stream(db, copy_cmd, "\n".join(csv_lines))
    return stg, colnames, pg_types, nrows


def load_shapefile_geom(db, entry):
    """读 .shp Point 要素 → 落 独立几何 staging <table>__geom_stg(__rid, geom)。CRS 照存不转（§12口径一）。"""
    zip_path, member = entry["key"].split("::", 1)
    zp = os.path.join(USEDATA, zip_path)
    schema, tname = _target_parts(entry)
    srid = int(entry["geom"]["srid"])
    ensure_schemas(db)

    with zipfile.ZipFile(zp) as z:
        shp_bytes = z.read(member + ".shp")
    pts = list(shp.iter_points(shp_bytes))

    sq, gtab = quote_ident(schema), quote_ident(tname + "__geom_stg")
    execute(db, f"DROP TABLE IF EXISTS {sq}.{gtab};")
    execute(db, f"CREATE TABLE {sq}.{gtab} (__rid bigint, geom geometry(Point,{srid}));")
    # 每 db.py 调 = 独立 psql 会话，跨调用 TEMP 表不存续 → 用持久 scratch（用完即 DROP）
    scratch = quote_ident("_g_scratch")
    execute(db, f"DROP TABLE IF EXISTS {sq}.{scratch};")
    execute(db, f"CREATE TABLE {sq}.{scratch}(__rid bigint, x double precision, y double precision);")
    lines = [f"{i + 1},{repr(x)},{repr(y)}" for i, (x, y) in enumerate(pts)]
    copy_stream(db, f"COPY {sq}.{scratch}(__rid,x,y) FROM STDIN WITH (FORMAT csv);", "\n".join(lines))
    execute(db, f"INSERT INTO {sq}.{gtab} SELECT __rid, ST_SetSRID(ST_Point(x,y), {srid}) FROM {sq}.{scratch};")
    execute(db, f"DROP TABLE IF EXISTS {sq}.{scratch};")
    return gtab, len(pts)


if __name__ == "__main__":
    import sys
    db = sys.argv[1] if len(sys.argv) > 1 else "cbdb_reh"
    entries = load_entries()
    # 段A 源1：CBDB NIAN_HAO
    e = next(x for x in entries if x["carrier"] == "sqlite" and x["target"].endswith("NIAN_HAO"))
    stg, cols, types, n = load_sqlite_staging(db, e)
    print(f"staging {stg}: {n} 行, {len(cols)} 列 已装载（未换名）")
    print("列:", list(zip(cols, types)))
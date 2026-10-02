# -*- coding: utf-8 -*-
"""build_sources_yaml.py —— 由真值基线生成 sources.yaml 骨架（§5.1 一源一条）。

目标命名（本阶段定，随阶段三 load.py 使用）：
  CBDB sqlite(78)      → public schema（数据库 cbdb 自专）
  CHGIS shapefile(706) → chgis schema
  MapInfo V3(142)      → harv  schema
  tab(5)/xls(2)        → harv  schema（xls 无读数器，暂不装）
列→PG 类型按 §5.3（DBF: C→text / N(,0)→bigint / N(,d)→numeric / D,L→text / F→double precision；
sqlite: INTEGER/smallint/int/BOOLEAN→bigint / REAL/FLOAT/double→double precision / text→text / BLOB→bytea）。

未定项（诚实标注）：
  shapefile 之 geom.srid —— 需 .prj 指纹提取（§5.1 geom 字段），阶段三预演段 A 前补；
  key_cols —— 值级对账键，阶段三各源按表性质定（§6.3）。
"""
import json
import os
import posixpath
import re


HERE = os.path.dirname(os.path.abspath(__file__))
DATAMGMT = os.path.dirname(HERE)
CONFIG = os.path.join(DATAMGMT, "config")
RECON = os.path.join(DATAMGMT, "recon")


def dbf_pg(f):
    t = f['type']
    if t == 'C':
        return 'text'
    if t == 'N':
        return 'bigint' if f['decimals'] == 0 else f"numeric({f['length']},{f['decimals']})"
    if t in ('D', 'L', 'M'):
        return 'text'
    if t == 'F':
        return 'double precision'
    return 'text'


def sqlite_pg(decl):
    d = decl.split('(')[0].strip().lower()
    if d in ('integer', 'int', 'smallint', 'tinyint', 'bigint', 'boolean', 'bit'):
        return 'bigint'
    if d in ('real', 'float', 'double', 'decimal', 'numeric'):
        return 'double precision'
    if d == 'blob':
        return 'bytea'
    return 'text'


def mapinfo_pg(f):
    t = f['type'].lower()
    if t == 'char':
        return 'text'
    if t == 'integer':
        return 'integer'
    if t == 'smallint':
        return 'smallint'
    if t == 'float':
        return 'double precision'
    if t == 'decimal':
        return f"numeric({f['width']},{f['decimals']})"
    if t in ('logical', 'date'):
        return 'text'
    return 'text'


def resolve_srid(prj_norm):
    """.prj 文本 → (srid, 依据)。确定者给 EPSG（web 核实）；非标准命名者显式 review 不猜。§5.3 H-2。"""
    if not prj_norm:
        return ("0", "no_prj (源件未声明，§5.3)")
    t = prj_norm.lower()
    if 'gcs_wgs_1984' in t:
        return ("4326", "GCS_WGS_1984 地理坐标")
    if 'xian_1980_gk_zone_19' in t or 'xian_1980_gauss_kruger_zone_19' in t:
        return ("2333", "Xian 1980 / Gauss-Kruger zone 19 (CM 111E，108–114E)")
    if 'xian 1980' in t and 'gauss' not in t and 'gk' not in t and 'zone' not in t:
        return ("4610", "Xian 1980 地理坐标")
    if 'krasovsky_1940' in t or 'krassovsky' in t:
        return ("", "review: 非标准命名(Krasovsky 椭球)，候选 4284 Pulkovo1942 / 4214 Beijing1954，待定")
    if 'clarke_1866' in t:
        return ("", "review: Clarke 1866 椭球，候选 4008")
    if 'north_american_1927' in t:
        return ("", "review: NAD27，候选 4267")
    if 'transverse_mercator' in t:
        return ("", "review: Transverse_Mercator 自定义（datum unknown）")
    return ("", "review")


def q(s):
    return json.dumps(s, ensure_ascii=False)


def main():
    srcs = []

    # CBDB sqlite 78
    cbdb = json.load(open(os.path.join(RECON, "cbdb_baseline.json"), encoding="utf-8"))
    new = cbdb['versions']['20260919（权威源 harvard/cbdb）']['tables']
    for t in new:
        cols = {c['name']: sqlite_pg(c['type']) for c in t['columns']}
        srcs.append({
            "key": "harvard/cbdb/cbdb_20260919.sqlite3::" + t['name'],
            "carrier": "sqlite", "target": "public." + t['name'],
            "truth_rows": t['rows'], "columns": cols,
        })

    # shapefile 706
    for line in open(os.path.join(RECON, "truth_baseline.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        if r.get('kind') != 'shapefile':
            continue
        has_dbf = 'fields' in r
        has_shp = 'shp_rows' in r
        if not has_dbf and not has_shp:
            continue    # 孤儿成员（如 Ming_Stations_2016 残留 .cpg）——非真实图层，剔除
        cols = {f['name']: dbf_pg(f) for f in r.get('fields', [])}
        srid, srid_note = resolve_srid(r.get('crs'))
        member = posixpath.join(r.get('dir', ''), r['layer'])
        srcs.append({
            "key": r['zip'] + "::" + member,
            "carrier": "shapefile", "target": "chgis." + r['layer'],
            "truth_rows": r.get('dbf_rows'), "columns": cols,
            "geom": {"srid": srid, "note": srid_note, "prj_present": bool(r.get('crs'))},
            "geometry_only": (not has_dbf) and has_shp,
        })

    # MapInfo 142
    mi = json.load(open(os.path.join(RECON, "mapinfo_baseline.json"), encoding="utf-8"))
    for m in mi:
        cols = {f['name']: mapinfo_pg(f) for f in m.get('fields', [])}
        srcs.append({
            "key": m['zip'] + "::" + m.get('member', '?'),
            "carrier": "mapinfo", "target": "harv." + (m.get('member', '?').rsplit('.', 1)[0]),
            "truth_rows": m.get('rows'),
            "charset": m.get('charset_codec'),
            "columns": cols,
            "parsed_n": m.get('parsed_fields'), "declared_n": m.get('n_fields'),
        })

    # tab 5
    tab = json.load(open(os.path.join(RECON, "tab_baseline.json"), encoding="utf-8"))
    for t_ in tab:
        name = os.path.basename(t_['path']).replace('.tab', '')
        hdr = t_.get('first_line', '').lstrip('\ufeff')
        names = hdr.split(t_.get('delimiter', '\t')) if hdr else []
        srcs.append({
            "key": t_['path'], "carrier": "tsv", "target": "harv." + name,
            "truth_rows": t_['rows_total'], "encoding": t_['encoding'],
            "columns": [n for n in names if n], "columns_typed": False,
            "note": "列名取自表头行；PG 类型待阶段三按§5.3逐列嗅探(表头+样本)",
        })

    # xls 2（无读数器）
    xls = json.load(open(os.path.join(RECON, "xls_baseline.json"), encoding="utf-8"))
    for x in xls:
        srcs.append({
            "key": x['path'], "carrier": "xls", "target": None,
            "truth_rows": None, "columns": None,
            "status": "reader-missing(不装,待 xls 读数器)",
        })

    header = [
        "title: " + q("源清单 sources.yaml（§5.1）——阶段二生成，一源一条"),
        "generator: " + q("datamgmt/maintenance/build_sources_yaml.py"),
        "target: " + q("database=cbdb / host=192.168.3.32:5433 / instance=pg32b"),
        "schema_map: " + q("sqlite→public, shapefile→chgis, mapinfo→harv, tab→harv, xls→harv(待读数器)"),
        "geom_srid_status: " + q("shapefile SRID 已按 .prj 定：571 层确认(4326/2333/4610)＋4 层无 prj→0＋131 层非标准命名 review 待定"),
        "todo_key_cols: " + q("值级对账键各源按表性质定（§6.3），阶段三补"),
        "sources:",
    ]
    for s in srcs:
        header.append("  - " + json.dumps(s, ensure_ascii=False, sort_keys=True))

    os.makedirs(CONFIG, exist_ok=True)
    with open(os.path.join(CONFIG, "sources.yaml"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(header) + "\n")

    from collections import Counter
    c = Counter(s['carrier'] for s in srcs)
    print("sources 总数:", len(srcs), dict(c))


if __name__ == "__main__":
    main()
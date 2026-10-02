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
        cols = {f['name']: dbf_pg(f) for f in r.get('fields', [])}
        srcs.append({
            "key": r['zip'] + ("::" + r['layer'] if r.get('dir') or r.get('layer') else ""),
            "carrier": "shapefile", "target": "chgis." + r['layer'],
            "truth_rows": r.get('dbf_rows'), "columns": cols,
            "no_dbf_fields": not r.get('fields'),
        })

    # MapInfo 142
    mi = json.load(open(os.path.join(RECON, "mapinfo_baseline.json"), encoding="utf-8"))
    for m in mi:
        srcs.append({
            "key": m['zip'] + "::" + m.get('member', '?'),
            "carrier": "mapinfo", "target": "harv." + (m.get('member', '?').rsplit('.', 1)[0]),
            "truth_rows": m.get('rows', None),
            "charset": m.get('charset_codec'),
            "columns": None,  # 阶段三由 .tab 解析补全
        })

    # tab 5
    tab = json.load(open(os.path.join(RECON, "tab_baseline.json"), encoding="utf-8"))
    for t_ in tab:
        name = os.path.basename(t_['path']).replace('.tab', '')
        srcs.append({
            "key": t_['path'], "carrier": "tsv", "target": "harv." + name,
            "truth_rows": t_['rows_total'], "encoding": t_['encoding'],
            "columns": None,  # 阶段三按表头行补全
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
        "todo_geom_srid: " + q("shapefile 之 srid 待 .prj 指纹提取补（§5.1 geom；阶段三段A前）"),
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
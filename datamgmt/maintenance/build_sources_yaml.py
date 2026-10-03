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
    """.prj 文本 → (srid, 依据)。确定者给 EPSG（web 核实）；不确定者不猜。

    CRS 裁决（段B，§5.3 H-2＋§12口径一「照存不转」）：
    * GCS_Krasovsky_1940 / krass 椭球(6378245,298.3) 地理坐标 → 4214 Beijing 1954
      （中国 CHGIS 语境；Krasovsky 椭球地理坐标之标准 EPSG。1 例标 "Krassovsky,1942" 备 4284，见 note）。
    * GCS_Assumed_Geographic_1 / D_NAD27、GCS_Clarke_1866 → 4267 NAD27（备 4008，已弃用）。
    * Transverse_Mercator 自定义（datum/椭球 unknown）→ 0，照存不转、不造 CRS。
    """
    if not prj_norm:
        return ("0", "no_prj 源件未声明 CRS，照存不转")
    t = prj_norm.lower()
    if 'gcs_wgs_1984' in t:
        return ("4326", "GCS_WGS_1984 地理坐标")
    if 'xian_1980_gk_zone_19' in t or 'xian_1980_gauss_kruger_zone_19' in t:
        return ("2333", "Xian 1980 / Gauss-Kruger zone 19 (CM 111E，108–114E)")
    if 'xian 1980' in t and 'gauss' not in t and 'gk' not in t and 'zone' not in t:
        return ("4610", "Xian 1980 地理坐标")
    if 'transverse_mercator' in t and 'unknown' in t:
        return ("0", "自定义 Transverse_Mercator（datum/椭球 unknown），无标准 EPSG，照存不转")
    if 'north_american_1927' in t or 'assumed_geographic_1' in t:
        return ("4267", "NAD27 地理坐标（Clarke1866 椭球）")
    if 'clarke_1866' in t:
        return ("4267", "Clarke1866 地理坐标 → NAD27 datum（备已弃用之 4008）")
    if 'krasovsky' in t or 'krassovsky' in t or 'krass' in t:
        return ("4214", "Krasovsky1940 椭球地理坐标 → Beijing 1954 (EPSG 4214)；标'1942'者备 4284")
    return ("", "review")


def doi_of(zip_path):
    m = re.search(r'doi_10_7910/DVN/([A-Za-z0-9]+)', zip_path)
    return m.group(1) if m else '?'


def marker_of(zip_path, layer):
    k = (zip_path + layer).lower()
    if 'big5' in k:
        return 'big5'
    if 'gbk' in k or '_gb' in k or 'gb2312' in k:
        return 'gbk'
    if '_utf' in k:
        return 'utf8'
    return None


def decoding_of(zip_path, layer):
    """返回 decoding.yaml 族 id（DOI_{doi}_{marker|nomark}）。§6.1 两侧据此读同一份判表。"""
    d = doi_of(zip_path)
    m = marker_of(zip_path, layer)
    return f"DOI_{d}_{m or 'nomark'}"


def q(s):
    return json.dumps(s, ensure_ascii=False)


def _dedupe_shapefiles(shp_srcs, collisions_path=None):
    """同 target 多副本（顺 §5.2 闸0）：去 HIMIVE（V3_Data_Archive 合集镜像）→ 同 DOI 保留最少 '::'（直取非嵌套）。
    内容差异已另案查明（见 recon/collisions.json 与段B报告）：v2_1820_cnty_pts_{gb,utf} 两个版本 NAME_PY 一处
    'Shuyang/Muyang' 差异，已按「忠于图层本体 DOI（ZZKZ6U CHGIS_V2），弃合集镜像」取值并逐案向用户报告。"""
    from collections import defaultdict
    if collisions_path is None:
        collisions_path = os.path.join(RECON, "collisions.json")
    by = defaultdict(list)
    for s in shp_srcs:
        by[s["target"]].append(s)
    out, collisions = [], []
    for target, lst in sorted(by.items()):
        if len(lst) == 1:
            out.append(lst[0])
            continue
        kept = [s for s in lst if "DVN/HIMIVE" not in s["key"]] or lst[:]
        if len(kept) > 1:
            kept.sort(key=lambda s: s["key"].count("::"))
            kept = kept[:1]
        out.append(kept[0])
        collisions.append({"target": target, "n_copies": len(lst),
                           "copies": [s["key"] for s in lst], "kept": kept[0]["key"]})
    if collisions:
        os.makedirs(os.path.dirname(collisions_path), exist_ok=True)
        json.dump({"n_collisions": len(collisions), "collisions": collisions},
                  open(collisions_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return out


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
    shp_srcs = []
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
        shp_srcs.append({
            "key": r['zip'] + "::" + member,
            "carrier": "shapefile", "target": "chgis." + r['layer'],
            "truth_rows": r.get('dbf_rows'), "columns": cols,
            "decoding": r['layer'].lower(),
            "geom": {"srid": srid, "note": srid_note, "prj_present": bool(r.get('crs'))},
            "geometry_only": (not has_dbf) and has_shp,
        })
    srcs.extend(_dedupe_shapefiles(shp_srcs))

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

    # xls 2（xlrd 已读全 schema，隔离环境 /tmp/xlsdeps）
    xls = json.load(open(os.path.join(RECON, "xls_baseline.json"), encoding="utf-8"))
    for x in xls:
        if not x.get('registered'):
            srcs.append({"key": x['path'], "carrier": "xls", "target": None,
                         "columns": None, "status": "未登记不装"})
            continue
        cols = {c['name']: c['pg_type'] for c in x['columns']}
        srcs.append({
            "key": x['path'], "carrier": "xls",
            "target": "harv." + os.path.basename(x['path']).rsplit('.', 1)[0],
            "truth_rows": x['data_rows'], "columns": cols,
            "sheet": x['sheet'], "header_row": x['header_row'],
            "drop_cols": x['drop_cols'],
        })

    header = [
        "title: " + q("源清单 sources.yaml（§5.1）——阶段二生成，一源一条"),
        "generator: " + q("datamgmt/maintenance/build_sources_yaml.py"),
        "target: " + q("database=cbdb / host=192.168.3.32:5433 / instance=pg32b"),
        "schema_map: " + q("sqlite→public, shapefile→chgis, mapinfo→harv, tab→harv, xls→harv"),
        "geom_srid_status: " + q("shapefile SRID 已按 .prj 全定：4326×35, 2333×534, 4610×2, 4214×124(Krasovsky→Beijing1954), 4267×2(NAD27), 0×8(3无prj+5自定义TM，照存不转)"),
        "collisions: " + q("40 图层同名多副本已按闸0裁决（recon/collisions.json）；其中 v2_1820_cnty_pts_{gb,utf} 双版本字节有异，已逐案报告用户"),
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
# -*- coding: utf-8 -*-
"""pg32b 数据总目 · 构建器

输入(只读): /tmp/xrg_demo/catalog.json —— extract_catalog.py 产物（399 表 × 7,168 列，count 精确实测，2026-09-27）
            descs.py —— 语义层（三档信度说明 / 家族归类 / 关系推断）
输出:      demo/catalog/index.html + cat-cbdb.html + cat-chgis.html + cat-harv.html
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import descs

GEN = '2026-09-27'
cat = json.load(open('/tmp/xrg_demo/catalog.json', encoding='utf-8'))
assert len(cat) == 399, f'表数应为 399，实为 {len(cat)}'
TOT_ROWS = sum(v['rows'] or 0 for v in cat.values())
assert TOT_ROWS == 8580233, f'行数合计应为 8,580,233，实为 {TOT_ROWS:,}'
assert all(v['rows'] is not None for v in cat.values()), '存在缺统计的表'

pubset = set(v['tb'] for v in cat.values() if v['sc'] == 'public')

def rec_of(v):
    sc, tb = v['sc'], v['tb']
    desc, lv = descs.DESCFN[sc](tb)
    cols, geon = [], 0
    for c in v['cols']:
        r = {'n': c['n'], 'dt': c['dt'], 'u': c['udt'], 'nn': c.get('nn', 0)}
        if 'd' in c: r['d'] = c['d']
        if 'mn' in c: r['mn'] = str(c['mn']); r['mx'] = str(c['mx'])
        if 'm' in c: r['m'] = c['m']
        if 'geo' in c: r['geo'] = c['geo']
        if c['udt'] == 'geometry': geon += 1
        cols.append(r)
    rec = {'tb': tb, 'desc': desc, 'lv': lv, 'fam': descs.FAMFN[sc](tb),
           'rows': v['rows'] or 0, 'ncols': len(cols), 'geon': geon,
           'cols': cols, 'sample': v['sample'] or []}
    if sc == 'public':
        rel, seen = [], set()
        for c in cols:
            t = descs.REL.get(c['n'])
            if t and t in pubset and t != tb and (c['n'], t) not in seen:
                seen.add((c['n'], t)); rel.append([c['n'], t])
        rec['rel'] = rel
    return rec

def fam_agg(tables):
    agg = {}
    for r in tables:
        f = agg.setdefault(r['fam'], [0, 0]); f[0] += 1; f[1] += r['rows']
    return [{'f': k, 't': v[0], 'r': v[1]} for k, v in sorted(agg.items(), key=lambda x: -x[1][1])]

tpl = open(os.path.join(HERE, 'catalog-template.html'), encoding='utf-8').read()
app = open(os.path.join(HERE, 'app_catalog.js'), encoding='utf-8').read()

def js(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')

PAGES = [
 ('cat-cbdb.html', ('public', 'ogr_system_tables'), 'CBDB 人物库', 'CBDB 人物库 <em>全目</em>',
  'public schema · 86 张 CBDB 表 ＋ 4 张 PostGIS 系统视图（另附 ogr 元数据表 1 张）。中国历代人物传记库（Harvard）：66 万人物的地址、亲属、社交、除授、入仕、别名、文献出处——星型结构，一切事实表围绕 <code>biog_main</code>。'),
 ('cat-chgis.html', ('chgis',), 'CHGIS 历史地理', 'CHGIS 历史地理 <em>全目</em>',
  'chgis schema · 211 张表。V2–V6 历代政区点面全套（1820/1911 基准＋时序层）、Hartwell 四朝代快照（741/1080/1200/1391）、~1km DEM 高程、明代驿站驿路卫所、中国年代学总表。「宋人分布图」的底图与「庐山地形」的高程都出自这里。'),
 ('cat-harv.html', ('harv',), 'TGaz 辞典与历史地图', 'TGaz 辞典与历史地图 <em>全目</em>',
  'harv schema · 97 张表。TGaz 中国历史地名辞典（82,117 地名 × 245,042 历史拼写 × 隶属/今地/ID 桥）、俄国地理学会图集与普尔热瓦尔斯基等探险地图、茶马古道、TBRC 藏传佛教寺院、谭其骧图集 GBK 名表、2016 高铁与 2013 天然气管道、DCW 海岸线。'),
]

built = []
for fn, scs, title, h1, sub in PAGES:
    tables = [rec_of(v) for v in cat.values() if v['sc'] in scs]
    tables.sort(key=lambda r: -r['rows'])
    fams = fam_agg(tables)
    data = {'tables': tables, 'fams': fams}
    srows = sum(r['rows'] for r in tables)
    scols = sum(r['ncols'] for r in tables)
    sgeo = sum(r['geon'] for r in tables)
    cfg = {'title': title, 'h1': h1, 'sub': sub, 'gen': GEN,
           'stats': [[len(tables), '表'], [srows, '总行数（count 实测）'],
                     [scols, '总列数'], [sgeo, '几何列（空间）']]}
    out = tpl.replace('__TITLE__', title)
    out = out.replace('__DATA__', js(data)).replace('__CFG__', js(cfg)).replace('/*__APP__*/', app)
    for ph in ('__TITLE__', '__DATA__', '__CFG__', '__APP__'):
        assert ph not in out, f'{fn} 占位残留 {ph}'
    p = os.path.join(HERE, fn)
    open(p, 'w', encoding='utf-8').write(out)
    built.append((fn, len(tables), srows))
    print(f'{fn}: {len(tables)} 表 · {srows:,} 行 · {scols} 列 · {sgeo} 几何列 · {os.path.getsize(p):,}B')

# ---------- index ----------
def schema_card(sc_list, sc_label, href, t, d, col):
    tables = [rec_of(v) for v in cat.values() if v['sc'] in sc_list]
    fams = fam_agg(tables)
    reps = [[r['tb'], r['rows'], r['desc']] for r in sorted(tables, key=lambda x: -x['rows'])[:6]]
    return {'sc': sc_label, 'href': href, 'title': t, 'd': d, 'col': col,
            'tables': len(tables), 'rows': sum(r['rows'] for r in tables),
            'cols': sum(r['ncols'] for r in tables),
            'fams': [[f['f'], f['t'], f['r']] for f in fams[:5]], 'reps': reps}

idx_data = {
 'gen': GEN,
 'stats': [[len(cat), '张表（含 4 张 PostGIS 视图）'], [TOT_ROWS, '总行数（count(*) 实测）'],
           [sum(len(v['cols']) for v in cat.values()), '总列数'], [4, 'schema · 三座数据库']],
 'schemas': [
   schema_card(('public', 'ogr_system_tables'), 'public + ogr', 'cat-cbdb.html', 'CBDB 人物库',
     '66 万历史人物传记及其地址、亲属、社交、除授、入仕、别名、文献出处（125 万条引用）。星型结构，一切围绕 biog_main。', '#d4a24e'),
   schema_card(('chgis',), 'chgis', 'cat-chgis.html', 'CHGIS 历史地理',
     'V2–V6 历代政区点面全套、Hartwell 四朝代快照、~1km DEM 高程、明代驿站驿路、中国年代学总表。', '#6fb3a0'),
   schema_card(('harv',), 'harv', 'cat-harv.html', 'TGaz 辞典与历史地图',
     'TGaz 历史地名辞典（82,117 地名 × 245,042 拼写）、俄国探险地图、茶马古道、藏传佛教寺院、高铁与气管道、谭图 GBK 名表。', '#9b7fb8'),
 ],
 'demos': [
   {'href': '../pg32b-roam.html', 'k': '全库导览', 'title': 'pg32b 数据漫游',
    'd': '八章导览：时代分布 / 完整度 / 关系类型 / 籍贯地图 / 网络中心 / 苏轼拆行 / 地理半壁 / 全表目录。范本 cbdb-demo 同构重制。'},
   {'href': '../A-song-distribution.html', 'k': '专题演示 A', 'title': '宋人分布图 v1',
    'd': 'Hartwell 1080 府级面 × 5.6 万籍贯点染色，附五行校勘台（v6 缺面 / 務州讹字 / 福州离群行实证）。'},
   {'href': '../person/index.html', 'k': '人物专题', 'title': '蘇軾 · 一个人的一生',
    'd': '以一人为主线三页联动：全景档案（身份/亲缘/著作/出处）· 1,033 条社交力导向图（34 位身后追慕者单列紫色）· 行迹地图＋DEM 贬谪路剖面。personid 参数化，换人可重跑。'},
 ],
}
itpl = open(os.path.join(HERE, 'index-template.html'), encoding='utf-8').read()
iapp = open(os.path.join(HERE, 'app_index.js'), encoding='utf-8').read()
out = itpl.replace('__DATA__', js(idx_data)).replace('/*__APP__*/', iapp)
assert '__DATA__' not in out and '__APP__' not in out
p = os.path.join(HERE, 'index.html')
open(p, 'w', encoding='utf-8').write(out)
print(f'index.html: {os.path.getsize(p):,}B')

for f in os.listdir(HERE):
    if f.endswith(('.html', '.js', '.py')):
        os.chmod(os.path.join(HERE, f), 0o644)
print('完成:', [b[0] for b in built], '+ index.html')

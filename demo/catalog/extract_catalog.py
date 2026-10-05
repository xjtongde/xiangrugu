#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pg32b 数据总目 · 抽数引擎（395 表 × 7,128 列全量画像）

四阶段（每阶段一条 ssh 会话，SQL 走 stdin 直达 psql，无 shell 引号层）：
  M 元数据   information_schema.columns 全量
  A 全表统计 每表精确行数 + 每列非空数 + 数值/时间列 min/max + 3 行样例（文本化截断）
  B 逐列去重 count(DISTINCT col)，18 列一批（几何/json/bytea/数组除外，非空=0 跳过）
  C 高频值   distinct≤25 的类别列取 Top3 值；几何列取 GeometryType×SRID 画像

产物: /tmp/xrg_demo/cat_meta.json / cat_A.json / cat_B.json / cat_C.json / catalog.json
用法: python3 extract_catalog.py   （预计 15–30 分钟，后台跑）
"""
import json, subprocess, re, sys, time

OUT = '/tmp/xrg_demo'
SSH = ['ssh', '-i', '/root/.ssh/id_rsa/32/32', '-o', 'ConnectTimeout=8',
       '-o', 'ServerAliveInterval=30', 'root@192.168.3.32']
RPSQL = 'docker exec -i pg32b psql -U postgres -d cbdb -At'
NUMDT = {'smallint','integer','bigint','numeric','real','double precision','oid'}
TIMEDT = ('timestamp','date','time')
SKIP_DIST_DT = {'json','jsonb','xml','bytea','ARRAY'}

def run_sql(sql, tag, timeout=5400):
    t0 = time.time()
    p = subprocess.run(SSH + [RPSQL], input=sql.encode(), capture_output=True, timeout=timeout)
    err = p.stderr.decode(errors='replace')
    out = p.stdout.decode()
    if p.returncode != 0:
        print(f'[{tag}] rc={p.returncode} stderr头: {err[:400]}', flush=True)
    elif err.strip():
        n_err = err.count('ERROR')
        if n_err: print(f'[{tag}] {n_err} 条 ERROR（首条）: {err.splitlines()[0][:200]}', flush=True)
    print(f'[{tag}] {time.time()-t0:.0f}s 输出{len(out)//1024}KB', flush=True)
    return out

def qi(i): return '"' + i.replace('"', '""') + '"'
def qt(sc, tb): return qi(sc) + '.' + qi(tb)
def ql(s): return "'" + s.replace("'", "''") + "'"

def parse_marked(out):
    """按 @X@key[@i] 标记行切分输出，返回 {key(+i): body}"""
    res, cur, buf = {}, None, []
    for line in out.splitlines():
        m = re.match(r'^@([MABC])@(\S+)$', line)
        if m:
            if cur: res[cur] = '\n'.join(buf).strip()
            cur, buf = m.group(1) + '@' + m.group(2), []
        elif cur is not None:
            buf.append(line)
    if cur: res[cur] = '\n'.join(buf).strip()
    return res

def jload(body):
    if not body or body.startswith(('ERROR','psql:')): return None
    try: return json.loads(body.splitlines()[0])
    except Exception: return None

# ---------- M: 元数据 ----------
print('== 阶段 M：元数据 ==', flush=True)
meta_out = run_sql(r"""
\echo @M@meta
SELECT json_agg(row_to_json(x)) FROM (
  SELECT table_schema sc, table_name tb, column_name col, data_type dt, udt_name udt,
         ordinal_position pos
  FROM information_schema.columns
  WHERE table_schema IN ('public','chgis','harv','ogr_system_tables')
  ORDER BY table_schema, table_name, ordinal_position) x;
""", 'M')
meta = jload(parse_marked(meta_out).get('M@meta'))
assert meta and len(meta) > 7000, f'元数据异常: {len(meta) if meta else 0}'
json.dump(meta, open(OUT+'/cat_meta.json','w'), ensure_ascii=False)

tables = {}
for r in meta:
    tables.setdefault((r['sc'], r['tb']), []).append(r)
for k in tables: tables[k].sort(key=lambda c: c['pos'])
print(f'{len(meta)} 列 / {len(tables)} 表', flush=True)

def is_geo(c): return c['udt'] == 'geometry'
def is_num(c): return c['dt'] in NUMDT or c['dt'].startswith(TIMEDT)
def dist_ok(c):
    return (not is_geo(c) and c['dt'] not in SKIP_DIST_DT
            and not (c['dt'] == 'USER-DEFINED' and not is_geo(c)))

# ---------- A: 全表统计 + 样例 ----------
print('== 阶段 A：全表统计 ==', flush=True)
sql = ['\\echo @A@start']
keys = sorted(tables.keys())
for sc, tb in keys:
    cols = tables[(sc, tb)]
    aggs = ['count(*) AS "rows"']
    for c in cols:
        aggs.append(f'count({qi(c["col"])}) AS {qi("nn__"+c["col"])}')
    for c in cols:
        if is_num(c):
            aggs.append(f'min({qi(c["col"])}) AS {qi("mn__"+c["col"])}')
            aggs.append(f'max({qi(c["col"])}) AS {qi("mx__"+c["col"])}')
    sql.append(f'\\echo @A@{sc}.{tb}')
    sql.append(f'SELECT row_to_json(_q) FROM (SELECT {", ".join(aggs)} FROM {qt(sc,tb)}) _q;')
    sel = []
    for c in cols:
        if is_geo(c):
            expr = f'left(regexp_replace(ST_AsText({qi(c["col"])}), E\'[\\n\\r\\t]+\',\' \',\'g\'),70)'
        else:
            expr = f'left(regexp_replace({qi(c["col"])}::text, E\'[\\n\\r\\t]+\',\' \',\'g\'),70)'
        sel.append(expr + ' AS ' + qi(c['col']))
    sql.append(f'SELECT json_agg(row_to_json(_q)) FROM (SELECT {", ".join(sel)} FROM {qt(sc,tb)} LIMIT 3) _q;')
outA = run_sql('\n'.join(sql) + '\n', 'A')
A = {}
resA = parse_marked(outA)
for sc, tb in keys:
    body = resA.get(f'A@{sc}.{tb}', '')
    lines = [l for l in body.splitlines() if l.strip()]
    stat = jload(lines[0]) if lines else None
    samp = jload(lines[1]) if len(lines) > 1 else None
    A[f'{sc}.{tb}'] = {'stat': stat, 'sample': samp or []}
    if stat is None: print(f'  [A失败] {sc}.{tb}', flush=True)
json.dump(A, open(OUT+'/cat_A.json','w'), ensure_ascii=False)
n_ok = sum(1 for v in A.values() if v['stat'])
print(f'A 完成: {n_ok}/{len(keys)}', flush=True)

# ---------- B: 逐列去重 ----------
print('== 阶段 B：逐列 distinct ==', flush=True)
sql = ['\\echo @B@start']
bplan = []   # (key, chunk_idx, cols)
for sc, tb in keys:
    st = A[f'{sc}.{tb}']['stat']
    if not st: continue
    elig = [c for c in tables[(sc, tb)]
            if dist_ok(c) and st.get('nn__'+c['col'], 0) > 0]
    for i in range(0, len(elig), 18):
        ch = elig[i:i+18]
        bplan.append((f'{sc}.{tb}', i//18, ch))
        aggs = ', '.join(f'count(DISTINCT {qi(c["col"])}) AS {qi(c["col"])}' for c in ch)
        sql.append(f'\\echo @B@{sc}.{tb}@{i//18}')
        sql.append(f'SELECT row_to_json(_q) FROM (SELECT {aggs} FROM {qt(sc,tb)}) _q;')
print(f'B 计划: {len(bplan)} 批', flush=True)
outB = run_sql('\n'.join(sql) + '\n', 'B', timeout=7200)
B = {}
resB = parse_marked(outB)
for key, ci, ch in bplan:
    d = jload(resB.get(f'B@{key}@{ci}', '')) or {}
    B.setdefault(key, {}).update(d)
json.dump(B, open(OUT+'/cat_B.json','w'), ensure_ascii=False)
print(f'B 完成: {sum(len(v) for v in B.values())} 列', flush=True)

# ---------- C: 类别列高频值 + 几何画像 ----------
print('== 阶段 C：高频值/几何 ==', flush=True)
sql = ['\\echo @C@start']
cplan = []
for sc, tb in keys:
    key = f'{sc}.{tb}'
    st = A[key]['stat']
    if not st: continue
    rows = st['rows']
    picks = []   # (col, kind)
    for c in tables[(sc, tb)]:
        cn = c['col']
        if is_geo(c) and st.get('nn__'+cn, 0) > 0:
            picks.append((cn, 'geo'))
        else:
            dd = B.get(key, {}).get(cn)
            nn = st.get('nn__'+cn, 0)
            if dd is not None and 0 < dd <= 25 and dd < rows and nn > 0:
                picks.append((cn, 'cat'))
    for i in range(0, len(picks), 25):
        ch = picks[i:i+25]
        cplan.append((key, i//25, [c for c, _ in ch]))
        parts = []
        for cn, kind in ch:
            if kind == 'geo':
                parts.append(f'{ql(cn)},(SELECT json_agg(row_to_json(s)) FROM (SELECT GeometryType({qi(cn)}) AS v, count(*) AS c, min(ST_SRID({qi(cn)})) AS srid FROM {qt(sc,tb)} GROUP BY 1 ORDER BY c DESC LIMIT 4) s)')
            else:
                parts.append(f'{ql(cn)},(SELECT json_agg(row_to_json(s)) FROM (SELECT left(regexp_replace({qi(cn)}::text, E\'[\\n\\r\\t]+\',\' \',\'g\'),30) AS v, count(*) AS c FROM {qt(sc,tb)} WHERE {qi(cn)} IS NOT NULL GROUP BY 1 ORDER BY c DESC LIMIT 3) s)')
        sql.append(f'\\echo @C@{key}@{i//25}')
        sql.append(f'SELECT json_build_object({", ".join(parts)}) FROM (SELECT 1) z;')
print(f'C 计划: {len(cplan)} 批', flush=True)
outC = run_sql('\n'.join(sql) + '\n', 'C', timeout=7200) if cplan else ''
C = {}
resC = parse_marked(outC)
for key, ci, colnames in cplan:
    d = jload(resC.get(f'C@{key}@{ci}', '')) or {}
    C.setdefault(key, {}).update(d)
json.dump(C, open(OUT+'/cat_C.json','w'), ensure_ascii=False)
print(f'C 完成: {sum(len(v) for v in C.values())} 列', flush=True)

# ---------- 汇总 catalog.json ----------
cat = {}
for sc, tb in keys:
    key = f'{sc}.{tb}'
    st = A[key]['stat']
    cols = []
    for c in tables[(sc, tb)]:
        cn = c['col']
        rec = {'n': cn, 'dt': c['dt'], 'udt': c['udt']}
        if st:
            rec['nn'] = st.get('nn__'+cn, 0)
            if 'mn__'+cn in st: rec['mn'] = st['mn__'+cn]; rec['mx'] = st['mx__'+cn]
        dd = B.get(key, {}).get(cn)
        if dd is not None: rec['d'] = dd
        mm = C.get(key, {}).get(cn)
        if mm:
            if is_geo(c): rec['geo'] = mm
            else: rec['m'] = [[x['v'], x['c']] for x in mm]
        cols.append(rec)
    cat[key] = {'sc': sc, 'tb': tb,
                'rows': st['rows'] if st else None,
                'cols': cols, 'sample': A[key]['sample']}
json.dump(cat, open(OUT+'/catalog.json','w'), ensure_ascii=False)
tot = sum(v['rows'] or 0 for v in cat.values())
n_missing = sum(1 for v in cat.values() if v['rows'] is None)
print(f'== catalog.json 完成: {len(cat)} 表 · 精确行数合计 {tot:,} · 缺统计 {n_missing} ==', flush=True)

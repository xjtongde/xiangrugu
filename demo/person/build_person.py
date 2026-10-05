# -*- coding: utf-8 -*-
"""人物专题 · 构建器（以一人为主线的一套页面）

输入(只读): /tmp/xrg_demo/person_{pid}.json —— extract_person.py 实测产物
            /tmp/xrg_demo/A2.json —— Hartwell 1080 府级面底图（303 面）
输出:      demo/person/index.html + network.html + journey.html（自包含单文件，离线可看）
换人重跑: python3 extract_person.py <personid> && 改下方 PID/NAME 即可。
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PID = 3767
GEN = '2026-09-27'

d = json.load(open(f'/tmp/xrg_demo/person_{PID}.json', encoding='utf-8'))
A2 = json.load(open('/tmp/xrg_demo/A2.json', encoding='utf-8'))
assert len(A2) == 303, f'底图面数应为 303，实为 {len(A2)}'
C = d['counts']
assert C['assoc'] == 1033 and C['post'] == 35 and C['addr'] == 31 and C['kin'] == 27 \
    and C['kin_rev'] == 27 and C['text'] == 40 and C['source'] == 9, f'counts 异常: {C}'
assert len(d['assoc']) == 1033 and len(d['post']) == 35 and len(d['kin']) == 27
assert len(d['dem_legs']) == 4 and all(len(l['pts']) == 101 for l in d['dem_legs']), 'DEM 剖面应 4 段×101 点'
DEATH = d['main']['d']

dated = [a for a in d['assoc'] if a.get('y1') and a['y1'] > 0]   # -1 为 CBDB「未详」占位，不计
posth = [a for a in dated if a['y1'] > DEATH]
uniq = len(set(a['pid'] for a in d['assoc'] if a.get('pid') is not None))
wmap = {}
for a in d['assoc']:
    if a.get('pid') is not None:
        wmap[a['pid']] = wmap.get(a['pid'], 0) + 1
heavy = sum(1 for w in wmap.values() if w >= 5)
PB = {x['pid']: x.get('b') for x in (d.get('pbirth') or []) if x.get('b')}
assert PB, 'pbirth 为空——伙伴生年未抽取'
posth_pids = {pid for pid, b in PB.items() if b > DEATH}
posthP = len(posth_pids)
posthRecs = sum(1 for a in d['assoc'] if a.get('pid') in posth_pids)
stops = sum(1 for p in d['post'] if p.get('fy') is not None
            and any(q and q.get('x') is not None for q in (p.get('pxy') or [])))
addr_xy = sum(1 for a in d['addr'] if a.get('x') is not None)

def js(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')

posts_idx = [{k: v for k, v in p.items() if k != 'pxy'} for p in d['post']]

PAGES = [
 ('index-template.html', 'app_person_index.js', 'index.html',
  {k: d[k] for k in ('pid', 'main', 'alt', 'entry', 'kin', 'kin2', 'addr', 'works', 'src', 'status', 'counts')}
  | {'post': posts_idx},
  {'gen': GEN, 'stats': [[C['assoc'], '社交记录'], [uniq, '唯一伙伴'], [C['kin'] + C['kin_rev'], '亲缘（双向）'],
                          [C['addr'], '地址记录'], [C['post'], '除授段数'], [C['text'], '著作关联'],
                          [C['source'], '文献出处'], [C['status'], '身份标签']]}),
 ('network-template.html', 'app_person_network.js', 'network.html',
  {'main': {'id': d['main']['id'], 'nm': d['main']['nm'], 'd': DEATH}, 'assoc': d['assoc'], 'pbirth': d['pbirth']},
  {'gen': GEN, 'stats': [[len(d['assoc']), '交往记录'], [uniq, '唯一伙伴'], [len(dated), '真实系年（皆生前）'],
                          [posthP, f'身后生伙伴（＞{DEATH}）'], [posthRecs, '身后伙伴的记录'], [heavy, '多条记录伙伴(≥5)']]}),
 ('journey-template.html', 'app_person_journey.js', 'journey.html',
  {'main': {'id': d['main']['id'], 'nm': d['main']['nm'], 'b': d['main']['b'], 'd': DEATH},
   'post': d['post'], 'addr': d['addr'], 'dem_legs': d['dem_legs'], 'base': A2},
  {'gen': GEN, 'stats': [[len(d['post']), '除授段数'], [stops, '可落图任所'], [len(d['addr']), '地址记录'],
                          [addr_xy, '地址有坐标'], [len(d['dem_legs']), 'DEM 剖面段'],
                          [sum(len(l['pts']) for l in d['dem_legs']), '剖面采样点']]}),
]

for tpl_f, app_f, out_f, data, cfg in PAGES:
    tpl = open(os.path.join(HERE, tpl_f), encoding='utf-8').read()
    app = open(os.path.join(HERE, app_f), encoding='utf-8').read()
    out = tpl.replace('__DATA__', js(data)).replace('__CFG__', js(cfg)).replace('/*__APP__*/', app)
    for ph in ('__DATA__', '__CFG__', '__APP__'):
        assert ph not in out, f'{out_f} 占位残留 {ph}'
    p = os.path.join(HERE, out_f)
    open(p, 'w', encoding='utf-8').write(out)
    os.chmod(p, 0o644)
    print(f'{out_f}: {os.path.getsize(p):,}B')

for f in os.listdir(HERE):
    if f.endswith(('.html', '.js', '.py')):
        os.chmod(os.path.join(HERE, f), 0o644)
print(f'完成：蘇軾({PID}) 三页 · 社交{len(d["assoc"])} 伙伴{uniq} · 身后生伙伴{posthP}人/{posthRecs}条 · 可落图任所{stops} · 地址有坐标{addr_xy}')

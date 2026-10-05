# -*- coding: utf-8 -*-
"""pg32b 数据漫游 生成器（范本：/root/homelan/cbdb-demo 的 template+app+build 构建模式）

输入(只读):
  /tmp/xrg_demo/roam_data.json —— 21 个聚合查询结果（2026-09-27 抽自 pg32b @192.168.3.32 cbdb 库）
  demo/roam-template.html + demo/app_roam.js
输出:
  demo/pg32b-roam.html（自包含单文件，离线可看）
"""
import json, os

D = os.path.dirname(os.path.abspath(__file__))
d = json.load(open('/tmp/xrg_demo/roam_data.json', encoding='utf-8'))
d.pop('entry_cols', None)   # 侦察用输出，不进页面

# —— 口径断言（与 pg32b 实测基线核对）——
assert len(d['tables']) == 395, '表数应为 395'
assert sum(t['rows'] for t in d['tables']) == 8580012, '行数合计应为 8,580,012（健康基线）'
assert d['cov']['t'] == 661969 and d['cov']['f'] == 58344, 'biog_main/女性数与范本快照不符'
assert len(d['places']) == 40 and len(d['toplink']) == 20
assert d['su_main']['nm'] == '蘇軾' and d['su_assoc_tot'] == 1033
assert len(d['gis']) == 13 and all(-600 <= r['y'] <= 1915 for r in d['years'])

tpl = open(os.path.join(D, 'roam-template.html'), encoding='utf-8').read()
app = open(os.path.join(D, 'app_roam.js'), encoding='utf-8').read()
out = tpl.replace('__DATA__', json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c'))
out = out.replace('/*__APP__*/', app)
assert '__DATA__' not in out and '__APP__' not in out, '占位残留'

dst = os.path.join(D, 'pg32b-roam.html')
open(dst, 'w', encoding='utf-8').write(out)
for f in ('pg32b-roam.html', 'roam-template.html', 'app_roam.js'):
    os.chmod(os.path.join(D, f), 0o644)
os.chmod(__file__, 0o644)
print(f"输出 {dst} {os.path.getsize(dst):,} bytes · tables={len(d['tables'])} places={len(d['places'])} gis={len(d['gis'])}")

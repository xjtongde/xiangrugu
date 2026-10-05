# -*- coding: utf-8 -*-
"""宋人分布图 v1 生成器（范本：/root/homelan/cbdb-demo 的 template+build 构建模式）

输入(只读): /tmp/xrg_demo/A2.json —— Hartwell 1080 府级面 × CBDB 宋人籍贯
            （2026-09-27 抽自 pg32b @192.168.3.32 cbdb 库，重跑管线见会话记录）
输出:      /root/xiangrugu/demo/A-song-distribution.html（自包含单文件，离线可看）

KPI/校勘数字全部为本次会话 pg32b 直查实测值，来源注于行内。
"""
import json, os

SRC = '/tmp/xrg_demo/A2.json'
DEMO = '/root/xiangrugu/demo'

A = json.load(open(SRC, encoding='utf-8'))
assert len(A) == 303, f'面数应为 303，实为 {len(A)}'

# 校勘②：hartwell_pref_pgn S005500002400「務州」为「婺州」形近讹字
#   证据：该面落图 1,772 人与 CHGIS v6 面层「婺州」完全一致；v6 点层有婺州(119.650,29.105)=金华；宋代无「務州」
#   处理：仅改显示名，不改数据库
FIX = {'務州': '婺州'}
fixed = 0
for d in A:
    if d['n'] in FIX:
        d['n'] = FIX[d['n']]
        fixed += 1
assert fixed == 1, f'婺州讹字修正应命中 1 处，实为 {fixed}'

face_sum = sum(d.get('c') or 0 for d in A)

KPI = {
    # —— 漏斗（pg32b 实测 2026-09-27）——
    'song_total': 83373,      # biog_main c_dy=15（dynasties: 宋 960–1279）
    'has_idx':    56556,      # 其中 c_index_addr_id>0
    'has_coord':  56135,      # 索引地址在 addr_codes 有 x_coord
    'placed':     55985,      # ST_Within 落入 Hartwell 1080 面（去重）
    'dropouts':   150,        # 有坐标但未落面
    'addr_total': 30157, 'addr_coord': 15555,   # addr_codes 坐标覆盖率 51.6%
    'snap': 1080, 'snap_label': '元豐三年', 'gen': '2026-09-27',
    # —— 底图对比（校勘①）——
    'v6_prefs_1100': 161, 'v6_pts_1100': 355, 'v6_dropouts': 11119, 'recovered': 10969,
    # —— 落图外 Top12（NOT EXISTS 实查）——
    'dropout_top': [['泰州海岸海水',43],['范陽',15],['薊州',8],['新城',8],['五原',6],['盧龍',5],
                    ['會同',4],['涿州',4],['成州',4],['幽州',4],['大興',3],['靖州',3]],
    # —— 校勘台五行（ev/act 允许内嵌 HTML）——
    'finds': [
        {'t': 'CHGIS v6 府级面层宋代缺面', 'cls': 'bad', 'jd': '图层覆盖缺口',
         'ev': '1100 年生效面仅 <b>161</b> 个（同年点层有 355 个，含開封府 938–1233）；開封府/河南府面 <b>1368 年起</b>才有、成都府 1371、眉州 1380——中原与四川宋代缺面。用 v6 底图时 11,119 人籍贯落图外（開封 2,004、洛陽 634、四川诸地约 1,700）。',
         'act': '底图换 <code>hartwell_pref_pgn</code>（yr=1080，303 面，含開封府/成都府/眉州）；落图外降至 150 人，找回 10,969 人。'},
        {'t': 'Hartwell 层「務州」疑讹字', 'cls': 'warn', 'jd': '形近讹写',
         'ev': 'code S005500002400（Zhou）；该面落图 <b>1,772 人</b>与 v6 面层「婺州」人数完全一致；v6 点层婺州 (119.650, 29.105)＝金华。宋无「務州」，婺/務形近。',
         'act': '构建时仅改显示名为「婺州」（本脚本 FIX 表），原始数据不动。'},
        {'t': 'CBDB「福州」坐标离群行', 'cls': 'warn', 'jd': '坐标离群',
         'ev': 'addr_codes 一行坐标 (122.580, <b>42.717</b>)；CHGIS 点层与 CBDB 另一行均为 (119.322, 26.074)，Δ≈<b>16.97°</b>，疑纬度错置。',
         'act': '实测 0 人籍贯指向该行，本页零损害；公示为「按地名 join」者的地雷。'},
        {'t': '籍贯「泰州海岸海水」', 'cls': 'ok', 'jd': '史料照录',
         'ev': '43 人籍贯原文即此，坐标落台州海面，不 within 任何府面。',
         'act': '不落图、不修改，计入落图外 150 人并如实展示。'},
        {'t': '同名两地「華陽」', 'cls': 'ok', 'jd': '同名歧义',
         'ev': 'addr_codes 同名两套坐标：成都附郭 (104.078, 30.650) 与洛阳一带 (113.753, 34.567)。',
         'act': '本页按 <code>c_addr_id</code> 联结而非地名，天然免疫。'},
    ],
}
assert KPI['placed'] + KPI['dropouts'] == KPI['has_coord'], '漏斗口径不闭合'
assert face_sum >= KPI['placed'], '面合计不应小于去重数'

tpl = open(os.path.join(DEMO, 'A-template.html'), encoding='utf-8').read()
out = tpl.replace('__DATA__', json.dumps(A, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c'))
out = out.replace('__KPI__', json.dumps(KPI, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c'))
assert '__DATA__' not in out and '__KPI__' not in out, '占位残留'

dst = os.path.join(DEMO, 'A-song-distribution.html')
open(dst, 'w', encoding='utf-8').write(out)
os.chmod(dst, 0o644)
os.chmod(os.path.join(DEMO, 'A-template.html'), 0o644)
os.chmod(__file__, 0o644)
print(f'面数={len(A)} 人次合计={face_sum} 重叠双计={face_sum - KPI["placed"]} 讹字修正={fixed}')
print(f'输出 {dst} {os.path.getsize(dst):,} bytes')

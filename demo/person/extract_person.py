# -*- coding: utf-8 -*-
"""人物专题 · 抽数引擎（以一人为主线，抽全其方方面面）

用法: python3 extract_person.py [personid]   （默认 3767 = 蘇軾）
产物: /tmp/xrg_demo/person_{id}.json
两段式: ① 事实表全量（本体/别名/入仕/亲缘双向/社交1033/地址/除授/著作/出处/身份/事件）
        ② 驿路 waypoints → 四段贬谪/出蜀路线的 DEM 高程剖面采样
SQL 经 stdin 直达 psql（无 shell 引号层）；列名全部经 catalog.json 实测核对。
"""
import json, subprocess, re, sys, time

PID = int(sys.argv[1]) if len(sys.argv) > 1 else 3767
OUT = f'/tmp/xrg_demo/person_{PID}.json'
SSH = ['ssh', '-i', '/root/.ssh/id_rsa/32/32', '-o', 'ConnectTimeout=8',
       '-o', 'ServerAliveInterval=30', 'root@192.168.3.32']
RPSQL = 'docker exec -i pg32b psql -U postgres -d cbdb -At'
P = str(PID)

def run_sql(sql, tag, timeout=900):
    t0 = time.time()
    p = subprocess.run(SSH + [RPSQL], input=sql.encode(), capture_output=True, timeout=timeout)
    err = p.stderr.decode(errors='replace')
    if err.strip():
        print(f'[{tag}] stderr: {err[:300]}', flush=True)
    print(f'[{tag}] {time.time()-t0:.0f}s', flush=True)
    return p.stdout.decode()

def parse_marked(out):
    res, cur, buf = {}, None, []
    for line in out.splitlines():
        m = re.match(r'^@(\w+)@$', line)
        if m:
            if cur: res[cur] = '\n'.join(buf).strip()
            cur, buf = m.group(1), []
        elif cur is not None:
            buf.append(line)
    if cur: res[cur] = '\n'.join(buf).strip()
    return res

def jl(body):
    if not body or body.startswith(('ERROR', 'psql:')):
        print('  !!', body[:200]); return None
    try: return json.loads(body.splitlines()[0])
    except Exception: return None

Q = {}
Q['counts'] = f"""SELECT json_build_object(
 'text',(SELECT count(*) FROM biog_text_data WHERE c_personid={P}),
 'events',(SELECT count(*) FROM events_data WHERE c_personid={P}),
 'status',(SELECT count(*) FROM status_data WHERE c_personid={P}),
 'inst',(SELECT count(*) FROM biog_inst_data WHERE c_personid={P}),
 'source',(SELECT count(*) FROM biog_source_data WHERE c_personid={P}),
 'possession',(SELECT count(*) FROM possession_data WHERE c_personid={P}),
 'alt',(SELECT count(*) FROM altname_data WHERE c_personid={P}),
 'assoc',(SELECT count(*) FROM assoc_data WHERE c_personid={P}),
 'kin',(SELECT count(*) FROM kin_data WHERE c_personid={P}),
 'kin_rev',(SELECT count(*) FROM kin_data WHERE c_kin_id={P}),
 'addr',(SELECT count(*) FROM biog_addr_data WHERE c_personid={P}),
 'post',(SELECT count(*) FROM posted_to_office_data WHERE c_personid={P}))"""

Q['main'] = f"""SELECT row_to_json(_q) FROM (
 SELECT b.c_personid id, b.c_name_chn nm, b.c_name pinyin, b.c_surname_chn sur, b.c_mingzi_chn mz,
        b.c_index_year iy, b.c_birthyear b, b.c_deathyear d, b.c_death_age age,
        b.c_fl_earliest_year fl1, b.c_fl_latest_year fl2,
        dy.c_dynasty_chn dyn, ch.c_choronym_chn chor, hh.c_household_status_desc_chn hh,
        iyt.c_index_year_type_hz iyt,
        ia.c_name_chn idx_addr, ia.x_coord idx_x, ia.y_coord idx_y,
        left(coalesce(b.c_notes,$$$$),800) notes
 FROM biog_main b
 LEFT JOIN dynasties dy ON dy.c_dy=b.c_dy
 LEFT JOIN choronym_codes ch ON ch.c_choronym_code=b.c_choronym_code
 LEFT JOIN household_status_codes hh ON hh.c_household_status_code=b.c_household_status_code
 LEFT JOIN indexyear_type_codes iyt ON iyt.c_index_year_type_code=b.c_index_year_type_code
 LEFT JOIN addr_codes ia ON ia.c_addr_id=b.c_index_addr_id
 WHERE b.c_personid={P}) _q"""

Q['alt'] = f"""SELECT json_agg(row_to_json(_q)) FROM (
 SELECT a.c_alt_name_chn n, a.c_alt_name py, ac.c_name_type_desc_chn ty, a.c_source src, a.c_pages pg
 FROM altname_data a LEFT JOIN altname_codes ac ON ac.c_name_type_code=a.c_alt_name_type_code
 WHERE a.c_personid={P} ORDER BY a.c_sequence) _q"""

Q['entry'] = f"""SELECT json_agg(row_to_json(_q)) FROM (
 SELECT ec.c_entry_desc_chn n, e.c_year y, e.c_entry_nh_year nh, e.c_exam_rank rk, e.c_age age,
        e.c_attempt_count att, e.c_sequence seq
 FROM entry_data e LEFT JOIN entry_codes ec ON ec.c_entry_code=e.c_entry_code
 WHERE e.c_personid={P} ORDER BY e.c_sequence) _q"""

KINSEL = """SELECT k.c_kinrel_chn rel, km.c_mourning_chn mourning, p.c_personid pid, p.c_name_chn n,
       p.c_birthyear b, p.c_deathyear d, dy.c_dynasty_chn dyn
 FROM kin_data kd JOIN kinship_codes k ON k.c_kincode=kd.c_kin_code
 JOIN biog_main p ON p.c_personid={WHO}
 LEFT JOIN dynasties dy ON dy.c_dy=p.c_dy
 LEFT JOIN kin_mourning km ON km.c_kinrel_chn=k.c_kinrel_chn
 WHERE kd.c_personid={P} ORDER BY k.c_kinrel_chn"""
Q['kin'] = f"SELECT json_agg(row_to_json(_q)) FROM ({KINSEL.replace('{WHO}','kd.c_kin_id').replace('{P}',P)})_q"
Q['kin2'] = f"SELECT json_agg(row_to_json(_q)) FROM ({KINSEL.replace('{WHO}','kd.c_personid').replace('{P}',P).replace('kd.c_personid='+P,'kd.c_kin_id='+P)})_q"

Q['assoc'] = f"""SELECT json_agg(row_to_json(_q)) FROM (
 SELECT a.c_assoc_id pid, p.c_name_chn n, ac.c_assoc_desc_chn rel,
        (SELECT at2.c_assoc_type_desc_chn FROM assoc_code_type_rel act
          JOIN assoc_types at2 ON at2.c_assoc_type_code=act.c_assoc_type_code
         WHERE act.c_assoc_code=a.c_assoc_code LIMIT 1) ty,
        a.c_assoc_first_year y1, a.c_assoc_last_year y2,
        ad.c_name_chn place, ad.x_coord px, ad.y_coord py,
        left(a.c_text_title,60) txt, oc.c_occasion_desc_chn occas,
        lg.c_lit_genre_desc_chn genre, kc.c_kinrel_chn via_kin
 FROM assoc_data a JOIN assoc_codes ac ON ac.c_assoc_code=a.c_assoc_code
 JOIN biog_main p ON p.c_personid=a.c_assoc_id
 LEFT JOIN addr_codes ad ON ad.c_addr_id=a.c_addr_id
 LEFT JOIN occasion_codes oc ON oc.c_occasion_code=a.c_occasion_code
 LEFT JOIN literarygenre_codes lg ON lg.c_lit_genre_code=a.c_litgenre_code
 LEFT JOIN kinship_codes kc ON kc.c_kincode=a.c_kin_code
 WHERE a.c_personid={P}) _q"""

Q['pbirth'] = f"""SELECT json_agg(row_to_json(_q)) FROM (
 SELECT c_personid pid, c_birthyear b, c_deathyear d
 FROM biog_main
 WHERE c_personid IN (SELECT DISTINCT c_assoc_id FROM assoc_data WHERE c_personid={P})) _q"""

Q['addr'] = f"""SELECT json_agg(row_to_json(_q)) FROM (
 SELECT bc.c_addr_desc_chn ty, ad.c_name_chn n, ad.x_coord x, ad.y_coord y,
        ba.c_firstyear y1, ba.c_lastyear y2, ba.c_natal natal
 FROM biog_addr_data ba LEFT JOIN biog_addr_codes bc ON bc.c_addr_type=ba.c_addr_type
 LEFT JOIN addr_codes ad ON ad.c_addr_id=ba.c_addr_id
 WHERE ba.c_personid={P} ORDER BY ba.c_addr_type) _q"""

Q['post'] = f"""SELECT json_agg(row_to_json(_q)) FROM (
 SELECT po.c_firstyear fy, po.c_lastyear ly, o.c_office_chn off, ap.c_appt_desc_chn appt,
        (SELECT string_agg(a.c_name_chn, $$、$$) FROM posted_to_addr_data pa
          JOIN addr_codes a ON a.c_addr_id=pa.c_addr_id WHERE pa.c_posting_id=po.c_posting_id) place,
        (SELECT json_agg(row_to_json(q)) FROM (SELECT a.c_name_chn n, a.x_coord x, a.y_coord y
          FROM posted_to_addr_data pa JOIN addr_codes a ON a.c_addr_id=pa.c_addr_id
          WHERE pa.c_posting_id=po.c_posting_id) q) pxy,
        left(po.c_notes,100) notes
 FROM posted_to_office_data po
 LEFT JOIN office_codes o ON o.c_office_id=po.c_office_id
 LEFT JOIN appointment_codes ap ON ap.c_appt_code=po.c_appt_code
 WHERE po.c_personid={P} ORDER BY po.c_firstyear NULLS FIRST) _q"""

Q['works'] = f"""SELECT json_agg(row_to_json(_q)) FROM (
 SELECT t.c_title_chn title, t.c_title tpy, tr.c_role_desc_chn role, bt.c_year y, t.c_text_year ty,
        tt.c_text_type_desc_chn type, ex.c_extant_desc_chn extant
 FROM biog_text_data bt JOIN text_codes t ON t.c_textid=bt.c_textid
 LEFT JOIN text_role_codes tr ON tr.c_role_id=bt.c_role_id
 LEFT JOIN text_type tt ON tt.c_text_type_code=t.c_text_type_id
 LEFT JOIN extant_codes ex ON ex.c_extant_code=t.c_extant
 WHERE bt.c_personid={P}) _q"""

Q['src'] = f"""SELECT json_agg(row_to_json(_q)) FROM (
 SELECT t.c_title_chn title, bs.c_pages pages, bs.c_main_source main, bs.c_self_bio selfb,
        left(bs.c_notes,120) notes
 FROM biog_source_data bs LEFT JOIN text_codes t ON t.c_textid=bs.c_textid
 WHERE bs.c_personid={P}) _q"""

Q['status'] = f"""SELECT json_agg(row_to_json(_q)) FROM (
 SELECT sc.c_status_desc_chn st, s.c_firstyear y1, s.c_lastyear y2, s.c_supplement sup
 FROM status_data s LEFT JOIN status_codes sc ON sc.c_status_code=s.c_status_code
 WHERE s.c_personid={P}) _q"""

Q['events'] = f"""SELECT json_agg(row_to_json(_q)) FROM (
 SELECT ec.c_event_name_chn ev, left(e.c_event,90) txt, e.c_year y, e.c_role role, ad.c_name_chn place
 FROM events_data e LEFT JOIN event_codes ec ON ec.c_event_code=e.c_event_code
 LEFT JOIN addr_codes ad ON ad.c_addr_id=e.c_addr_id
 WHERE e.c_personid={P}) _q"""

Q['wp'] = f"""SELECT json_agg(row_to_json(_q)) FROM (
 SELECT c_name_chn n, x_coord x, y_coord y, c_addr_id id FROM addr_codes
 WHERE c_name_chn IN ($$眉州$$,$$開封府$$,$$黃州$$,$$惠州$$,$$昌化$$,$$儋州$$,$$杭州$$,$$常州$$,
                      $$潁昌府$$,$$密州$$,$$徐州$$,$$湖州$$,$$汝州$$,$$登州$$,$$定州$$,$$鳳翔府$$,$$眉山县$$)
   AND x_coord IS NOT NULL) _q"""

Q['demsrid'] = "SELECT ST_SRID(rast) FROM chgis.dem LIMIT 1"

print(f'== 人物 {PID} · 阶段①事实表 ==', flush=True)
sql = ['\\echo @start@']
for k, q in Q.items():
    sql.append(f'\\echo @{k}@')
    sql.append(q + ';')
out = run_sql('\n'.join(sql) + '\n', '①')
res = parse_marked(out)
data = {'pid': PID}
for k in Q:
    data[k] = jl(res.get(k, ''))
    if data[k] is None and k not in ('status', 'events', 'demsrid'):
        print(f'  [{k}] 空/失败', flush=True)
print('counts:', data.get('counts'), flush=True)
print('demsrid:', data.get('demsrid'), flush=True)

# ---- 阶段②: DEM 高程剖面（四段路线，直线采样 101 点/段）----
wps = {}
for w in (data.get('wp') or []):
    wps.setdefault(w['n'], w)
print('waypoints:', sorted(wps.keys()), flush=True)
DAN = '昌化' if '昌化' in wps else '儋州'
LEGS = [('眉州', '開封府', '1057 · 初次出蜀赴京（嘉祐二年进士）'),
        ('開封府', '黃州', '1080 · 乌台诗案后责授黄州'),
        ('黃州', '惠州', '1094 · 绍圣元年再贬惠州'),
        ('惠州', DAN, f'1097 · 三贬{DAN}（渡琼州海峡）')]
legs_out = []
sql = []
for a, b, label in LEGS:
    if a not in wps or b not in wps:
        print(f'  缺 waypoint: {a}/{b}，跳过', flush=True)
        legs_out.append({'label': label, 'a': a, 'b': b, 'pts': []})
        continue
    x1, y1 = wps[a]['x'], wps[a]['y']
    x2, y2 = wps[b]['x'], wps[b]['y']
    sql.append(f'\\echo @dem_{a}_{b}@')
    sql.append(f"""SELECT json_agg(row_to_json(_q)) FROM (
 WITH leg AS (SELECT ST_SetSRID(ST_MakeLine(ST_MakePoint({x1},{y1}),ST_MakePoint({x2},{y2})),4326) g)
 SELECT round((i/100.0)::numeric,3)::float t,
        round(ST_X(ST_LineInterpolatePoint((SELECT g FROM leg), i/100.0))::numeric,4)::float lon,
        round(ST_Y(ST_LineInterpolatePoint((SELECT g FROM leg), i/100.0))::numeric,4)::float lat,
        (SELECT max(ST_Value(d.rast, ST_LineInterpolatePoint((SELECT g FROM leg), i/100.0)))::float
           FROM chgis.dem d
          WHERE ST_Intersects(d.rast, ST_LineInterpolatePoint((SELECT g FROM leg), i/100.0))) elev
 FROM generate_series(0,100) i) _q;""")
if sql:
    print('== 阶段② DEM 剖面 ==', flush=True)
    out2 = run_sql('\n'.join(sql) + '\n', '②', timeout=1200)
    res2 = parse_marked(out2)
    for a, b, label in LEGS:
        pts = jl(res2.get(f'dem_{a}_{b}', '')) or []
        got = sum(1 for p in pts if p.get('elev') is not None)
        mx = max([p['elev'] for p in pts if p.get('elev') is not None], default=None)
        print(f'  {a}→{b}: {len(pts)}点 有高程{got} 最高{mx}', flush=True)
        legs_out.append({'label': label, 'a': a, 'b': b, 'pts': pts})
data['dem_legs'] = legs_out
data['waypoints'] = wps

json.dump(data, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
import os
print(f'== 写出 {OUT} {os.path.getsize(OUT):,}B ==', flush=True)

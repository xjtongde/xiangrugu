/* pg32b 数据漫游 · 渲染逻辑（范本：/root/homelan/cbdb-demo/app.js 模式） */
const $=id=>document.getElementById(id);
const fmt=n=>(n??0).toLocaleString('en-US');
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const S=DATA;
const tip=$('tip');
document.addEventListener('mousemove',e=>{const t=e.target.closest&&e.target.closest('[data-tip]');
  if(t){tip.style.display='block';tip.innerHTML=t.getAttribute('data-tip');tip.style.left=Math.min(innerWidth-350,e.clientX+12)+'px';tip.style.top=(e.clientY+14)+'px';}
  else tip.style.display='none';});

/* ---------- 表说明（显式 + 规则回退） ---------- */
const DESC={
 biog_main:'人物主表（姓名·年代·籍贯·注记）',biog_source_data:'人物↔传记出处（文献·页码）',
 biog_addr_data:'人物↔地址（籍贯/寓居/死所…）',biog_addr_codes:'地址类型词表',
 biog_inst_data:'人物↔机构',altname_data:'别名记录（字/号/谥/法名…）',altname_codes:'别名类型词表',
 addr_codes:'历史地名主表（带经纬度 15,555）',entry_data:'入仕记录（科举/荐举/荫补…）',
 entry_codes:'入仕途径词表',office_codes:'官职名词表',office_type_codes:'官职类型词表',
 posted_to_office_data:'除授记录（人×官×起讫年）',posted_to_addr_data:'除授任地桥表',
 kin_data:'亲属关系记录（有向：A之父为B）',kinship_codes:'亲属类型词表',
 assoc_data:'社会交往记录（人×人×类型×年×地）',assoc_codes:'社会关系类型词表',
 status_data:'人物身份记录',status_codes:'身份词表',household_status_codes:'户状态词表',
 ethnicity_codes:'族群词表',dynasties:'朝代表（代码·中英文名·起讫）',
 text_codes:'文献主表（书名·作者·存佚）',institution_data:'机构主表',institution_codes:'机构类型词表',
 academies_2957:'历代书院 2,957 处（带坐标）',
 v6_pref_pgn:'CHGIS V6 时序府级面（beg/end 生效年）',v6_pref_pts:'V6 时序府级点（1100年生效355）',
 v6_cnty_pts:'V6 时序县级点（1100年1,252）',hartwell_pref_pgn:'Hartwell四快照(741/1080/1200/1391)府级面——「宋人分布图」底图',
 hartwell_cnty_pgn:'Hartwell 县级面',dem:'~1km高程栅格瓦片——「庐山地形」数据源',
 ming_stations_2016:'明代驿站 1,000 处',ming_routes_2016:'明代驿路',
 tgaz_placename:'TGaz 历史地名辞典·地名主表',tgaz_spelling:'TGaz 历史拼写/异体',
 tgaz_part_of:'TGaz 地名隶属关系',dcw_asia_contour:'DCW 亚洲海岸线底图',
 tan_tan_gbk_names1:'谭其骧图集 GBK 地名(1)',tan_tan_gbk_names2:'谭其骧图集 GBK 地名(2)',
 bgis_v1_1_2013:'BGIS 2013 佛教地志底表'};
function descOf(n){
  if(DESC[n])return DESC[n];
  if(/_codes?$/.test(n))return '词表 / 代码表';
  if(/_data$/.test(n))return '事实记录表';
  if(/^v[2-6]_/.test(n))return 'CHGIS 时序政区层';
  if(/^tgaz_/.test(n))return 'TGaz 地名辞典';
  if(/^tan_tan_/.test(n))return '谭图 GBK 地名';
  if(/^bgis/.test(n))return 'BGIS 佛教地志';
  if(/^dcw_/.test(n))return 'DCW 底图';
  if(/^hartwell_/.test(n))return 'Hartwell 政区复原';
  if(/^ming_/.test(n))return '明代地理';
  return '';
}

/* ---------- meta + KPI ---------- */
$('meta').innerHTML='数据版本 CBDB 20260919 · 与范本 SQLite 快照同版（女性 58,344 完全一致）· PostgreSQL 18.6 + PostGIS 3.6.4 · 生成于 2026-09-27 · 自包含离线可看 · <a href="A-song-distribution.html" style="color:var(--gold)">宋人分布图 v1 →</a>';
const allRows=S.tables.reduce((s,t)=>s+t.rows,0),allCols=S.tables.reduce((s,t)=>s+t.cols,0);
const tgaz=(S.gis.find(g=>g.n==='tgaz_placename')||{c:0}).c;
$('kpis').innerHTML=[
 [fmt(S.cov.t),'人物库人数（biog_main）'],
 [fmt(allRows),'全库行数（pg_stat 估计）'],
 [S.tables.length+' × '+fmt(allCols),'表 × 列 · 4 schema'],
 [fmt(S.tot.addrxy),'带坐标历史地名'],
 [fmt(S.tot.kin+S.tot.assoc),'亲属＋社会条目'],
 [(S.cov.f/S.cov.t*100).toFixed(1)+'%','女性占比（'+fmt(S.cov.f)+'人）'],
 [fmt(tgaz),'TGaz 历史地名'],
].map(([v,k])=>`<div class="kpi"><b>${v}</b><span>${k}</span></div>`).join('');

/* ---------- 直方图 / 横条图 ---------- */
function hist(el,rows){
  const W=520,H=250,L=46,B=24,T=10;
  const max=Math.max(...rows.map(r=>r.c))||1,bw=(W-L-8)/rows.length;
  let s=`<svg viewBox="0 0 ${W} ${H}" width="100%">`;
  for(let i=0;i<=3;i++){const v=max*i/3,y=T+(H-T-B)*(1-i/3);
    s+=`<line x1="${L}" y1="${y.toFixed(1)}" x2="${W-8}" y2="${y.toFixed(1)}" stroke="#2a3342" stroke-width=".6"/>`+
       `<text x="${L-5}" y="${(y+4).toFixed(1)}" font-size="9.5" fill="#8b94a3" text-anchor="end">${v>=10000?(v/10000).toFixed(1)+'万':Math.round(v)}</text>`;}
  rows.forEach((r,i)=>{const h=(H-T-B)*r.c/max,x=L+i*bw,y=H-B-h;
    s+=`<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${Math.max(1,bw-2).toFixed(1)}" height="${Math.max(.5,h).toFixed(1)}" fill="#d4a24e" opacity=".85" data-tip="<b>${r.y} ~ ${r.y+49}</b> · ${fmt(r.c)} 人"/>`;
    if(i%6===0)s+=`<text x="${(x+bw/2).toFixed(1)}" y="${H-7}" font-size="9" fill="#8b94a3" text-anchor="middle">${r.y}</text>`;});
  el.innerHTML=s+'</svg>';
}
function hbar(el,rows,color,labelW,W){
  W=W||520;labelW=labelW||80;
  const max=rows.reduce((m,r)=>Math.max(m,r.c||0),0)||1,rh=26;
  let s=`<svg viewBox="0 0 ${W} ${rows.length*rh+6}" width="100%">`;
  rows.forEach((r,i)=>{const y=i*rh+3,w=Math.max(2,(r.c||0)/max*(W-labelW-95));
    s+=`<text x="${labelW}" y="${y+14}" text-anchor="end" font-size="12" fill="#e8e6df">${esc(r.n||'（未注）')}</text>`+
       `<rect x="${labelW+8}" y="${y+4}" width="${w.toFixed(1)}" height="12" rx="3" fill="${color}" opacity=".85" data-tip="<b>${esc(r.n||'（未注）')}</b> · ${fmt(r.c)} 条"/>`+
       `<text x="${(labelW+14+w).toFixed(1)}" y="${y+14}" font-size="10.5" fill="#8b94a3">${fmt(r.c)}</text>`;});
  el.innerHTML=s+'</svg>';
}
hist($('years'),S.years);
hbar($('dynasties'),S.dynasties,'#6fb3a0',64);
$('t-kin').textContent=fmt(S.tot.kin);$('t-assoc').textContent=fmt(S.tot.assoc);
$('t-entry').textContent=fmt(S.tot.entry);$('t-addr').textContent=fmt(S.tot.addr);
hbar($('kin'),S.kin,'#c56a5a',150);
hbar($('assoc'),S.assoc,'#5b8db8',150);
hbar($('entry'),S.entry,'#6fb3a0',160);
hbar($('addr'),S.addrty,'#d4a24e',150);

/* ---------- 完整度 ---------- */
(function(){
  const C=S.cov;
  const rows=[['索引年（c_index_year）',C.iy],['生年（c_birthyear）',C.b],['卒年（c_deathyear）',C.d],['整理者注记（c_notes 非空）',C.notes]];
  $('coverage').innerHTML=rows.map(([k,v])=>{const p=v/C.t*100;
    return `<div style="margin:9px 0"><div class="small">${k}：<b style="color:var(--ink)">${fmt(v)}</b> / ${fmt(C.t)}（${p.toFixed(1)}%）</div><div class="prog"><i style="width:${Math.max(1,p)}%"></i></div></div>`;}).join('')
   +`<p class="small" style="margin-top:12px">① 不到一半的人有索引年、生卒年更稀——但库并不硬造数字：<code>biog_main</code> 用 <code>c_by_nh_code</code>（年号码）、<code>c_by_range</code>（区间码）、<code>c_by_intercalary</code>（闰月）、<code>c_by_day_gz</code>（干支日）等十余个字段把「模糊」本身编码进结构。</p>
    <p class="small" style="margin-top:6px">② 女性 ${fmt(C.f)} 人（${(C.f/C.t*100).toFixed(1)}%），多经亲属表以「某人之妻/母」入录——覆盖率本身就是史料现实。</p>
    <p class="small" style="margin-top:6px">③ 地名坐标覆盖 ${fmt(S.tot.addrxy)} / ${fmt(S.tot.addrtot)}（${(S.tot.addrxy/S.tot.addrtot*100).toFixed(1)}%）——有地址不等于有坐标；完整漏斗见「宋人分布图 v1」。</p>`;
})();

/* ---------- 籍贯气泡地图 ---------- */
(function(){
  const MW=1060,MH=560,X0=96,X1=126,Y0=16,Y1=50;
  const mpx=l=>Math.max(8,Math.min(MW-8,(l-X0)/(X1-X0)*MW));
  const mpy=l=>Math.max(8,Math.min(MH-8,MH-(l-Y0)/(Y1-Y0)*MH));
  const P=S.places,max=Math.max(...P.map(p=>p.c));
  let s=`<svg viewBox="0 0 ${MW} ${MH}" width="100%" style="background:radial-gradient(120% 90% at 60% 40%,#151b25 0%,#0c0f14 100%);border-radius:8px">`;
  for(let l=100;l<=125;l+=5)s+=`<line x1="${mpx(l)}" y1="0" x2="${mpx(l)}" y2="${MH}" stroke="#2a3342" stroke-width=".5" opacity=".4"/><text x="${mpx(l)+3}" y="13" font-size="9.5" fill="#5b6675">${l}°E</text>`;
  for(let l=20;l<=50;l+=5)s+=`<line x1="0" y1="${mpy(l)}" x2="${MW}" y2="${mpy(l)}" stroke="#2a3342" stroke-width=".5" opacity=".4"/><text x="4" y="${mpy(l)-3}" font-size="9.5" fill="#5b6675">${l}°N</text>`;
  P.forEach(p=>{const x=mpx(p.x),y=mpy(p.y),r=Math.sqrt(p.c/max)*13+2.5;
    s+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${(r*1.8).toFixed(1)}" fill="#d4a24e" opacity=".14"/>`+
       `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(1)}" fill="#d4a24e" opacity=".8" stroke="#f0d9a8" stroke-width=".6" data-tip="<b>${esc(p.n)}</b> · ${fmt(p.c)} 人<br>${p.x.toFixed(2)}, ${p.y.toFixed(2)}"/>`;});
  P.slice(0,18).forEach(p=>{const x=mpx(p.x),y=mpy(p.y),r=Math.sqrt(p.c/max)*13+2.5;
    s+=`<text x="${x.toFixed(1)}" y="${(y-r-4).toFixed(1)}" font-size="10.5" fill="#e8e6df" opacity=".9" text-anchor="middle" style="paint-order:stroke;stroke:#0b0e13;stroke-width:2.5px;pointer-events:none">${esc(p.n)}</text>`;});
  s+=`<text x="12" y="${MH-10}" font-size="10.5" fill="#5b6675">全朝代「籍贯(基本地址)」Top40 · 圆面积 ∝ 人数 · 经纬网格每 5° · 生成于 ${'2026-09-27'}</text>`;
  $('map').innerHTML=s+'</svg>';
})();

/* ---------- 网络中心 ---------- */
hbar($('toplink'),S.toplink.map(t=>({n:t.n+'（'+(t.dy||'?')+'）',c:t.c})),'#6fb3a0',170,980);

/* ---------- 苏轼 tabs ---------- */
let tabIx=0;
function panel(i){
  const m=S.su_main;
  if(i===0){
    const alt=(S.su_alt||[]).map(a=>`<span class="pill">${esc(a.n)}${a.ty?' · '+esc(a.ty):''}</span>`).join('');
    const src=(S.su_src||[]).map(x=>`<span class="pill" style="color:var(--dim)">${esc(x.n)}${x.p?' · '+esc(x.p):''}</span>`).join('');
    const ent=(S.su_entry||[]).map(x=>esc(x.n)+(x.y?'（纪年 '+x.y+'）':'')).join('；');
    return `<div style="display:flex;gap:16px;align-items:baseline;flex-wrap:wrap">
      <b style="font-size:28px;color:var(--gold);letter-spacing:3px">${esc(m.nm)}</b>
      <span class="small">personid ${m.id} · ${esc(m.dy)} · 索引年 ${m.iy} · ${m.b}–${m.d}（享年 ${m.age}）</span></div>
    <p class="small" style="margin-top:12px">别名：${alt||'—'}</p>
    <p class="small" style="margin-top:6px">入仕：${ent||'—'} <span style="color:var(--dim)">（<code>c_entry_nh_year</code> 存纪年而非公元——对照史实：嘉祐二年 1057 进士、嘉祐六年 1061 制科贤良方正）</span></p>
    <p class="small" style="margin-top:6px">传记出处（${(S.su_src||[]).length} 条）：${src}</p>
    ${m.notes?`<p class="small" style="margin-top:10px;font-style:italic;color:var(--dim)">整理者注记（英文原文节选）：“${esc(m.notes)}…”</p>`:''}`;
  }
  if(i===1)return `<table><tr><th>类型</th><th>地点</th><th>经度</th><th>纬度</th></tr>`+S.su_addr.map(a=>`<tr><td class="small">${esc(a.tn||'?')}</td><td>${esc(a.n||'未具名')}</td><td class="small">${a.x!=null?a.x.toFixed(3):'—'}</td><td class="small">${a.y!=null?a.y.toFixed(3):'—'}</td></tr>`).join('')+`</table>`;
  if(i===2)return `<table><tr><th>关系</th><th>人物</th></tr>`+S.su_kin.map(k=>`<tr><td class="small">${esc(k.rel)}</td><td>${esc(k.n)}</td></tr>`).join('')+`</table>`;
  if(i===3)return `<p class="small" style="margin-bottom:8px">显示前 ${S.su_assoc.length} 条 / 全库 ${fmt(S.su_assoc_tot)} 条（悬停榜单见「五」——苏轼即全网第二中心）</p>`+S.su_assoc.map(a=>`<span class="pill">${esc(a.n)} · ${esc(a.rel)}${a.y?' · '+a.y:''}</span>`).join('');
  return `<table><tr><th>起</th><th>讫</th><th>职事官</th><th>任地</th></tr>`+S.su_post.map(p=>`<tr><td class="small">${p.fy>0?p.fy:'—'}</td><td class="small">${p.ly>0?p.ly:'—'}</td><td>${esc(p.o||'?')}</td><td class="small">${esc(p.place||'—')}</td></tr>`).join('')+`</table><p class="small" style="margin-top:6px">[未詳] = 除授记录存在、任地无明文——CBDB 不补空白。1061 凤翔签判起步，至 1101 终。</p>`;
}
function renderSu(){
  const defs=['生平与别名','籍贯与寓居（'+S.su_addr.length+'）','亲缘（'+S.su_kin.length+'）','交游（'+S.su_assoc.length+'/'+fmt(S.su_assoc_tot)+'）','仕履（'+S.su_post.length+'）'];
  $('sushi').innerHTML='<div class="tabs">'+defs.map((d,j)=>`<button class="${j===tabIx?'on':''}">${d}</button>`).join('')+'</div><div>'+panel(tabIx)+'</div>';
  $('sushi').querySelectorAll('button').forEach((b,j)=>b.onclick=()=>{tabIx=j;renderSu();});
}
renderSu();

/* ---------- 地理半壁 ---------- */
(function(){
  const GD={ming_routes_2016:'明代驿路（线）',ming_stations_2016:'明代驿站（点）',hartwell_pref_pgn:'Hartwell 四快照府级面 741/1080/1200/1391——「宋人分布图 v1」底图',academies_2957:'历代书院（点，带坐标）',dem:'~1km 高程栅格瓦片——「庐山地形」数据源',v6_pref_pgn:'CHGIS V6 时序府级面（1080 年仅 303 有效面中宋代缺，见 demo A 校勘台）',v6_pref_pts:'CHGIS V6 时序府级点',hartwell_cnty_pgn:'Hartwell 县级面（升级县级分辨率用）',v6_cnty_pts:'CHGIS V6 时序县级点',tgaz_part_of:'TGaz 地名隶属关系',tgaz_spelling:'TGaz 历史拼写/异体记录',dcw_asia_contour:'DCW 亚洲海岸线/等高线底图',tgaz_placename:'TGaz 中国历史地名辞典·地名主表'};
  const order=['v6_pref_pgn','v6_pref_pts','v6_cnty_pts','hartwell_pref_pgn','hartwell_cnty_pgn','dem','academies_2957','ming_stations_2016','ming_routes_2016','tgaz_placename','tgaz_spelling','tgaz_part_of','dcw_asia_contour'];
  const g=Object.fromEntries(S.gis.map(x=>[x.n,x.c]));
  const sch={};S.tables.forEach(t=>{const s=sch[t.sc]=sch[t.sc]||[0,0];s[0]++;s[1]+=t.rows;});
  const SN={public:'CBDB 人物库本体',chgis:'CHGIS V2–V6 + Hartwell + 明代地理 + DEM',harv:'TGaz 地名辞典 + 谭图 GBK 名表 + DCW',ogr_system_tables:'GDAL/OGR 元数据'};
  $('gis').innerHTML=`<tr><th>schema</th><th>表数</th><th>行数(估)</th><th>内容</th></tr>`+
    Object.entries(sch).map(([k,v])=>`<tr><td><span class="sch ${k}">${k}</span></td><td>${v[0]}</td><td>${fmt(v[1])}</td><td class="small">${SN[k]||''}</td></tr>`).join('')+
    `<tr><th colspan="4" style="padding-top:12px">重点地理图层</th></tr><tr><th colspan="2">图层</th><th>行数</th><th>说明</th></tr>`+
    order.filter(n=>g[n]!=null).map(n=>`<tr><td colspan="2"><code>${n}</code></td><td>${fmt(g[n])}</td><td class="small">${GD[n]||descOf(n)}</td></tr>`).join('');
})();

/* ---------- 395 表目录 ---------- */
function renderTables(){
  const q=($('tblfilter')&&$('tblfilter').value||'').toLowerCase();
  const max=S.tables[0].rows||1;
  const rows=S.tables.filter(t=>!q||(t.n+' '+descOf(t.n)+' '+t.sc).toLowerCase().includes(q));
  let h='<table><tr><th>schema</th><th>表名</th><th>中文说明</th><th>列</th><th style="width:170px">行(估)</th></tr>';
  rows.forEach(t=>{const p=Math.max(1,Math.round(Math.sqrt(t.rows/max)*100));
    h+=`<tr><td><span class="sch ${t.sc}">${t.sc}</span></td><td><code>${t.n}</code></td><td class="small">${esc(descOf(t.n))}</td><td class="small">${t.cols}</td><td class="small">${fmt(t.rows)}<div class="prog" style="height:4px"><i style="width:${p}%"></i></div></td></tr>`;});
  $('tables').innerHTML=rows.length?h+'</table>':`<div class="small">无匹配（${S.tables.length} 表中）</div>`;
}
renderTables();
if($('tblfilter'))$('tblfilter').oninput=renderTables;

/* ---------- footer ---------- */
$('foot').innerHTML=`数据：pg32b @ 192.168.3.32（PostgreSQL 18.6 + PostGIS 3.6.4，cbdb 库 395 表 / ${fmt(allRows)} 行）· CBDB（Harvard，20260919 版）· CHGIS V6 与 Hartwell 复原（学术使用许可，禁再分发）· TGaz · 本页全部统计实算自数据库 · 生成于 2026-09-27 · xiangrugu 工作区 demo/ · <a href="A-song-distribution.html" style="color:var(--gold)">专题演示：宋人分布图 v1</a> · <a href="catalog/index.html" style="color:var(--gold)">数据总目（399 表全量画像）</a>`;

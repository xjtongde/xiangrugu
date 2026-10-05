/* 蘇軾 · 人物全景（app_person_index.js）—— 数据全部来自 extract_person.py 实测 */
const $=id=>document.getElementById(id);
const fmt=n=>(n??0).toLocaleString('en-US');
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const now=()=>(typeof performance!=='undefined'&&performance.now)?performance.now():Date.now();
const tip=$('tip');
document.addEventListener('mousemove',e=>{const t=e.target.closest&&e.target.closest('[data-tip]');
  if(t){tip.style.display='block';tip.innerHTML=t.getAttribute('data-tip');
    tip.style.left=Math.min(innerWidth-350,e.clientX+12)+'px';tip.style.top=(e.clientY+14)+'px';}
  else tip.style.display='none';});
function countUp(el,to,dur=950){const t0=now();
  function f(){const p=Math.min(1,(now()-t0)/dur),e=1-Math.pow(1-p,3);
    el.textContent=fmt(Math.round(to*e));if(p<1)requestAnimationFrame(f);}
  requestAnimationFrame(f);}

const M=D.main,C=D.counts;
/* ---------- hero ---------- */
$('hName').textContent=M.nm;
$('hPy').textContent=M.pinyin;
$('hPills').innerHTML=D.alt.map(a=>`<span class="pill${a.ty==='諡號'?' gd':''}"><b>${esc(a.ty||'别称')}</b>${esc(a.n)} <span style="opacity:.6;font-family:Georgia,serif;font-size:11px">${esc(a.py||'')}</span></span>`).join('');
const life=`${M.b}–${M.d}（${(M.d||0)-(M.b||0)+1} 岁）`;
$('hMeta').innerHTML=`${esc(M.dyn||'')} · 郡望 ${esc(M.chor||'—')} · 索引地址 ${esc(M.idx_addr||'—')}${M.idx_x!=null?`（${M.idx_x.toFixed(2)}, ${M.idx_y.toFixed(2)}）`:''} · 生卒 ${life} · CBDB personid <code>${M.id}</code> · 索引年 ${M.iy}（${esc(M.iyt||'')}）`;
$('stats').innerHTML=CFG.stats.map(s=>`<div class="stat"><b>0</b><span>${s[1]}</span></div>`).join('');
[...$('stats').children].forEach((el,i)=>countUp(el.firstChild,CFG.stats[i][0]));

/* ---------- 一 · 身份档案 ---------- */
const kv=(k,v)=>`<dt>${k}</dt><dd>${v}</dd>`;
$('kvMain').innerHTML=
  kv('姓名',`<b style="font-size:16px">${esc(M.nm)}</b> <span class="dim">（${esc(M.pinyin)}）</span>`)+
  kv('生卒年',`${life} <span class="small">（库载生年 ${M.b}；出生地记录作 ${M.b+1}，两说并存）</span>`)+
  kv('朝代 / 郡望',`${esc(M.dyn||'—')} / ${esc(M.chor||'—')}`)+
  kv('户籍状态',esc(M.hh||'—'))+
  kv('索引地址',`${esc(M.idx_addr||'—')} <span class="small">(${M.idx_x}, ${M.idx_y})</span>`)+
  kv('活跃年 fl',`${M.fl1??'—'} ~ ${M.fl2??'—'}`);
$('notes').innerHTML='<b style="color:var(--gold);font-style:normal">CBDB 原编者注记（英文，照录）：</b><br>'+esc(M.notes||'（无）');
$('alts').innerHTML=D.alt.map(a=>`<div style="display:flex;gap:10px;align-items:baseline;padding:6px 0;border-bottom:1px dashed #1d2530"><b style="font-size:17px;color:var(--gold);min-width:110px">${esc(a.n)}</b><span class="small">${esc(a.py||'')} · ${esc(a.ty||'')}${a.src?' · 出处 '+esc(a.src)+(a.pg?' '+esc(a.pg):''):''}</span></div>`).join('');
$('sts').innerHTML=D.status.map(s=>`<span class="stchip${(s.st||'').includes('黨籍')?' party':''}" data-tip="${esc(s.st)}${s.y1?'（'+s.y1+(s.y2?'–'+s.y2:'')+'）':''}${s.sup?' · '+esc(s.sup):''}">${esc(s.st)}</span>`).join('');

/* ---------- 二 · 入仕 ---------- */
$('entries').innerHTML=D.entry.map(e=>{
  const nh=e.nh?`纪年第 ${e.nh} 年`:'';
  return `<div class="entrycard"><span class="yr">${e.y||'—'}</span><span class="t"><b>${esc(e.n)}</b><span>${e.age?'时年 '+e.age+' 岁 · ':''}${e.rk?'榜列第 '+esc(e.rk)+' 等 · ':''}${nh} · c_sequence=${e.seq}</span></span></div>`;}).join('');

/* ---------- 三 · 人生年表 ---------- */
(function(){
  const JADE='#6fb3a0',RED='#c56a5a',GOLD='#d4a24e',DIM='#8b94a3';
  const Y0=1030,Y1=1106,W=1560,H=230,L=44,R=20,T=30,B=30;
  const x=y=>L+(y-Y0)/(Y1-Y0)*(W-L-R);
  const posts=D.post.filter(p=>p.fy!=null);
  const lanes=[];
  posts.forEach(p=>{
    const a=x(p.fy),b=x(Math.max((p.ly&&p.ly>p.fy)?p.ly:p.fy+2));
    let li=0;while(li<lanes.length&&lanes[li].some(s=>a<s[1]+3&&b+3>s[0]))li++;
    (lanes[li]=lanes[li]||[]).push([a,b]);
    p._l=li;p._a=a;p._b=b;
  });
  let s='';
  for(let y=1030;y<=1105;y+=5){
    const maj=y%10===0;
    s+=`<line x1="${x(y).toFixed(1)}" y1="${T-8}" x2="${x(y).toFixed(1)}" y2="${H-B+6}" stroke="${maj?'#2a3342':'#1d2530'}" stroke-width="${maj?1:.6}"/>`;
    if(maj)s+=`<text x="${x(y).toFixed(1)}" y="${H-B+20}" text-anchor="middle" font-size="11" fill="${DIM}" font-family="Georgia,serif">${y}</text>`;
  }
  s+=`<line x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}" stroke="#2a3342"/>`;
  s+=`<line x1="${x(M.b)}" y1="${T-14}" x2="${x(M.b)}" y2="${H-B}" stroke="${RED}" stroke-dasharray="3 3" opacity=".7"/><text x="${x(M.b)-5}" y="${T-6}" text-anchor="end" font-size="11" fill="${RED}">生 ${M.b}</text>`;
  s+=`<line x1="${x(M.d)}" y1="${T-14}" x2="${x(M.d)}" y2="${H-B}" stroke="${RED}" stroke-dasharray="3 3" opacity=".7"/><text x="${x(M.d)+5}" y="${T-6}" font-size="11" fill="${RED}">卒 ${M.d}（常州）</text>`;
  posts.forEach(p=>{
    const ly=(p.ly&&p.ly>p.fy)?p.ly:null,y=T+4+p._l*17,w=Math.max(4,p._b-p._a);
    s+=`<rect x="${p._a.toFixed(1)}" y="${y}" width="${w.toFixed(1)}" height="11" rx="2.5" fill="${ly?JADE:'none'}" stroke="${JADE}" stroke-width="${ly?0:1.2}" ${ly?'opacity=".85"':'stroke-dasharray="3 2"'} data-tip="<b>${p.fy}${ly?'–'+ly:'–?'} ${esc(p.off||'')}</b><br>${esc(p.place||'[未詳]')}${p.appt?' · '+esc(p.appt):''}${ly?'':'<br>离任年库内未詳（虚框）'}"/>`;
    if(w>46&&p.place&&p.place!=='[未詳]')s+=`<text x="${(p._a+5).toFixed(1)}" y="${y+9}" font-size="9" fill="#0e1116" font-weight="600" pointer-events="none">${esc(p.place)}</text>`;
  });
  D.entry.forEach(e=>{if(e.y)s+=`<path d="M${x(e.y)} ${H-B-6} l5 6 l-5 6 l-5 -6 Z" fill="${GOLD}" data-tip="<b>${e.y} ${esc(e.n)}</b><br>${e.rk?'第 '+esc(e.rk)+' 等 · ':''}${e.age?'时年 '+e.age:''}"/>`;});
  const svg=$('tl');
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
  svg.setAttribute('width',W);
  svg.innerHTML=s;
})();

/* ---------- 四 · 亲缘 ---------- */
function kinBucket(rel){
  if(/孫|姪|堂|從|世/.test(rel))return '后裔与族亲';
  if(/妻|姻|婿|妾|舅|姨/.test(rel))return '婚姻与姻亲';
  if(/父|母|兄|弟|姊|妹|子|女/.test(rel))return '至亲';
  return '其他';
}
function kinTable(list,hotSet){
  const g={};list.forEach(k=>{(g[kinBucket(k.rel)]=g[kinBucket(k.rel)]||[]).push(k);});
  return ['至亲','婚姻与姻亲','后裔与族亲','其他'].filter(k=>g[k]).map(k=>
    `<div class="kinhead">${k}（${g[k].length}）</div><table class="tb"><tr><th>关系</th><th>人物</th><th>生卒</th><th>朝代</th><th>pid</th></tr>`+
    g[k].map(r=>`<tr><td><span class="rel${hotSet.has(r.rel)?' hot':''}">${esc(r.rel)}</span>${r.mourning?`<span class="small"> 服:${esc(r.mourning)}</span>`:''}</td><td><b>${esc(r.n)}</b></td><td class="yrs">${r.b&&r.b>0?r.b:'?'}–${r.d&&r.d>0?r.d:'?'}</td><td class="dim">${esc(r.dyn||'—')}</td><td class="pid">${r.pid}</td></tr>`).join('')+`</table>`).join('');
}
$('kinA').innerHTML=kinTable(D.kin,new Set(['父','母','弟','兄','妻','妾','三子','长子','次子','女']));
$('kinB').innerHTML=kinTable(D.kin2,new Set());

/* ---------- 五 · 地址 ---------- */
(function(){
  const ord=['籍貫(基本地址)','出生地','死所','葬地','前住地','遊歷或曾經到過'];
  const g={};D.addr.forEach(a=>{(g[a.ty||'其他']=g[a.ty||'其他']||[]).push(a);});
  $('addrGrp').innerHTML=Object.keys(g).sort((a,b)=>ord.indexOf(a)-ord.indexOf(b)).map(t=>
    `<div class="addrgrp"><span class="g">${esc(t)}（${g[t].length}）</span><div class="items">`+
    g[t].map(a=>`${esc(a.n||'?')}<i>${a.y1?' '+a.y1:''}${a.y2?'–'+a.y2:''}${a.x!=null?' ('+Number(a.x).toFixed(2)+','+Number(a.y).toFixed(2)+')':' (无坐标)'}</i>`).join(' · ')+
    `</div></div>`).join('');
})();

/* ---------- 六 · 著作 ---------- */
$('worksT').innerHTML=`<tr><th>题名</th><th>角色</th><th>年</th><th>类型</th><th>存佚</th></tr>`+
  D.works.map(w=>`<tr><td><b>${esc(w.title)}</b> <span class="small">${esc(w.tpy||'')}</span></td><td class="dim">${esc(w.role||'未詳')}</td><td class="yrs">${(w.y&&w.y>0)?w.y:(w.ty&&w.ty>0)?w.ty:'—'}</td><td class="dim">${esc(w.type||'—')}</td><td>${w.extant==='現存'?'<span class="ext y">現存</span>':'<span class="ext n">'+esc(w.extant||'未詳')+'</span>'}</td></tr>`).join('');

/* ---------- 七 · 出处 ---------- */
$('srcs').innerHTML=D.src.map(s=>`<div class="srcrow"><span style="min-width:230px"><b>${esc(s.title)}</b>${s.main?' <span class="mainpill">主要出处</span>':''}</span><span class="pg">${esc(s.pages||'')}</span>${s.notes?`<span class="small">${esc(s.notes)}</span>`:''}</div>`).join('');
$('kvData').innerHTML=
  kv('personid',`<code>${M.id}</code>`)+
  kv('记录盘点',`社交 <b>${fmt(C.assoc)}</b> · 亲缘 ${C.kin}＋反向 ${C.kin_rev} · 地址 ${C.addr} · 除授 ${C.post} · 著作 ${C.text} · 出处 ${C.source} · 身份 ${C.status} · 别名 ${C.alt}`)+
  kv('零记录表',`events_data 0 · biog_inst_data 0 · possession_data 0（他的生平事件主要藏在除授/地址/社交的年份里）`)+
  kv('外部对照',`ctext 291374 · Wikidata Q36020 · 中研院权威 018284`)+
  kv('生成',CFG.gen+' · extract_person.py（personid 参数化，换人可重跑）');

/* ---------- 渐入 / footer ---------- */
if(typeof IntersectionObserver!=='undefined'){
  const io=new IntersectionObserver(es=>{es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}})},{rootMargin:'80px'});
  document.querySelectorAll('.fade,h2,.card').forEach(el=>{el.classList.add('fade');io.observe(el);});
}else document.querySelectorAll('.fade').forEach(el=>el.classList.add('in'));
$('foot').innerHTML=`数据：pg32b @ 192.168.3.32 · cbdb 库（CBDB Harvard 20260919 版）· 本页全部数字实测于 ${CFG.gen}（biog_main/altname/entry/kin×2向/biog_addr/posted_to_office×posted_to_addr/biog_text×text_codes/biog_source/status_data）· 管线：extract_person.py → person_${M.id}.json → build_person.py · 学术使用许可，禁再分发 · <a href="../catalog/index.html" style="color:var(--gold)">数据总目</a> · <a href="../pg32b-roam.html" style="color:var(--gold)">数据漫游</a>`;

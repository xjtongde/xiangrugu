/* pg32b 数据总目 · 页面逻辑（三卷共用，CFG 驱动；无外部依赖，离线可跑） */
const $=id=>document.getElementById(id);
const fmt=n=>(n??0).toLocaleString('en-US');
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const now=()=>(typeof performance!=='undefined'&&performance.now)?performance.now():Date.now();
const tip=$('tip');
document.addEventListener('mousemove',e=>{const t=e.target.closest&&e.target.closest('[data-tip]');
  if(t){tip.style.display='block';tip.innerHTML=t.getAttribute('data-tip');
    tip.style.left=Math.min(innerWidth-370,e.clientX+12)+'px';tip.style.top=(e.clientY+14)+'px';}
  else tip.style.display='none';});

const PALETTE=['#d4a24e','#6fb3a0','#5b8db8','#c56a5a','#9b7fb8','#5aa8b8','#a8a05a','#c89b6a','#7a8ca0','#8fbc8f','#b8789b','#6a9fb5'];
const FAMCOL={};DATA.fams.forEach((f,i)=>FAMCOL[f.f]=PALETTE[i%PALETTE.length]);
const famcol=f=>FAMCOL[f]||'#8b94a3';

/* ---------- 标题 / KPI 滚动 ---------- */
document.title=CFG.title+' · pg32b 数据总目';
$('ttl').textContent=CFG.title;
$('h1').innerHTML=CFG.h1;
$('sub').innerHTML=CFG.sub;
$('topchips').textContent=`count(*) 精确实测 · ${CFG.gen}`;
function countUp(el,to,dur=950){const t0=now();
  function f(){const p=Math.min(1,(now()-t0)/dur),e=1-Math.pow(1-p,3);
    el.textContent=fmt(Math.round(to*e));if(p<1)requestAnimationFrame(f);}
  requestAnimationFrame(f);}
$('stats').innerHTML=CFG.stats.map(s=>`<div class="stat"><b>0</b><span>${s[1]}</span></div>`).join('');
[...$('stats').children].forEach((el,i)=>countUp(el.firstChild,CFG.stats[i][0]));

/* ---------- 行数版图（treemap） ---------- */
function treemap(items,x,y,w,h,out){
  if(!items.length||w<1||h<1)return;
  if(items.length===1){out.push({it:items[0],x,y,w,h});return;}
  const total=items.reduce((s,i)=>s+i.v,0)||1;
  let acc=0,best=1,bd=1e18;
  for(let i=0;i<items.length-1;i++){acc+=items[i].v;const d=Math.abs(acc/total-.5);if(d<bd){bd=d;best=i+1;}}
  const L=items.slice(0,best),R=items.slice(best);
  const lt=(L.reduce((s,i)=>s+i.v,0)/total)||0;
  if(w>=h){treemap(L,x,y,Math.max(1,w*lt),h,out);treemap(R,x+w*lt,y,w-w*lt,h,out);}
  else{treemap(L,x,y,w,Math.max(1,h*lt),out);treemap(R,x,y+h*lt,w,h-h*lt,out);}
}
(function(){
  const W=700,H=330,N=26;
  const sorted=[...DATA.tables].sort((a,b)=>b.rows-a.rows);
  const head=sorted.slice(0,N).map(t=>({v:Math.max(t.rows,1),t}));
  const rest=sorted.slice(N);
  if(rest.length)head.push({v:Math.max(rest.reduce((s,t)=>s+t.rows,0),1),rest:rest.length});
  const out=[];treemap(head,2,2,W-4,H-4,out);
  let s=`<svg class="tm" viewBox="0 0 ${W} ${H}" width="100%">`;
  out.forEach(o=>{
    if(o.it.rest!=null){
      s+=`<rect x="${o.x.toFixed(1)}" y="${o.y.toFixed(1)}" width="${o.w.toFixed(1)}" height="${o.h.toFixed(1)}" rx="3" fill="#2a3342" opacity=".55" data-tip="<b>其余 ${o.it.rest} 表</b><br>合计 ${fmt(o.it.v)} 行"/>`;
      if(o.w>70&&o.h>22)s+=`<text x="${(o.x+o.w/2).toFixed(1)}" y="${(o.y+o.h/2+4).toFixed(1)}" font-size="11" fill="#8b94a3" text-anchor="middle" pointer-events="none">其余 ${o.it.rest} 表</text>`;
      return;
    }
    const t=o.it.t,col=famcol(t.fam);
    s+=`<rect x="${o.x.toFixed(1)}" y="${o.y.toFixed(1)}" width="${o.w.toFixed(1)}" height="${o.h.toFixed(1)}" rx="3" fill="${col}" opacity=".78" data-tb="${esc(t.tb)}" data-tip="<b>${esc(t.tb)}</b> · ${fmt(t.rows)} 行 × ${t.ncols} 列<br>${esc(t.desc)||'（无说明）'}<br><span style='color:#8b94a3'>家族：${esc(t.fam)} · 点击直达卡片</span>"/>`;
    if(o.w>62&&o.h>20){
      const nm=o.w>100?t.tb:(t.tb.length>Math.floor(o.w/7.2)?t.tb.slice(0,Math.max(3,Math.floor(o.w/7.2)))+'…':t.tb);
      s+=`<text x="${(o.x+7).toFixed(1)}" y="${(o.y+15).toFixed(1)}" font-size="10.5" fill="#0e1116" font-weight="600" pointer-events="none" font-family="ui-monospace,Menlo,monospace">${esc(nm)}</text>`;
      if(o.h>36)s+=`<text x="${(o.x+7).toFixed(1)}" y="${(o.y+28).toFixed(1)}" font-size="9.5" fill="#0e1116" opacity=".75" pointer-events="none">${fmt(t.rows)} 行</text>`;
    }
  });
  $('treemap').innerHTML=s+'</svg>';
  $('treemap').querySelectorAll('rect[data-tb]').forEach(r=>r.addEventListener('click',()=>{
    const tb=r.getAttribute('data-tb');
    $('q').value=tb;activeFam=null;syncFamUI();render();
    const card=document.getElementById('card-'+tb);
    if(card){setOpen(card,true);card.scrollIntoView({behavior:'smooth',block:'center'});}
  }));
})();

/* ---------- 家族 donut + 图例筛选 ---------- */
let activeFam=null;
(function(){
  const tot=DATA.fams.reduce((s,f)=>s+f.r,0)||1;
  const cx=85,cy=85,r2=72,r1=45;let a=-Math.PI/2;
  const P=a=>[cx+r2*Math.cos(a),cy+r2*Math.sin(a)],P1=a=>[cx+r1*Math.cos(a),cy+r1*Math.sin(a)];
  let s=`<svg viewBox="0 0 170 170" width="170" height="170">`;
  DATA.fams.forEach(f=>{
    const a1=a+(f.r/tot)*Math.PI*2,gap=Math.min(.03,(a1-a)*.08),b0=a+gap,b1=Math.max(a1-gap,b0+.001);
    const lg=(a1-a)>Math.PI?1:0;
    s+=`<path d="M${P(b0)[0].toFixed(2)} ${P(b0)[1].toFixed(2)} A${r2} ${r2} 0 ${lg} 1 ${P(b1)[0].toFixed(2)} ${P(b1)[1].toFixed(2)} L${P1(b1)[0].toFixed(2)} ${P1(b1)[1].toFixed(2)} A${r1} ${r1} 0 ${lg} 0 ${P1(b0)[0].toFixed(2)} ${P1(b0)[1].toFixed(2)} Z" fill="${famcol(f.f)}" opacity=".85" data-fam="${esc(f.f)}" data-tip="<b>${esc(f.f)}</b><br>${f.t} 表 · ${fmt(f.r)} 行 · ${(f.r/tot*100).toFixed(1)}%"/>`;
    a=a1;
  });
  s+=`<text x="85" y="81" text-anchor="middle" font-size="19" fill="#e8e6df" font-family="Georgia,serif">${fmt(tot)}</text><text x="85" y="99" text-anchor="middle" font-size="10.5" fill="#8b94a3">总行数</text></svg>`;
  $('donut').innerHTML=s;
  $('donutleg').innerHTML=DATA.fams.map(f=>`<div class="legendrow" data-fam="${esc(f.f)}"><i style="background:${famcol(f.f)}"></i><span class="n">${esc(f.f)}</span><span class="small">${f.t}表</span><b>${fmt(f.r)}</b></div>`).join('');
  const go=fam=>{activeFam=(activeFam===fam)?null:fam;syncFamUI();render();};
  $('donutleg').querySelectorAll('.legendrow').forEach(el=>el.addEventListener('click',()=>go(el.getAttribute('data-fam'))));
  $('donut').querySelectorAll('path').forEach(el=>el.addEventListener('click',()=>go(el.getAttribute('data-fam'))));
})();
function syncFamUI(){
  $('donutleg').querySelectorAll('.legendrow').forEach(el=>el.classList.toggle('off',activeFam&&el.getAttribute('data-fam')!==activeFam));
  document.querySelectorAll('#famrow .famchip').forEach(el=>el.classList.toggle('on',(el.getAttribute('data-fam')||'')===activeFam||(activeFam===null&&el.getAttribute('data-fam')===null)));
}
$('famrow').innerHTML=`<span class="famchip on" data-fam="">全部 <b>${DATA.tables.length}</b></span>`+
  DATA.fams.map(f=>`<span class="famchip" data-fam="${esc(f.f)}"><i style="background:${famcol(f.f)}"></i>${esc(f.f)} <b>${f.t}</b></span>`).join('');
document.querySelectorAll('#famrow .famchip').forEach(el=>el.addEventListener('click',()=>{
  const f=el.getAttribute('data-fam');activeFam=(f==='')?null:(activeFam===f?null:f);syncFamUI();render();}));

/* ---------- 列类型堆叠条 ---------- */
(function(){
  const CLS={int:['整数','#5b8db8'],dec:['定点/浮点','#6fb3a0'],txt:['文本','#d4a24e'],time:['日期时间','#9b7fb8'],geo:['几何(空间)','#c56a5a'],oth:['其他','#8b94a3']};
  function tclass(c){
    if(c.u==='geometry')return 'geo';
    const t=c.dt||'';
    if(t==='integer'||t==='bigint'||t==='smallint')return 'int';
    if(t==='numeric'||t==='real'||t==='double precision')return 'dec';
    if(t.indexOf('character')===0||t==='text')return 'txt';
    if(t.indexOf('timestamp')===0||t.indexOf('date')===0||t.indexOf('time')===0)return 'time';
    return 'oth';
  }
  const cnt={};DATA.tables.forEach(t=>t.cols.forEach(c=>{const k=tclass(c);cnt[k]=(cnt[k]||0)+1;}));
  const tot=Object.values(cnt).reduce((a,b)=>a+b,0)||1;
  $('tbar').innerHTML=Object.keys(CLS).filter(k=>cnt[k]).map(k=>`<div style="flex:${cnt[k]};background:${CLS[k][1]}" data-tip="<b>${CLS[k][0]}</b> · ${fmt(cnt[k])} 列 · ${(cnt[k]/tot*100).toFixed(1)}%"></div>`).join('');
  $('typekey').innerHTML=Object.keys(CLS).filter(k=>cnt[k]).map(k=>`<span><i style="background:${CLS[k][1]}"></i>${CLS[k][0]} ${fmt(cnt[k])}</span>`).join('');
})();

/* ---------- 表卡片 ---------- */
let sortMode=0;
const SORTS=[['行数↓',(a,b)=>b.rows-a.rows],['名称 A→Z',(a,b)=>a.tb<b.tb?-1:1],['列数↓',(a,b)=>b.ncols-a.ncols||b.rows-a.rows]];
function firstSamp(t,cn){for(const r of (t.sample||[])){const v=r[cn];if(v!=null&&v!=='')return v;}return '';}
function colRow(t,c){
  const rows=t.rows||0,nn=c.nn??0;
  const nnp=rows?Math.round(nn/rows*100):0;
  const dp=(c.d!=null&&nn)?Math.round(c.d/nn*100):null;
  let val='<span class="rng">—</span>';
  if(c.geo){val=c.geo.map(g=>`<span class="mv" data-tip="${esc(g.v)} × ${fmt(g.c)}${g.srid!=null?' · SRID '+g.srid:''}">${esc(g.v)} <b>${fmt(g.c)}</b></span>`).join('')+(c.geo[0]&&c.geo[0].srid!=null?`<span class="mini g">SRID ${c.geo[0].srid}</span>`:'');}
  else if(c.m){val=c.m.map(x=>`<span class="mv" data-tip="${esc(x[0])} · ${fmt(x[1])} 行 · 占非空 ${nn?(x[1]/nn*100).toFixed(1):0}%">${esc(x[0])} <b>${fmt(x[1])}</b></span>`).join('');}
  else if(c.mn!=null){val=`<span class="rng">${esc(c.mn)} ~ ${esc(c.mx)}</span>`;}
  const sv=firstSamp(t,c.n);
  const dtl=c.u==='geometry'?'GEOM':(c.dt||'').replace('character varying','varchar').replace('double precision','float8').replace('timestamp without time zone','timestamp').replace('timestamp with time zone','timestamptz');
  return `<tr><td><span class="cn">${esc(c.n)}</span></td><td><span class="dt">${esc(dtl)}</span></td>`+
    `<td>${nn===0?'<span class="rng">全空</span>':fmt(nn)+`<span class="mini">${nnp}%</span><span class="mbar j"><i style="width:${nnp}%"></i></span>`}</td>`+
    `<td>${c.d!=null?fmt(c.d)+(dp!=null?`<span class="mbar g"><i style="width:${Math.min(100,dp)}%"></i></span>`:''):'<span class="rng">—</span>'}</td>`+
    `<td>${val}</td><td>${sv?`<span class="samp" data-tip="${esc(sv)}">${esc(sv.length>34?sv.slice(0,34)+'…':sv)}</span>`:'<span class="rng">—</span>'}</td></tr>`;
}
function bodyHTML(t){
  let h=`<div class="tbin">`;
  if(t.rel&&t.rel.length)h+=`<div class="secnote">关系推断（命名规约 · 本库 0 外键约束）</div><div>`+t.rel.map(r=>`<span class="relchip" data-tip="${esc(r[0])} 惯例指向 ${esc(r[1])}（推断，非数据库约束）">${esc(r[0])} → ${esc(r[1])}</span>`).join('')+`</div>`;
  h+=`<div class="secnote">列档案（${t.cols.length} 列 · 非空/distinct 为 count 实测 · 高频值 = 类别列 Top3）</div>
  <table class="prof"><tr><th>列名</th><th>类型</th><th>非空</th><th>distinct</th><th>值域 / 高频值</th><th>样例</th></tr>`+
  t.cols.map(c=>colRow(t,c)).join('')+`</table>`;
  if(t.sample&&t.sample.length){
    h+=`<div class="secnote">样例行（前 ${t.sample.length} 行 · 每格截断 70 字符）</div><div class="sampwrap"><table class="samp"><tr>`+
      t.cols.map(c=>`<th>${esc(c.n)}</th>`).join('')+`</tr>`+
      t.sample.map(r=>`<tr>`+t.cols.map(c=>`<td title="">${r[c.n]!=null?esc(String(r[c.n]).slice(0,46)):''}</td>`).join('')+`</tr>`).join('')+
      `</table></div>`;
  }else h+=`<div class="empty">空表（0 行）——结构保留，无数据。</div>`;
  return h+`</div>`;
}
function cardHTML(t){
  const lvb=t.lv==='ok'?'<span class="lv ok">✓实证</span>':t.lv==='doc'?'<span class="lv doc">◈通说</span>':'<span class="lv guess">?推断</span>';
  return `<div class="tcard" id="card-${esc(t.tb)}">
   <div class="thead">
    <span class="fdot" style="background:${famcol(t.fam)}"></span>
    <span class="tname">${esc(t.tb)}</span>${lvb}
    <span class="tdesc">${esc(t.desc)||'<i>（暂无说明——按名称亦无法可靠推断）</i>'}</span>
    ${t.geon?`<span class="mini g">${t.geon} 几何列</span>`:''}
    <span class="mini">${t.ncols} 列</span>
    <span class="tnum">${fmt(t.rows)}</span>
    <span class="chev">▶</span>
   </div><div class="tbody"></div></div>`;
}
function setOpen(card,on){
  const b=card.querySelector('.tbody');
  if(on){
    if(card.dataset.built!=='1'){const t=BY_TB[card.id.slice(5)];b.innerHTML=bodyHTML(t);card.dataset.built='1';}
    card.classList.add('open');b.style.maxHeight=b.scrollHeight+'px';
    setTimeout(()=>{if(card.classList.contains('open'))b.style.maxHeight='none';},380);
  }else{
    if(!card.classList.contains('open'))return;
    b.style.maxHeight=b.scrollHeight+'px';
    requestAnimationFrame(()=>requestAnimationFrame(()=>{card.classList.remove('open');b.style.maxHeight='0px';}));
  }
}
const BY_TB={};DATA.tables.forEach(t=>BY_TB[t.tb]=t);
let io=null;
if(typeof IntersectionObserver!=='undefined')
  io=new IntersectionObserver(es=>{es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}})},{rootMargin:'100px'});
function render(){
  const q=($('q').value||'').trim().toLowerCase();
  let rows=DATA.tables.filter(t=>(!activeFam||t.fam===activeFam)&&(!q||(t.tb+' '+t.desc+' '+t.cols.map(c=>c.n).join(' ')).toLowerCase().includes(q)));
  rows.sort(SORTS[sortMode][1]);
  $('count').textContent=`显示 ${rows.length} / ${DATA.tables.length} 表 · 合计 ${fmt(rows.reduce((s,t)=>s+t.rows,0))} 行`+(q?` · 搜索「${q}」`:'')+(activeFam?` · 家族「${activeFam}」`:'');
  $('list').innerHTML=rows.length?rows.map(cardHTML).join(''):'<div class="nohit">无匹配。试试列名（如 x_coord / c_personid）或中文说明。</div>';
  const cards=[...$('list').querySelectorAll('.tcard')];
  cards.forEach(c=>{c.querySelector('.thead').addEventListener('click',()=>setOpen(c,!c.classList.contains('open')));
    if(io)io.observe(c);else c.classList.add('in');});
}
render();
let deb=null;
$('q').addEventListener('input',()=>{clearTimeout(deb);deb=setTimeout(render,140);});
document.addEventListener('keydown',e=>{
  if(e.key==='/'&&document.activeElement!==$('q')){e.preventDefault();$('q').focus();}
  if(e.key==='Escape'){$('q').value='';render();}
});
$('sortbtn').addEventListener('click',()=>{sortMode=(sortMode+1)%SORTS.length;$('sortbtn').textContent='排序：'+SORTS[sortMode][0];render();});
let allOpen=false;
$('expbtn').addEventListener('click',()=>{
  allOpen=!allOpen;$('expbtn').textContent=allOpen?'全部收起':'全部展开';
  document.querySelectorAll('#list .tcard').forEach(c=>setOpen(c,allOpen));
});

/* ---------- footer ---------- */
$('foot').innerHTML=`数据：pg32b @ 192.168.3.32（PostgreSQL 18.6 + PostGIS 3.6.4）· 行数/非空/distinct/高频值均为 <b>count 精确实测</b>（${CFG.gen}）· 说明三档：<span class="lv ok">✓实证</span> 本会话亲验 <span class="lv doc">◈通说</span> 公开文档/名称自明 <span class="lv guess">?推断</span> 仅凭名称猜测 · 关系一律为命名规约<b>推断</b>（库内 0 外键约束）· 源数据 CBDB（Harvard）/ CHGIS V6 / TGaz（学术许可，禁再分发）· <a href="index.html">返回总目</a>`;

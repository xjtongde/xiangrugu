/* 蘇軾 · 行迹与贬谪之路（app_person_journey.js）—— Hartwell 1080 底图 + 除授足迹 + DEM 剖面 */
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

/* ---------- 数据整理 ---------- */
const M=D.main;
const posts=D.post.map((p,i)=>({...p,pi:i}));
const addrPts=D.addr.filter(a=>a.x!=null&&a.y!=null).map((a,i)=>({...a,ai:i}));
const stops=[];                       // 可落图的除授点（按 fy 排序）
posts.forEach(p=>{
  const xy=(p.pxy||[]).find(q=>q&&q.x!=null);
  if(p.fy!=null&&xy){stops.push({...p,x:xy.x,y:xy.y,pn:(xy.n||p.place)});}
});
stops.sort((a,b)=>a.fy-b.fy||a.pi-b.pi);
stops.forEach((s,i)=>s.no=i+1);

/* ---------- KPI ---------- */
$('stats').innerHTML=CFG.stats.map(s=>`<div class="stat"><b>0</b><span>${s[1]}</span></div>`).join('');
[...$('stats').children].forEach((el,i)=>countUp(el.firstChild,CFG.stats[i][0]));

/* ---------- 投影 ---------- */
const VW=1000,VH=700,PAD=18;
let minLon=1e9,maxLon=-1e9,minLat=1e9,maxLat=-1e9;
(function walk(a){if(typeof a[0]==='number'){
    if(a[0]<minLon)minLon=a[0];if(a[0]>maxLon)maxLon=a[0];
    if(a[1]<minLat)minLat=a[1];if(a[1]>maxLat)maxLat=a[1];}
  else a.forEach(walk);})(D.base.map(f=>f.g.coordinates));
const PX=(lon)=>PAD+(lon-minLon)/(maxLon-minLon)*(VW-2*PAD);
const PY=(lat)=>PAD+(maxLat-lat)/(maxLat-minLat)*(VH-2*PAD);

/* ---------- 地图 ---------- */
function ringPath(ring){return 'M'+ring.map(c=>PX(c[0]).toFixed(1)+' '+PY(c[1]).toFixed(1)).join('L')+'Z';}
function facePath(g){
  if(g.type==='Polygon')return g.coordinates.map(ringPath).join('');
  return g.coordinates.map(p=>p.map(ringPath).join('')).join('');
}
const FIX={'務州':'婺州'};   // 与宋人分布图同一处 Hartwell 讹字，仅改显示名
let mapS='';
// 经纬网
mapS+='<g id="ggrat">';
for(let lon=Math.ceil(minLon/5)*5;lon<maxLon;lon+=5)mapS+=`<line class="grat" x1="${PX(lon).toFixed(1)}" y1="${PAD}" x2="${PX(lon).toFixed(1)}" y2="${VH-PAD}"/>`;
for(let lat=Math.ceil(minLat/5)*5;lat<maxLat;lat+=5)mapS+=`<line class="grat" x1="${PAD}" y1="${PY(lat).toFixed(1)}" x2="${VW-PAD}" y2="${PY(lat).toFixed(1)}"/>`;
mapS+='</g>';
// 底图
mapS+='<g id="gbase">';
D.base.forEach(f=>{const n=FIX[f.n]||f.n;
  mapS+=`<path class="mland" fill-rule="evenodd" d="${facePath(f.g)}" data-tip="<b>${esc(n)}</b> · Hartwell 1080 府级面"/>`;});
mapS+='</g>';
// 路线
mapS+='<g id="groute">';
mapS+=`<polyline class="route" points="${stops.map(s=>PX(s.x).toFixed(1)+','+PY(s.y).toFixed(1)).join(' ')}"/>`;
// 编号点（同坐标多任 → 环绕错位）
const byxy={};stops.forEach(s=>{const k=s.x.toFixed(2)+','+s.y.toFixed(2);(byxy[k]=byxy[k]||[]).push(s);});
Object.values(byxy).forEach(list=>list.forEach((s,j)=>{
  const ang=j/list.length*2*Math.PI,rr=list.length>1?13:0;
  s._cx=PX(s.x)+Math.cos(ang)*rr;s._cy=PY(s.y)+Math.sin(ang)*rr;
}));
const ADDRCOL={'出生地':'#d4a24e','籍貫(基本地址)':'#e8e6df','死所':'#c56a5a','葬地':'#9b7fb8','前住地':'#5b8db8','遊歷或曾經到過':'#6fb3a0'};
mapS+='<g id="gaddr">';
addrPts.forEach(a=>{
  const x=PX(a.x),y=PY(a.y),col=ADDRCOL[a.ty]||'#6fb3a0';
  mapS+=`<path class="addrpt" d="M${x.toFixed(1)} ${(y-5).toFixed(1)} L${(x+5).toFixed(1)} ${y.toFixed(1)} L${x.toFixed(1)} ${(y+5).toFixed(1)} L${(x-5).toFixed(1)} ${y.toFixed(1)} Z" fill="${a.ty==='籍貫(基本地址)'?'none':col}" stroke="${col}" stroke-width="1.6" data-tip="<b>${esc(a.n)}</b> · ${esc(a.ty)}${a.y1?'<br>'+a.y1+(a.y2?'–'+a.y2:'')+' 年':''}"/>`;
});
mapS+='</g>';
stops.forEach(s=>{
  mapS+=`<g class="stop" data-pi="${s.pi}" data-tip="<b>#${s.no} ${s.fy}${s.ly&&s.ly>s.fy?'–'+s.ly:'–?'} · ${esc(s.off||'')}</b><br>${esc(s.pn)}${s.appt?' · '+esc(s.appt):''}${s.notes?'<br><span style=\'color:#8b94a3\'>'+esc(s.notes)+'</span>':''}">`+
    `<circle cx="${s._cx.toFixed(1)}" cy="${s._cy.toFixed(1)}" r="9" fill="#d4a24e"/>`+
    `<text x="${s._cx.toFixed(1)}" y="${(s._cy+3.2).toFixed(1)}">${s.no}</text></g>`;
});
mapS+='</g>';
$('mapwrap').insertAdjacentHTML('afterbegin',
  `<svg viewBox="0 0 ${VW} ${VH}" xmlns="http://www.w3.org/2000/svg">${mapS}</svg>`);

/* ---------- 图层开关 ---------- */
const LAYERS=[['groute','除授路线（#编号）','#d4a24e'],['gaddr','地址足迹（菱形）','#6fb3a0'],['gbase','Hartwell 1080 底图','#28313f'],['ggrat','经纬网','#1c232e']];
let layerOn={groute:1,gaddr:1,gbase:1,ggrat:1};
function renderLayers(){
  $('layers').innerHTML=LAYERS.map(([id,label,col])=>`<span class="chip${layerOn[id]?' on':''}" data-l="${id}"><i style="background:${col}"></i>${label}</span>`).join('');
  document.querySelectorAll('#layers .chip').forEach(c=>c.addEventListener('click',()=>{
    const id=c.getAttribute('data-l');layerOn[id]=!layerOn[id];
    const g=document.getElementById(id);if(g)g.style.display=layerOn[id]?'':'none';
    renderLayers();}));
}
renderLayers();

/* ---------- 仕宦年表（联动） ---------- */
(function(){
  const Y0=1034,Y1=1106,W=1180,H=210,L=40,R=16,T=24,B=26;
  const x=y=>L+(y-Y0)/(Y1-Y0)*(W-L-R);
  const withFy=posts.filter(p=>p.fy!=null);
  const lanes=[];
  withFy.forEach(p=>{
    const a=x(p.fy),b=x(Math.max((p.ly&&p.ly>p.fy)?p.ly:p.fy+2));
    let li=0;while(li<lanes.length&&lanes[li].some(s=>a<s[1]+3&&b+3>s[0]))li++;
    (lanes[li]=lanes[li]||[]).push([a,b]);p._l=li;p._a=a;p._b=b;
  });
  let s='';
  for(let y=1040;y<=1100;y+=10){
    s+=`<line x1="${x(y)}" y1="${T-6}" x2="${x(y)}" y2="${H-B+4}" stroke="#2a3342" stroke-width=".8"/>`;
    s+=`<text x="${x(y)}" y="${H-B+18}" text-anchor="middle" font-size="10.5" fill="#8b94a3" font-family="Georgia,serif">${y}</text>`;
  }
  s+=`<line x1="${L}" y1="${H-B}" x2="${W-R}" y2="${H-B}" stroke="#2a3342"/>`;
  s+=`<line x1="${x(M.b)}" y1="${T-10}" x2="${x(M.b)}" y2="${H-B}" stroke="#c56a5a" stroke-dasharray="3 3" opacity=".6"/>`;
  s+=`<line x1="${x(M.d)}" y1="${T-10}" x2="${x(M.d)}" y2="${H-B}" stroke="#c56a5a" stroke-dasharray="3 3" opacity=".6"/>`;
  withFy.forEach(p=>{
    const ly=(p.ly&&p.ly>p.fy)?p.ly:null,y=T+p._l*16,w=Math.max(4,p._b-p._a);
    s+=`<rect class="postbar${ly?'':' open'}" data-pi="${p.pi}" x="${p._a.toFixed(1)}" y="${y}" width="${w.toFixed(1)}" height="10" rx="2" data-tip="<b>${p.fy}${ly?'–'+ly:'–?'} ${esc(p.off||'')}</b> · ${esc(p.place||'[未詳]')}"/>`;
  });
  const svg=$('tlbars');
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`);svg.setAttribute('width',W);
  svg.innerHTML=s;
  svg.querySelectorAll('.postbar').forEach(b=>b.addEventListener('click',()=>selectPost(parseInt(b.getAttribute('data-pi')))));
})();

/* ---------- 除授总表 ---------- */
$('postT').innerHTML=`<tr><th>#</th><th>起</th><th>止</th><th>官职</th><th>任法</th><th>任所</th><th>注</th></tr>`+
  posts.map(p=>{
    const st=stops.find(s=>s.pi===p.pi);
    return `<tr data-pi="${p.pi}"><td class="dim">${st?st.no:'—'}</td><td class="yr">${p.fy??'—'}</td><td class="yr">${(p.ly&&p.ly>0)?p.ly:'—'}</td><td><b>${esc(p.off||'—')}</b></td><td class="dim">${esc(p.appt||'—')}</td><td>${esc(p.place||'[未詳]')}</td><td class="dim" style="max-width:260px">${esc(p.notes||'')}</td></tr>`;}).join('');
document.querySelectorAll('#postT tr[data-pi]').forEach(tr=>tr.addEventListener('click',()=>selectPost(parseInt(tr.getAttribute('data-pi')))));

/* ---------- 三方联动选中 ---------- */
function selectPost(pi){
  document.querySelectorAll('.stop.sel,.postbar.sel,#postT tr.sel').forEach(e=>e.classList.remove('sel'));
  const g=document.querySelector(`.stop[data-pi="${pi}"]`);
  if(g){g.classList.add('sel');if(g.parentNode)g.parentNode.appendChild(g);}   // 选中置顶
  const b=document.querySelector(`.postbar[data-pi="${pi}"]`);if(b)b.classList.add('sel');
  const r=document.querySelector(`#postT tr[data-pi="${pi}"]`);
  if(r){r.classList.add('sel');r.scrollIntoView({block:'nearest'});}
}
document.querySelectorAll('.stop').forEach(g=>g.addEventListener('click',()=>selectPost(parseInt(g.getAttribute('data-pi')))));

/* ---------- DEM 剖面 ---------- */
function hav(lat1,lon1,lat2,lon2){
  const R=6371,t=Math.PI/180;
  const h=Math.sin((lat2-lat1)*t/2)**2+Math.cos(lat1*t)*Math.cos(lat2*t)*Math.sin((lon2-lon1)*t/2)**2;
  return 2*R*Math.asin(Math.sqrt(h));
}
D.dem_legs.forEach(leg=>{
  let km=0;leg.km=[0];
  for(let i=1;i<leg.pts.length;i++){
    const a=leg.pts[i-1],b=leg.pts[i];
    km+=hav(a.lat,a.lon,b.lat,b.lon);leg.km.push(km);
  }
  leg.total=km;
  leg.max=Math.max(...leg.pts.filter(p=>p.elev!=null).map(p=>p.elev));
  leg.sea=leg.pts.filter(p=>p.elev!=null&&p.elev<=25).length;
});
let curLeg=0;
function renderTabs(){
  $('dempick').innerHTML=D.dem_legs.map((l,i)=>`<span class="dtab${i===curLeg?' on':''}" data-i="${i}">${esc(l.label)}</span>`).join('');
  document.querySelectorAll('.dtab').forEach(t=>t.addEventListener('click',()=>{curLeg=parseInt(t.getAttribute('data-i'));renderTabs();renderDem();}));
}
function renderDem(){
  const leg=D.dem_legs[curLeg],pts=leg.pts;
  const W=1160,H=300,L=44,R=14,T=16,B=34;
  const X=km=>L+km/leg.total*(W-L-R);
  const ymax=Math.max(100,Math.ceil(leg.max/250)*250+60);
  const Y=e=>T+(1-e/ymax)*(H-T-B);
  let s=`<defs><linearGradient id="demgrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6fb3a0" stop-opacity=".55"/><stop offset="1" stop-color="#6fb3a0" stop-opacity=".05"/></linearGradient></defs>`;
  for(let g=0;g<=ymax;g+=g===0?500:500){
    if(g>ymax)break;
    s+=`<line class="daxis" x1="${L}" y1="${Y(g).toFixed(1)}" x2="${W-R}" y2="${Y(g).toFixed(1)}" ${g===0?'stroke-width="1.2"':'stroke-dasharray="2 4"'}/>`;
    s+=`<text class="dtxt" x="${L-6}" y="${(Y(g)+3).toFixed(1)}" text-anchor="end">${g}m</text>`;
  }
  const xt=Math.ceil(leg.total/6/50)*50;
  for(let k=0;k<=leg.total;k+=xt){
    s+=`<line class="daxis" x1="${X(k).toFixed(1)}" y1="${T}" x2="${X(k).toFixed(1)}" y2="${H-B}" stroke-dasharray="2 4" opacity=".4"/>`;
    s+=`<text class="dtxt" x="${X(k).toFixed(1)}" y="${H-B+16}" text-anchor="middle">${Math.round(k)}km</text>`;
  }
  // 分段（null 断开）
  let seg=[],segs=[];
  pts.forEach((p,i)=>{if(p.elev!=null){seg.push(i);}else if(seg.length){segs.push(seg);seg=[];}});
  if(seg.length)segs.push(seg);
  segs.forEach(sg=>{
    const line=sg.map(i=>`${X(leg.km[i]).toFixed(1)} ${Y(pts[i].elev).toFixed(1)}`).join('L');
    s+=`<path class="darea" d="M${X(leg.km[sg[0]]).toFixed(1)} ${Y(0).toFixed(1)} L${line} L${X(leg.km[sg[sg.length-1]]).toFixed(1)} ${Y(0).toFixed(1)} Z"/>`;
    s+=`<path class="dline" d="M${line}"/>`;
  });
  s+=`<text class="dtxt" x="${L}" y="${T-4}" fill="#d4a24e" font-size="11">${esc(leg.a)} → ${esc(leg.b)} · ${esc(leg.label)}</text>`;
  s+=`<line id="dcross" class="dcross" x1="0" y1="${T}" x2="0" y2="${H-B}" style="display:none"/>`;
  s+=`<circle id="cdot" r="3.4" fill="#d4a24e" stroke="#0e1116" style="display:none"/>`;
  const svg=$('dem');
  svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
  svg.innerHTML=s;
  const mx=svg.querySelector('#dcross'),md=svg.querySelector('#cdot');
  svg.onmousemove=e=>{
    const r=svg.getBoundingClientRect();
    const px=(e.clientX-r.left)/r.width*W;
    let bi=0,bd=1e9;
    pts.forEach((p,i)=>{const d=Math.abs(X(leg.km[i])-px);if(d<bd){bd=d;bi=i;}});
    const p=pts[bi];
    mx.setAttribute('x1',X(leg.km[bi]));mx.setAttribute('x2',X(leg.km[bi]));mx.style.display='';
    if(p.elev!=null){md.setAttribute('cx',X(leg.km[bi]));md.setAttribute('cy',Y(p.elev));md.style.display='';}else md.style.display='none';
    tip.style.display='block';
    tip.innerHTML=`<b>${Math.round(leg.km[bi])} km</b> · 高程 ${p.elev!=null?Math.round(p.elev)+' m':'无数据'}<br><span style="color:#8b94a3">${p.lon.toFixed(3)}, ${p.lat.toFixed(3)} · 采样点 ${bi}/100</span>`;
    tip.style.left=Math.min(innerWidth-300,e.clientX+12)+'px';tip.style.top=(e.clientY+14)+'px';
  };
  svg.onmouseleave=()=>{mx.style.display='none';md.style.display='none';tip.style.display='none';};
  $('demmeta').innerHTML=`<span>里程（直线） <b>${Math.round(leg.total)} km</b></span><span>最高 <b>${Math.round(leg.max)} m</b></span>`+
    (leg.sea?`<span>≤25m 低点 <b>${leg.sea}</b> 个${curLeg===3?'（琼州海峡两岸及沿海）':''}</span>`:'')+
    `<span class="small">数据：chgis.dem（3,358 幅 ~1km 栅格 · ST_Value 逐点取值 · SRID 4326）</span>`;
}
renderTabs();renderDem();

/* ---------- 诚实账 ---------- */
const noFy=posts.filter(p=>p.fy==null).length;
const undet=posts.filter(p=>!p.place||p.place.includes('未詳')).length;
const addrNoXY=D.addr.length-addrPts.length;
$('honest').innerHTML=`
 <li><b>生年两说并存</b>：biog_main 作 ${M.b}，出生地地址记录作 ${M.b+1}（史界通说 1037-01-08，即景祐三年十二月十九，公历已跨年）。本页不加裁决，两处均照录。</li>
 <li><b>库内原样</b>：除授 ${posts.length} 段中 ${noFy} 段无首任年（表内「—」）、${undet} 段任所为 [未詳]；地址 ${D.addr.length} 条中 ${addrNoXY} 条无坐标，均不入图、如实列示。</li>
 <li><b>剖面为直线采样</b>：起终点取 addr_codes 官方坐标连直线，每段 101 点；史实路线多沿江海水路（如出蜀走岷江—长江），里程与爬升仅供地形感知，不作路线考证。</li>
 <li><b>DEM 无海深</b>：chgis.dem 为陆地高程栅格，琼州海峡段呈现为近岸低值（4–40m）而非海深；「渡海」在数据里是一段贴地的低谷。</li>
 <li><b>底图时点</b>：Hartwell 1080 为单年快照，苏轼一生（1037–1101）政区屡有置废改名，底图仅作地理参照；「務州→婺州」讹字沿用宋人分布图同一处校勘（仅改显示名）。</li>
 <li><b>社交地点缺席</b>：他 1,033 条交往记录的 c_addr_id 全部为 [未詳]（0 坐标），故本页无「交往地点」图层——数据没有的，图上不画。</li>`;

$('foot').innerHTML=`数据：pg32b @ 192.168.3.32 · posted_to_office_data×posting_data×posted_to_addr_data（35 段）· biog_addr_data（31 条）· addr_codes 坐标 · hartwell_pref_pgn@1080（303 面底图）· chgis.dem ST_Value 剖面（4 段×101 点）· 实测于 ${CFG.gen} · 管线：extract_person.py（personid=${M.id}）→ build_person.py · CBDB（Harvard）/CHGIS 学术使用许可，禁再分发 · <a href="index.html" style="color:var(--gold)">全景</a> · <a href="network.html" style="color:var(--gold)">社交网络</a>`;

/* 蘇軾 · 社交网络（app_person_network.js）—— assoc_data 1,033 条全量，力导向星型图＋同类花瓣聚簇 */
const $=id=>document.getElementById(id);
const fmt=n=>(n??0).toLocaleString('en-US');
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const now=()=>(typeof performance!=='undefined'&&performance.now)?performance.now():Date.now();
const tip=$('tip');
document.addEventListener('mousemove',e=>{const t=e.target.closest&&e.target.closest('[data-tip]');
  if(t){tip.style.display='block';tip.innerHTML=t.getAttribute('data-tip');
    tip.style.left=Math.min(innerWidth-340,e.clientX+12)+'px';tip.style.top=(e.clientY+14)+'px';}
  else tip.style.display='none';});
function countUp(el,to,dur=950){const t0=now();
  function f(){const p=Math.min(1,(now()-t0)/dur),e=1-Math.pow(1-p,3);
    el.textContent=fmt(Math.round(to*e));if(p<1)requestAnimationFrame(f);}
  requestAnimationFrame(f);}

const DEATH=D.main.d;            // 1101
const PALETTE=['#6fb3a0','#d4a24e','#5b8db8','#c56a5a','#9b7fb8','#5aa8b8','#a8a05a','#c89b6a','#8fbc8f','#b8789b','#6a9fb5','#7a8ca0','#d4b48e','#79a88a','#a08cc0'];

/* ---------- 聚合 ---------- */
const P=new Map();               // pid -> {pid,n,w,recs,tys:{},y1min,y1max,post}
D.assoc.forEach(a=>{
  if(a.pid==null)return;
  let p=P.get(a.pid);
  if(!p){p={pid:a.pid,n:a.n||('id'+a.pid),w:0,recs:[],tys:{},y1min:null,y1max:null,post:false};P.set(a.pid,p);}
  p.w++;p.recs.push(a);
  const ty=a.ty||'未分类';p.tys[ty]=(p.tys[ty]||0)+1;
  if(a.y1&&a.y1>0){p.y1min=p.y1min==null?a.y1:Math.min(p.y1min,a.y1);p.y1max=p.y1max==null?a.y1:Math.max(p.y1max,a.y1);
    if(a.y1>DEATH)p.post=true;}
});
const partners=[...P.values()];
partners.forEach(p=>{p.ty=Object.keys(p.tys).sort((a,b)=>p.tys[b]-p.tys[a])[0];});
const PB={};(D.pbirth||[]).forEach(x=>{if(x&&x.pid!=null&&x.b)PB[x.pid]=x.b;});
partners.forEach(p=>{p.born=PB[p.pid];if(p.born&&p.born>DEATH)p.post=true;});
const TYCNT={};D.assoc.forEach(a=>{const t=a.ty||'未分类';TYCNT[t]=(TYCNT[t]||0)+1;});
const TYS=Object.keys(TYCNT).sort((a,b)=>TYCNT[b]-TYCNT[a]);
const TYCOL={};TYS.forEach((t,i)=>TYCOL[t]=PALETTE[i%PALETTE.length]);
const dated=D.assoc.filter(a=>a.y1&&a.y1>0).length;
const posth=D.assoc.filter(a=>a.y1&&a.y1>DEATH).length;
const aliveD=dated-posth;

/* ---------- KPI ---------- */
const uniq=partners.length,heavy=partners.filter(p=>p.w>=5).length,posthP=partners.filter(p=>p.post).length;
$('stats').innerHTML=CFG.stats.map(s=>`<div class="stat"><b>0</b><span>${s[1]}</span></div>`).join('');
[...$('stats').children].forEach((el,i)=>countUp(el.firstChild,CFG.stats[i][0]));

/* ---------- 力导向 ---------- */
const cv=$('graph'),ctx=cv.getContext('2d');
let W=1100,H=600,DPR=1,ox=0,oy=0,alpha=1,selId=null,hov=null,drag=null,pan=null;
const ego={pid:D.main.id,n:D.main.nm,w:0,ego:true,ty:'—'};
let nodes=[],vis=[];
function sizeCanvas(){
  DPR=(typeof devicePixelRatio!=='undefined')?devicePixelRatio:1;
  W=cv.clientWidth||1100;H=cv.clientHeight||600;
  cv.width=W*DPR;cv.height=H*DPR;
  ctx.setTransform(DPR,0,0,DPR,0,0);
}
function layout(){
  sizeCanvas();
  const cx=W/2,cy=H/2;
  ego.x=cx;ego.y=cy;ego.vx=0;ego.vy=0;
  partners.forEach((p,i)=>{
    const a=i/partners.length*Math.PI*2,r=90+Math.sqrt(i)*13;
    p.x=cx+Math.cos(a)*r;p.y=cy+Math.sin(a)*r;p.vx=0;p.vy=0;
    p.r=2.6+Math.sqrt(p.w)*1.5;
    p.postOnly=p.post&&!(p.y1min!=null&&p.y1min<=DEATH);
  });
  ego.r=13;
  nodes=[ego,...partners];
  applyFilter();
}
let activeTy=null;
function applyFilter(){
  vis=activeTy?partners.filter(p=>p.tys[activeTy]):partners;
  alpha=Math.max(alpha,.55);kick();
  renderChips();
}
let running=false;
function kick(){if(!running){running=true;requestAnimationFrame(step);}}
function step(){
  if(alpha>0.004||drag){
    const cx=W/2,cy=H/2;
    // 同类质心（花瓣）
    const cen={};vis.forEach(p=>{const c=cen[p.ty]=cen[p.ty]||[0,0,0];c[0]+=p.x;c[1]+=p.y;c[2]++;});
    for(const k in cen){cen[k][0]/=cen[k][2];cen[k][1]/=cen[k][2];}
    // 斥力 O(N²)
    for(let i=0;i<vis.length;i++){
      const a=vis[i];
      for(let j=i+1;j<vis.length;j++){
        const b=vis[j];let dx=b.x-a.x,dy=b.y-a.y,d2=dx*dx+dy*dy;
        if(d2<1){dx=Math.random()-.5;dy=Math.random()-.5;d2=1;}
        if(d2>160000)continue;
        const f=Math.min(2600/d2,3.2)*alpha,dd=Math.sqrt(d2);
        const fx=dx/dd*f,fy=dy/dd*f;
        a.vx-=fx;a.vy-=fy;b.vx+=fx;b.vy+=fy;
      }
      // ego 弹簧
      const dx=a.x-ego.x,dy=a.y-ego.y,dd=Math.max(1,Math.sqrt(dx*dx+dy*dy));
      const rest=70+340/(a.w+5),f=(dd-rest)*0.0055*alpha;
      a.vx-=dx/dd*f;a.vy-=dy/dd*f;
      ego.vx+=dx/dd*f*.12;ego.vy+=dy/dd*f*.12;
      // 花瓣质心
      const c=cen[a.ty];
      if(c){a.vx+=(c[0]-a.x)*0.0016*alpha;a.vy+=(c[1]-a.y)*0.0016*alpha;}
      // 向心
      a.vx+=(cx-a.x)*0.0009*alpha;a.vy+=(cy-a.y)*0.0009*alpha;
    }
    for(const p of vis){if(p!==drag){p.x+=p.vx;p.y+=p.vy;p.vx*=.82;p.vy*=.82;}
      p.x=Math.max(8,Math.min(W-8,p.x));p.y=Math.max(8,Math.min(H-8,p.y));}
    ego.vx+=(cx-ego.x)*0.004*alpha;ego.vy+=(cy-ego.y)*0.004*alpha;
    ego.x+=ego.vx*.35;ego.y+=ego.vy*.35;ego.vx*=.6;ego.vy*=.6;
    alpha*=0.99;
    draw();
    requestAnimationFrame(step);
  }else{running=false;draw();}
}
function draw(){
  ctx.clearRect(0,0,W,H);
  ctx.save();ctx.translate(ox,oy);
  const selP=selId!=null?P.get(selId):null;
  // 边
  vis.forEach(p=>{
    const isSel=p===selP;
    ctx.beginPath();ctx.moveTo(ego.x,ego.y);ctx.lineTo(p.x,p.y);
    ctx.strokeStyle=isSel?'rgba(212,162,78,.85)':p.post?'rgba(155,127,184,.34)':p.y1min!=null?'rgba(111,179,160,.24)':'rgba(139,148,163,.12)';
    ctx.lineWidth=isSel?Math.min(3.4,.9+p.w*.09):Math.min(2.2,.4+p.w*.07);
    ctx.stroke();
  });
  // 节点
  vis.forEach(p=>{
    const dim=selP&&p!==selP;
    ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,7);
    ctx.fillStyle=(p.post?'#9b7fb8':TYCOL[p.ty]||'#8b94a3');
    ctx.globalAlpha=dim?.28:1;ctx.fill();ctx.globalAlpha=1;
    if(p===selP||p===hov){ctx.strokeStyle='#fff';ctx.lineWidth=1.6;ctx.stroke();}
    if(p.r>=8.5||p===selP||p===hov){
      ctx.font='10px "Songti SC",serif';ctx.fillStyle=dim?'rgba(232,230,223,.3)':'#e8e6df';
      ctx.textAlign='center';ctx.fillText(p.n,p.x,p.y-p.r-4);
    }
  });
  // ego
  ctx.beginPath();ctx.arc(ego.x,ego.y,ego.r+4,0,7);ctx.fillStyle='rgba(212,162,78,.16)';ctx.fill();
  ctx.beginPath();ctx.arc(ego.x,ego.y,ego.r,0,7);ctx.fillStyle='#d4a24e';ctx.fill();
  ctx.strokeStyle='#0e1116';ctx.lineWidth=2;ctx.stroke();
  ctx.font='600 13px "Songti SC",serif';ctx.fillStyle='#d4a24e';ctx.textAlign='center';
  ctx.fillText(ego.n,ego.x,ego.y-ego.r-8);
  ctx.restore();
}
function pick(mx,my){
  const x=mx-ox,y=my-oy;
  let best=null,bd=1e9;
  for(const p of vis){const dx=p.x-x,dy=p.y-y,d=dx*dx+dy*dy;
    const rr=(p.r+5)*(p.r+5);if(d<rr&&d<bd){bd=d;best=p;}}
  const dx=ego.x-x,dy=ego.y-y;
  if(dx*dx+dy*dy<(ego.r+5)*(ego.r+5))return ego;
  return best;
}
cv.addEventListener('mousemove',e=>{
  const r=cv.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
  if(drag){drag.x=mx-ox;drag.y=my-oy;drag.vx=0;drag.vy=0;alpha=Math.max(alpha,.12);kick();return;}
  if(pan){ox=pan.ox+(mx-pan.mx);oy=pan.oy+(my-pan.my);draw();return;}
  hov=pick(mx,my);
  cv.style.cursor=hov?'pointer':'grab';
  if(hov&&!hov.ego){
    tip.style.display='block';
    tip.innerHTML=`<b>${esc(hov.n)}</b> · ${hov.w} 条记录${hov.born?`<br>生于 ${hov.born}${hov.post?' <span style="color:#9b7fb8">（身后追慕）</span>':''}`:''}<br>主要：${esc(hov.ty)}${hov.y1min!=null?` · 年份 ${hov.y1min}${hov.y1max>hov.y1min?'–'+hov.y1max:''}`:' · 记录无年份'}<br><span style="color:#8b94a3">点击查看全部往来</span>`;
    tip.style.left=Math.min(innerWidth-340,e.clientX+12)+'px';tip.style.top=(e.clientY+14)+'px';
  }else if(hov&&hov.ego){
    tip.style.display='block';tip.innerHTML='<b>蘇軾</b> · 本尊（全库社交第二中心）';
    tip.style.left=e.clientX+12+'px';tip.style.top=(e.clientY+14)+'px';
  }else tip.style.display='none';
});
let dragMoved=false;
cv.addEventListener('mousedown',e=>{
  const r=cv.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
  dragMoved=false;
  const p=pick(mx,my);
  if(p){drag=p;alpha=Math.max(alpha,.1);kick();}
  else pan={mx,my,ox,oy};
  cv.classList.add('drag');
  e.preventDefault();
});
document.addEventListener('mouseup',()=>{drag=null;pan=null;cv.classList.remove('drag');});
cv.addEventListener('mousemove',()=>{if(drag||pan)dragMoved=true;});
cv.addEventListener('click',e=>{
  if(dragMoved)return;
  const r=cv.getBoundingClientRect();
  const p=pick(e.clientX-r.left,e.clientY-r.top);
  if(!p)select(null);else if(!p.ego)select(p.pid);
});
function select(pid){
  selId=pid;
  const box=$('sel');
  if(pid==null){box.style.display='none';return;}
  const p=P.get(pid);if(!p){box.style.display='none';return;}
  $('seln').textContent=p.n;
  $('selc').innerHTML=`${p.w} 条 · ${Object.keys(p.tys).map(t=>`${esc(t)}×${p.tys[t]}`).join(' / ')}${p.post?` · <span style="color:#9b7fb8">身后追慕（生于 ${p.born}）</span>`:p.born?` · 生于 ${p.born}`:''} · pid ${p.pid}`;
  const recs=[...p.recs].sort((a,b)=>(a.y1||9999)-(b.y1||9999));
  $('selr').innerHTML=recs.map(r=>`<div class="rec"><div class="r1">${esc(r.rel||'')}${r.y1?` <span class="yrs" style="color:var(--jade)">${r.y1}${r.y2&&r.y2!==r.y1?'–'+r.y2:''}</span>`:''}</div>`+
    `${r.txt||r.occas||r.genre||r.via_kin?`<div class="r2">${[r.txt&&('题《'+esc(r.txt)+'》'),r.occas&&('场合:'+esc(r.occas)),r.genre&&('文体:'+esc(r.genre)),r.via_kin&&('经由亲缘:'+esc(r.via_kin))].filter(Boolean).join(' · ')}</div>`:''}</div>`).join('');
  box.style.display='block';
}
$('selx').addEventListener('click',()=>select(null));
if(typeof window!=='undefined'&&window.addEventListener)
  window.addEventListener('resize',()=>{const oW=W;sizeCanvas();ox+=(W-oW)/2;alpha=Math.max(alpha,.1);kick();});

/* ---------- 大类 chips ---------- */
function renderChips(){
  $('tychips').innerHTML=`<span class="chip${activeTy?'':' on'}" data-ty="">全部 <b>${fmt(D.assoc.length)}</b></span>`+
    TYS.map(t=>`<span class="chip${activeTy===t?' on':''}" data-ty="${esc(t)}"><i style="background:${TYCOL[t]}"></i>${esc(t)} <b>${TYCNT[t]}</b></span>`).join('');
  document.querySelectorAll('#tychips .chip').forEach(c=>c.addEventListener('click',()=>{
    const t=c.getAttribute('data-ty');activeTy=(t==='')?null:(activeTy===t?null:t);applyFilter();
    renderTybars();
  }));
}
function renderTybars(){
  const list=activeTy?TYS.filter(t=>t===activeTy):TYS;
  const mx=Math.max(...list.map(t=>TYCNT[t]),1);
  $('tybars').innerHTML=list.map(t=>`<div class="bar" data-ty="${esc(t)}" data-tip="点击筛选「${esc(t)}」"><span class="n">${esc(t)}</span><span class="b"><i style="width:${(TYCNT[t]/mx*100).toFixed(1)}%;background:${TYCOL[t]}"></i></span><span class="v">${TYCNT[t]}</span></div>`).join('');
  document.querySelectorAll('#tybars .bar').forEach(b=>b.addEventListener('click',()=>{
    const t=b.getAttribute('data-ty');activeTy=(activeTy===t)?null:t;applyFilter();renderTybars();}));
}
/* ---------- Top20 ---------- */
(function(){
  const top=[...partners].sort((a,b)=>b.w-a.w).slice(0,20);
  const mx=top[0].w;
  $('topbars').innerHTML=top.map(p=>`<div class="bar" data-pid="${p.pid}" data-tip="${esc(p.n)} · ${p.w} 条 · ${esc(p.ty)}${p.post?' · 身后追慕':''}"><span class="n">${esc(p.n)}</span><span class="b"><i style="width:${(p.w/mx*100).toFixed(1)}%"></i></span><span class="v">${p.w}</span></div>`).join('');
  document.querySelectorAll('#topbars .bar').forEach(b=>b.addEventListener('click',()=>select(parseInt(b.getAttribute('data-pid')))));
})();
/* ---------- 年份直方图 ---------- */
(function(){
  const ys=D.assoc.filter(a=>a.y1&&a.y1>0).map(a=>a.y1);
  const y0=Math.floor(Math.min(...ys)/5)*5,y1=Math.ceil(Math.max(...ys)/5)*5;
  const nb=(y1-y0)/5,bk=Array.from({length:nb},()=>[0,0]);
  ys.forEach(y=>{const i=Math.min(nb-1,(y-y0)/5|0);bk[i][y>DEATH?1:0]++;});
  const mx=Math.max(...bk.map(b=>b[0]+b[1]),1);
  $('hist').innerHTML=bk.map((b,i)=>{
    const tot=b[0]+b[1],hp=(tot/mx*100).toFixed(1),ap=(b[0]/Math.max(tot,1)*100).toFixed(0);
    return `<div class="hb" data-tip="${y0+i*5}–${y0+i*5+4}：在世 ${b[0]} · 身后 ${b[1]}"><div class="p" style="height:0"></div><div class="l" style="height:${hp}%"><div class="p" style="height:${100-ap}%"></div></div></div>`;}).join('');
  $('haxis').innerHTML=bk.map((b,i)=>`<span>${(y0+i*5)%20===0?(y0+i*5):''}</span>`).join('');
  const negN=D.assoc.filter(a=>a.y1&&a.y1<=0).length,nulN=D.assoc.filter(a=>!a.y1).length;
  $('histnote').innerHTML=`未入图者 <b style="color:var(--gold)">${fmt(negN+nulN)}</b> 条——CBDB 以 <b>-1</b> 记「未详」${fmt(negN)} 条、留空 ${fmt(nulN)} 条；真正系年者仅 <b>${fmt(dated)}</b> 条（${Math.min(...ys)}–${Math.max(...ys)}），<b>无一晚于 ${DEATH}</b>。身后经典化藏在伙伴生年里：${fmt(uniq)} 人中 <b style="color:#9b7fb8">${CFG.stats[3][0]} 人生于他死后</b>（周必大 1126 · 陸游 1125 · 魏了翁 1178 · 劉克莊 · 樓鑰，下及元代的袁桷、王惲），留下 <b style="color:#9b7fb8">${CFG.stats[4][0]} 条</b>序跋记咏——网络图中紫色节点即是。`;
})();
renderTybars();
layout();
$('foot').innerHTML=`数据：pg32b cbdb 库 assoc_data（c_personid=3767 全量 ${fmt(D.assoc.length)} 条，join assoc_codes/assoc_types/biog_main/occasion_codes/literarygenre_codes/kinship_codes）＋ 伙伴生卒年（biog_main）· 实测于 ${CFG.gen} · 「身后」判据＝伙伴生年＞${DEATH} 或记录年份＞卒年 · 关系为 CBDB 原码原样（含「黨魁為Y」等原文） · 学术使用许可，禁再分发 · <a href="index.html" style="color:var(--gold)">全景</a> · <a href="journey.html" style="color:var(--gold)">行迹</a>`;

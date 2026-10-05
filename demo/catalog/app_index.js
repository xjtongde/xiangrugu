/* pg32b 数据总目 · index 逻辑（无外部依赖） */
const $=id=>document.getElementById(id);
const fmt=n=>(n??0).toLocaleString('en-US');
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const now=()=>(typeof performance!=='undefined'&&performance.now)?performance.now():Date.now();
const tip=$('tip');
document.addEventListener('mousemove',e=>{const t=e.target.closest&&e.target.closest('[data-tip]');
  if(t){tip.style.display='block';tip.innerHTML=t.getAttribute('data-tip');
    tip.style.left=Math.min(innerWidth-360,e.clientX+12)+'px';tip.style.top=(e.clientY+14)+'px';}
  else tip.style.display='none';});
function countUp(el,to,dur=1000){const t0=now();
  function f(){const p=Math.min(1,(now()-t0)/dur),e=1-Math.pow(1-p,3);
    el.textContent=fmt(Math.round(to*e));if(p<1)requestAnimationFrame(f);}
  requestAnimationFrame(f);}

$('gen').textContent=DATA.gen;
$('stats').innerHTML=DATA.stats.map(s=>`<div class="stat"><b>0</b><span>${s[1]}</span></div>`).join('');
[...$('stats').children].forEach((el,i)=>countUp(el.firstChild,DATA.stats[i][0]));

const PALETTE=['#d4a24e','#6fb3a0','#5b8db8','#c56a5a','#9b7fb8','#5aa8b8','#a8a05a','#c89b6a'];
$('schemas').innerHTML=DATA.schemas.map((s,i)=>{
  const maxr=Math.max(...s.fams.map(f=>f[2]),1);
  return `<a class="scard" href="${s.href}" style="text-decoration:none;color:inherit">
   <span class="tag" style="background:${s.col||PALETTE[i%8]}">${esc(s.sc)}</span>
   <h3>${s.title}</h3>
   <div class="d">${s.d}</div>
   <div class="nums">
     <div><b>${fmt(s.tables)}</b><span>表</span></div>
     <div><b>${fmt(s.rows)}</b><span>行（实测）</span></div>
     <div><b>${fmt(s.cols)}</b><span>列</span></div>
   </div>
   <div class="fam">${s.fams.map((f,j)=>`<div class="frow"><span class="fn">${esc(f[0])}</span><span class="fb"><i style="width:${Math.max(2,f[2]/maxr*100)}%;background:${PALETTE[j%8]}"></i></span><b>${fmt(f[2])}</b></div>`).join('')}</div>
   <div class="reps">${s.reps.map(r=>`<span class="rep" data-tip="${esc(r[2]||'')} · ${fmt(r[1])} 行">${esc(r[0])}</span>`).join('')}</div>
   <span class="go">进入全目 →</span>
  </a>`;}).join('');

$('demos').innerHTML=DATA.demos.map(d=>`<a class="dcard" href="${d.href}"><div class="k">${esc(d.k)}</div><h4>${esc(d.title)}</h4><p>${d.d}</p></a>`).join('');

if(typeof IntersectionObserver!=='undefined'){
  const io=new IntersectionObserver(es=>{es.forEach((e,k)=>{if(e.isIntersecting){setTimeout(()=>e.target.classList.add('in'),k*60);io.unobserve(e.target);}})},{rootMargin:'60px'});
  document.querySelectorAll('.stat,.scard,.dcard').forEach(el=>io.observe(el));
}else document.querySelectorAll('.stat,.scard,.dcard').forEach(el=>el.classList.add('in'));

$('foot').innerHTML=`pg32b @ 192.168.3.32 · PostgreSQL 18.6 + PostGIS 3.6.4 · cbdb 库（public / chgis / harv / ogr_system_tables 四 schema）· 全部数字 count(*) 实测于 ${DATA.gen} · 源数据：CBDB（Harvard）· CHGIS V6 · Hartwell · TGaz（学术使用许可，禁再分发）· 构建管线：extract_catalog.py → catalog.json → build_catalog.py`;

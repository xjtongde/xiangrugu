import json,collections,subprocess
REL="datamgmt/contracts/releases/2026-10-06-bootstrap/import-package"
def show(p): return json.loads(subprocess.check_output(["git","show",f"2273529:{p}"]))
inv=json.load(open("a03-r25-inv.json"))["entries"]
invidx={(e["relative_path"],json.dumps(e.get("archive_chain"),sort_keys=True),json.dumps(e.get("archive_ordinals"))):e for e in inv}
bykp=collections.defaultdict(list)
for k,e in invidx.items(): bykp[(k[0],k[1])].append(k)
G=show(f"{REL}/spatial/groups.json")["groups"]
gidx={}
for g in G:
    loc=g["location"]; outer=loc["outer_relative_path"]; cc=loc.get("container_chain") or []
    for mm in g["members"]:
        hits=[kk for kk in bykp.get((outer,json.dumps(cc+[mm["leaf"]],sort_keys=True)),[]) if invidx[kk]["sha256"]==mm["sha256_inventory"]]
        if len(hits)==1: gidx[mm["member_key"]]=hits[0]
gid2grp={g["group_id"]:g for g in G if "group_id" in g}
def resolve(rp,ch,ordv=None,sha=None):
    if rp is None: return None
    cj=json.dumps(ch,sort_keys=True)
    if ordv is not None:
        k=(rp,cj,json.dumps(ordv))
        if k in invidx and (sha is None or invidx[k]["sha256"]==sha): return k
    hits=[kk for kk in bykp.get((rp,cj),[]) if sha is None or invidx[kk]["sha256"]==sha]
    return hits[0] if len(set(hits))==1 else None
res=collections.Counter(); unres=[]; srcs=set()
tb=show(f"{REL}/tabular/object-mapping.json")
for o in tb["objects"]+tb["proposed_objects"]:
    res["tab"]+=1
    sfc=o["source_file_or_chain"]; rp,_,rest=sfc.partition("!"); si=o.get("source_identity") or {}
    segs=rest.split("/") if rest else []
    cands=[[ "/".join(segs[:-1]),segs[-1]] if len(segs)>1 else segs.copy(), segs.copy(), [rest] if rest else [], [segs[-1]] if segs else []]
    k=None
    for ch in cands:
        k=resolve(rp,ch,None,si.get("sha256") if isinstance(si,dict) else None)
        if k: break
    if k is None: unres.append(("tab",sfc[:85]))
    else: srcs.add(k)
cb=show(f"{REL}/cbdb/table-mapping.json")
for t in cb["tables"]:
    res["cbdb"]+=1
    si=t["source_identity"]
    k=resolve(si.get("carrier_file"),si.get("carrier_archive_chain") or [],si.get("carrier_archive_ordinals") or [],si.get("carrier_sha256"))
    if k is None: unres.append(("cbdb",si.get("carrier_file")))
    else: srcs.add(k)
sp=show(f"{REL}/spatial/object-mapping.json")
for o in sp["proposed_objects"]:
    res["sp-prop"]+=1
    pm=o.get("primary_member")
    k=gidx.get(pm) if isinstance(pm,str) else None
    if k is None and o.get("group_id"):
        g=gid2grp.get(o["group_id"])
        if g:
            ks=[gidx.get(mm["member_key"]) for mm in g["members"] if mm["member_key"] in gidx]
            k=ks[0] if ks else None
    if k is None: unres.append(("sp-prop",str(pm)[:60]))
    else: srcs.add(k)
for a in sp["approved_objects_verbatim"]:
    res["sp-app"]+=1
    o=a.get("object") or a
    ok=False
    for c in o.get("components") or []:
        sel=c.get("selector") or {}
        k=resolve(sel.get("relative_path"),sel.get("archive_chain") or [],sel.get("archive_ordinals"),c.get("raw_sha256"))
        if k: ok=True; srcs.add(k)
    if not ok: unres.append(("sp-app",o.get("object_name")))
md=show(f"{REL}/mdb-sql/object-mapping.json")
for o in md["proposed_objects"]:
    res["mdb"]+=1
    sfc=o.get("source_file_or_chain") or ""; si=o.get("source_identity") or {}
    parts=sfc.split("!"); rp=parts[0]; rest=parts[1:]
    cands=[]
    if not rest: cands=[[]]
    elif len(rest)==1:
        segs=rest[0].split("/")
        if len(segs)==1: cands=[[segs[0]]]
        else: cands+=[[ "/".join(segs[:-1]),segs[-1]],segs,[segs[-1]]]
    else:
        mid="/".join(rest[:-1]); leaf=rest[-1]
        cands+=[[mid,leaf],list(rest),[leaf]]
    k=None
    for ch in cands:
        k=resolve(rp,ch,None,si.get("sha256"))
        if k: break
    if k is None: unres.append(("mdb",sfc[:85]))
    else: srcs.add(k)
r5=show(f"{REL}/raster-other/raster-mapping.json")
for o in r5["proposed_objects"]:
    res["raster"]+=1
    i=o["identity"]
    k=resolve(i["relative_path"],i.get("archive_chain"),i.get("archive_ordinals"),i.get("sha256"))
    if k is None: unres.append(("raster",i["relative_path"][-40:]))
    else: srcs.add(k)
print("counters:",dict(res),"TOTAL objects:",sum(res.values()))
print("UNRESOLVED:",len(unres)); [print(" U:",u) for u in unres[:8]]
print("distinct source members covered:",len(srcs))
# naming classification
nm=collections.Counter()
for o in tb["objects"]+tb["proposed_objects"]: nm[("tabular",bool(o.get("candidate_table_name")),bool(o.get("target_schema")))]+=1
for o in sp["proposed_objects"]: nm[("spatial-proposed",bool(o.get("candidate_table_name")),bool(o.get("dataset_namespace")))]+=1
for a in sp["approved_objects_verbatim"]: nm[("spatial-approved",True,True)]+=1
for t in cb["tables"]: nm[("cbdb",bool(t.get("target_table")),bool(t.get("target_schema")))]+=1
for o in md["proposed_objects"]: nm[("mdb",bool(o.get("table_name_proposal")),bool(o.get("target_schema")))]+=1
for o in r5["proposed_objects"]:
    tp=o.get("target_proposal") or {}
    nm[("raster",bool(tp.get("table_name")),bool(tp.get("schema")))]+=1
for k,v in sorted(nm.items(),key=str): print("NAMING:",k,v)
allprop=[]
for o in tb["objects"]+tb["proposed_objects"]: allprop.append((o.get("target_schema"),o.get("candidate_table_name")))
for o in sp["proposed_objects"]: allprop.append((o.get("target_schema"),o.get("candidate_table_name")))
for t in cb["tables"]: allprop.append((t.get("target_schema"),t.get("target_table")))
for o in md["proposed_objects"]: allprop.append((o.get("target_schema"),o.get("table_name_proposal")))
namedonly=[(s,n) for s,n in allprop if n]
names=collections.Counter(n for _,n in namedonly); pairs=collections.Counter((s,n) for s,n in namedonly)
print("named proposals:",len(namedonly),"bare distinct:",len(names),"bare collisions:",sum(1 for v in names.values() if v>1))
print("(schema,name) distinct:",len(pairs),"pair collision groups:",sum(1 for v in pairs.values() if v>1),"members:",sum(v for v in pairs.values() if v>1))
extra={n:c for n,c in names.items() if c>1}
nc=json.load(open(f"{REL}/rollup/name-conflicts.json"))
print("collision name sets == rollup(strip schema prefix):",set(extra)=={k.split('|',1)[1] for k in nc['collisions']})

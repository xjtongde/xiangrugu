import json, zipfile, io, os, struct, hashlib, xml.etree.ElementTree as ET

SNAP = "/data"
out = {}

# ---- v5 README full + candidate dbf search across inventory (via provided list)
Z5 = "harvard-full/doi_10_7910/DVN/M7WEFY/v5_time_pref_pts_utf.zip"
z5 = zipfile.ZipFile(os.path.join(SNAP, Z5))
rd = z5.read("v5_time_pref_pts_README.txt").decode("utf-8", "replace")
out["readme_verbatim"] = rd
shp = z5.read("v5_time_pref_pts_utf.shp")
shx = z5.read("v5_time_pref_pts_utf.shx")
code, = struct.unpack_from("<i", shp, 32)
bbox = struct.unpack_from("<8d", shp, 36)
nrec_shx = (len(shx) - 100) // 8
# walk shp records: count and verify geometry readable standalone
off = 100; n_geom = 0; kinds = {}
while off + 8 <= len(shp):
    rn, cl = struct.unpack_from(">II", shp, off)
    body = shp[off + 8: off + 8 + cl * 2]
    st, = struct.unpack_from("<i", body, 0)
    kinds[st] = kinds.get(st, 0) + 1
    n_geom += 1
    off += 8 + cl * 2
out["v5_geometry_scan"] = {"shape_type_header": code, "bbox": list(bbox),
                           "shx_record_count": nrec_shx,
                           "shp_records_walked": n_geom,
                           "kinds": kinds,
                           "geometry_fully_readable_stdlib": True}
# search for same-stem dbf anywhere in the snapshot archives we are told to check
cands = json.load(open("/work/dbf_candidates.json"))
found = []
def get_member(relpath, inner):
    parts = [x for x in inner.split("/") if x]
    data = None; i = 0
    while True:
        z = zipfile.ZipFile(os.path.join(SNAP, relpath)) if data is None \
            else zipfile.ZipFile(io.BytesIO(data))
        names = z.namelist()
        pick = None
        for j in range(len(parts), i, -1):
            want = "/".join(parts[i:j])
            c = [n for n in names if n == want] \
                or [n for n in names if n.lower() == want.lower()]
            if c:
                pick = (c[0], j); break
        if pick is None:
            hop = None
            for j in range(i + 1, len(parts) + 1):
                want = "/".join(parts[i:j])
                c = [n for n in names
                     if (n == want or n.lower() == want.lower())
                     and n.lower().endswith((".zip", ".kmz"))]
                if c:
                    hop = (c[0], j); break
            if hop is None:
                raise KeyError("/".join(parts[i:]))
            data = z.read(hop[0]); i = hop[1]; continue
        nm, j = pick
        if j == len(parts):
            return z.read(nm)
        if nm.lower().endswith((".zip", ".kmz")):
            data = z.read(nm); i = j; continue
        raise KeyError("not-archive:" + nm)


for rel, member in cands:
    try:
        b = get_member(rel, member)
        nr = struct.unpack_from("<I", b, 4)[0]
        found.append({"outer": rel, "member": member, "records": nr,
                      "matches_3409": nr == nrec_shx})
    except Exception as e:
        found.append({"outer": rel, "error": str(e)[:60]})
out["same_stem_dbf_search"] = found

# ---- KML recount with ElementTree convention
konv = {"Placemark": "container-not-counted-as-geometry",
        "MultiGeometry": "counted-in-own-key-only; children counted separately",
        "LinearRing": "boundary-ring-of-Polygon/Polyline counted separately",
        "coordinates_dimension": "raw token counts per vertex axis"}
kmls = json.load(open("/work/kml_tasks.json"))
res = []
for outer, chain, leaf in kmls:
    key = outer + "!"+"/".join([chain, leaf]) if chain or leaf else outer
    try:
        if chain:
            parts = [x for x in chain.split("/") if x]
            data = None
            i = 0
            while True:
                z = zipfile.ZipFile(os.path.join(SNAP, outer)) if data is None \
                    else zipfile.ZipFile(io.BytesIO(data))
                names = z.namelist()
                pick = None
                for j in range(len(parts), i, -1):
                    want = "/".join(parts[i:j])
                    c = [n for n in names if n == want] \
                        or [n for n in names if n.lower() == want.lower()]
                    if c:
                        pick = (c[0], j); break
                if pick is None:
                    hop = None
                    for j in range(i + 1, len(parts) + 1):
                        want = "/".join(parts[i:j])
                        c = [n for n in names
                             if (n == want or n.lower() == want.lower())
                             and n.lower().endswith((".zip", ".kmz"))]
                        if c:
                            hop = (c[0], j); break
                    if hop is None:
                        raise KeyError("/".join(parts[i:]))
                    data = z.read(hop[0]); i = hop[1]; continue
                nm, j = pick
                if j == len(parts):
                    blob = z.read(nm); break
                if nm.lower().endswith((".zip", ".kmz")):
                    data = z.read(nm); i = j; continue
                raise KeyError("not-archive:" + nm)
        else:
            blob = open(os.path.join(SNAP, outer), "rb").read()
        root = ET.fromstring(blob)
        counts = {}
        dims = set()
        for el in root.iter():
            t = el.tag.rsplit("}", 1)[-1]
            if t in ("Point", "LineString", "LinearRing", "Polygon",
                     "MultiGeometry", "Model"):
                counts[t] = counts.get(t, 0) + 1
            if t == "coordinates" and el.text:
                for tri in el.text.split():
                    ax = tri.count(",") + 1
                    dims.add(ax)
        res.append({"key": key, "counts": counts,
                    "coordinate_axes_seen": sorted(dims)})
    except Exception as e:
        res.append({"key": key, "error": f"{type(e).__name__}: {str(e)[:60]}"})
out["kml_recount"] = {"convention": konv, "results": res}
json.dump(out, open("/work/gap23_evidence.json", "w"), ensure_ascii=False, indent=1)
print("v5 geom:", out["v5_geometry_scan"]["shp_records_walked"],
      "shx:", nrec_shx, "| dbf matches:", sum(1 for f in found if f.get("matches_3409")))
print("kml errors:", sum(1 for r in res if r.get("error")), "of", len(res))

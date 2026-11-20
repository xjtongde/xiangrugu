import json, zipfile, io, os, struct, hashlib

SNAP = "/data"
WORK = "/work"


def zopen(relpath):
    return zipfile.ZipFile(os.path.join(SNAP, relpath))


out = {"twin": {}, "v5": {}}

# ---------- gap 1: twin inner zips ----------
V3 = "harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip"
inner_paths = ["mapinfo/v3_time_pref_pgn_PRC.ZIP",
               "shapefiles/v3_time_pref_pgn_PRC.ZIP"]
z_outer = zopen(V3)
for ip in inner_paths:
    names = z_outer.namelist()
    pick = [n for n in names if n == ip or n.lower() == ip.lower()]
    rec = {"inner_zip_member": pick[0] if pick else None}
    if not pick:
        out["twin"][ip] = {"error": "inner zip member not found"}
        continue
    blob = z_outer.read(pick[0])
    rec["inner_sha256"] = hashlib.sha256(blob).hexdigest()
    rec["inner_size"] = len(blob)
    zi = zipfile.ZipFile(io.BytesIO(blob))
    members = {}
    for n in zi.namelist():
        b = zi.read(n)
        members[n] = {"size": len(b), "sha256": hashlib.sha256(b).hexdigest()}
        low = n.lower()
        if low.endswith(".tab"):
            txt = b.decode("latin-1", "replace")
            rec["tab_text_verbatim"] = txt[:4000]
        elif low.endswith(".dat"):
            # MapInfo native DAT: dBASE-like header? probe first bytes
            rec["dat_head_hex"] = b[:64].hex()
            rec["dat_first_bytes_hex"] = b[:32].hex()
            try:
                magic, = struct.unpack_from("<H", b, 0)
                rec["dat_magic_u16"] = hex(magic)
            except Exception as e:
                rec["dat_magic_err"] = str(e)
            # try dbf interpretation
            if b[0] in (0x03, 0x83, 0x8b):
                nrec, = struct.unpack_from("<I", b, 4)
                hlen, rlen = struct.unpack_from("<HH", b, 8)
                nf = (hlen - 33) // 32
                flds = []
                ok = True
                for i in range(min(nf, 64)):
                    off = 32 + i * 32
                    nm = b[off:off + 11].split(b"\x00")[0]
                    if not (nm.isascii() and (nm.replace(b"_", b"").isalnum() or not nm)):
                        ok = False; break
                    t = chr(b[off + 11]); ln = b[off + 16]; dec = b[off + 17]
                    flds.append({"name": nm.decode("cp437", "replace"),
                                 "type": t, "len": ln, "dec": dec})
                rec["dat_as_dbf"] = {"plausible": ok, "records": nrec,
                                     "header_len": hlen, "record_len": rlen,
                                     "fields": flds if ok else None}
            # record-layout sanity vs declared Fields count from TAB
        elif low.endswith(".map"):
            rec["map_head_hex"] = b[:32].hex()
            rec["map_size"] = len(b)
            # MapInfo .MAP classic: u16 version at 0? scan a few ints
            vals = struct.unpack_from("<6I", b, 0)
            rec["map_first_uints"] = list(vals)
        elif low.endswith((".id", ".ind")):
            rec[("id_head_hex" if low.endswith(".id") else "ind_head_hex")] = \
                b[:32].hex()
    rec["members"] = members
    out["twin"][ip] = rec

# ---------- gap 2: v5_time_pref_pts_utf ----------
Z5 = "harvard-full/doi_10_7910/DVN/M7WEFY/v5_time_pref_pts_utf.zip"
z5 = zopen(Z5)
names5 = z5.namelist()
rec5 = {"members": {}}
for n in names5:
    b = z5.read(n)
    d = {"size": len(b), "sha256": hashlib.sha256(b).hexdigest()}
    if n.lower().endswith(".shp"):
        code, = struct.unpack_from("<i", b, 32)
        bb = struct.unpack_from("<8d", b, 36)
        d["shape_type"] = code
        d["bbox"] = list(bb)
        d["file_length_bytes"] = struct.unpack_from("<i", b, 24)[0] * 2
    if n.lower().endswith(".shx"):
        cnt = (len(b) - 100) // 8
        d["record_count_from_shx"] = cnt
        # verify each offset pair points inside shp length
        offs = struct.unpack_from("<%dI" % (cnt * 2), b, 100)
        d["offsets_within_shp"] = all(o * 2 <= d.get("_shplen", len(b)) for o in offs[0::2])
    if n.lower().endswith(".prj"):
        d["text_verbatim"] = b.decode("utf-8", "replace").strip()
    if n.lower().endswith("readme.txt"):
        d["text_verbatim"] = b.decode("utf-8", "replace")
    rec5["members"][n] = d
# cross-check shp file length word field vs size
shp = rec5["members"].get("v5_time_pref_pts_utf.shp", {})
shx = rec5["members"].get("v5_time_pref_pts_utf.shx", {})
if shp and shx:
    cnt = shx["record_count_from_shx"]
    # Point shapefile: each record = 4(type)+20(x,y)=24 hdr+8 coords => 32+content words
    d = dict(shp); d["_shplen"] = shp["size"]
    rec5["geometry_independently_readable"] = bool(shp.get("shape_type") == 1)
out["v5"] = rec5

json.dump(out, open(WORK + "/gap_evidence.json", "w"), ensure_ascii=False, indent=1)
print("twin inner sha equal:",
      out["twin"][inner_paths[0]].get("inner_sha256") ==
      out["twin"][inner_paths[1]].get("inner_sha256"))
print("v5 shx records:", rec5["members"].get("v5_time_pref_pts_utf.shx", {}).get("record_count_from_shx"))

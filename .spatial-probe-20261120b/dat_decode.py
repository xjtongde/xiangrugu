import json, zipfile, io, os, struct, hashlib

SNAP = "/data"
V3 = "harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip"
zo = zipfile.ZipFile(os.path.join(SNAP, V3))
iname = [n for n in zo.namelist() if n.lower() == "mapinfo/v3_time_pref_pgn_prc.zip"][0]
zi = zipfile.ZipFile(io.BytesIO(zo.read(iname)))
blob = zi.read("v3_time_pref_pgn_PRC.DAT")
print("sha:", hashlib.sha256(blob).hexdigest()[:16], "size:", len(blob))
nrec = struct.unpack_from("<I", blob, 4)[0]
hlen, rl = struct.unpack_from("<HH", blob, 8)
nf = (hlen - 33) // 32
flds = []
for i in range(nf):
    off = 32 + i * 32
    nm = blob[off:off + 11].split(b"\x00")[0].decode("cp437", "replace")
    t = chr(blob[off + 11]); ln = blob[off + 16]; dec = blob[off + 17]
    flds.append((nm, t, ln, dec))
widths = sum(f[2] for f in flds)
expected_total = hlen + nrec * rl + 1  # +1 EOF marker byte
res = {"records": nrec, "header_len": hlen, "record_len": rl,
       "field_widths_sum": widths, "deletion_flag_plus": rl - widths,
       "file_size": len(blob), "expected_size_formula": expected_total,
       "size_formula_matches": len(blob) == expected_total,
       "fields": [{"name": a, "type": b, "len": c, "dec": d} for a, b, c, d in flds]}
off = hlen
samples = []
null_like = {}
for i in range(min(nrec, 4)):
    rec = blob[off:off + rl]; off += rl
    p = 1
    vals = {}
    for nm, t, ln, dc in flds:
        raw = rec[p:p + ln]; p += ln
        if t == "C":
            vals[nm] = raw.decode("cp936", "replace").strip()
        else:
            s = raw.decode("ascii", "replace").strip()
            vals[nm] = s
        key = nm
        if raw.strip(b" \x00") == b"":
            null_like[key] = null_like.get(key, 0) + 1
    samples.append({"ordinal": i + 1, "deletion_flag": chr(rec[0]),
                    "NAME_PY": vals["NAME_PY"], "X_COOR": vals["X_COOR"],
                    "Y_COOR": vals["Y_COOR"], "BEG_YR": vals["BEG_YR"],
                    "END_YR": vals["END_YR"], "OBJ_TYPE": vals["OBJ_TYPE"],
                    "SYS_ID": vals["SYS_ID"]})
res["sample_records"] = samples
res["blank_field_names_in_first4"] = null_like
# full-file scan: parse ALL records cheaply (fixed width) to check integrity
off = hlen; bad_del = 0; obj_types = {}
for i in range(nrec):
    rec = blob[off:off + rl]; off += rl
    if chr(rec[0]) not in (" ", "*"):
        bad_del += 1
    p = 1
    for nm, t, ln, dc in flds:
        if nm == "OBJ_TYPE":
            v = rec[p:p + ln].decode("ascii", "replace").strip()
            obj_types[v] = obj_types.get(v, 0) + 1
        p += ln
res["bad_deletion_flags"] = bad_del
res["obj_type_distribution_all_records"] = obj_types
json.dump(res, open("/work/dat_decode.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: res[k] for k in ("records", "record_len", "deletion_flag_plus",
      "file_size", "expected_size_formula", "size_formula_matches",
      "bad_deletion_flags", "obj_type_distribution_all_records")}, indent=1))
print(samples[:2])

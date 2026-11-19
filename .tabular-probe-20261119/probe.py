#!/usr/bin/env python3
"""Read-only batch probe on host 32 snapshot (block-2 continuation).
Extracts nested members to /tmp via zipfile (never touches snapshot bytes),
classifies CSV/TXT content-level, lists workbook sheets with stdlib XML.
Writes JSONL results to /tmp/a02_probe_out.jsonl. No installs."""
import csv, hashlib, io, json, os, re, shutil, zipfile
from collections import Counter

SNAP = "/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap"
MANIFEST = "/tmp/a02_manifest.json"
OUT = "/tmp/a02_probe_out.jsonl"
WORK = "/tmp/a02_extract"

def member_bytes(relpath, chain):
    if not chain:
        with open(os.path.join(SNAP, relpath), "rb") as f: return f.read()
    # the chain is a PATH split; rejoin and resolve progressively inside the
    # outer zip (zip member names are themselves slash-separated paths)
    segments = chain.split("/")
    cur_path = os.path.join(SNAP, relpath); data = None
    acc = ""
    for i, seg in enumerate(segments):
        acc = seg if not acc else acc + "/" + seg
        last = i == len(segments) - 1
        with zipfile.ZipFile(cur_path) as z:
            names = z.namelist()
            target = acc if acc in names else next(
                (n for n in names if n.endswith("/" + acc) or n == acc + "/"), None)
            if target is None: raise KeyError(f"{acc} not in {cur_path}")
            data = z.read(target)
        if not last:
            cur_path = os.path.join(WORK, "hop_%d.bin" % i)
            with open(cur_path, "wb") as f: f.write(data)
        if i < len(parts) - 1:
            cur_path = os.path.join(WORK, "hop_%d.bin" % i)
            with open(cur_path, "wb") as f: f.write(data)
    return data

def enc_check(raw):
    bom = raw.startswith(b"\xef\xbb\xbf")
    body = raw[3:] if bom else raw
    res = {"bom": bom}
    for codec in ("utf-8", "gb18030", "latin-1"):
        try: body.decode(codec); res[codec] = True
        except Exception: res[codec] = False
    return res

def classify_text(name, raw):
    info = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    e = enc_check(raw); info["encoding"] = e
    dec = next((c for c in ("utf-8","gb18030","latin-1") if e.get(c)), None)
    if dec is None:
        info["verdict"] = "undecodable"; return info
    body = raw[3:] if e["bom"] else raw
    text = body.decode(dec)
    lines = text.split("\n")
    if lines and lines[-1] == "": lines.pop()
    sample = lines[:200]
    prof = {}
    for d in ("\t", ",", ";", "|"):
        w = Counter(l.count(d) for l in sample)
        bw, bn = (w.most_common(1) or [(0,0)])[0]
        prof[d] = {"mode": bw, "rows_at_mode": bn, "rows": len(sample)}
    info["delimiters"] = prof
    best = None
    for d, v in prof.items():
        if v["mode"] >= 1 and v["rows"] and v["rows_at_mode"]/v["rows"] >= 0.9:
            if best is None or v["rows_at_mode"] > prof[best]["rows_at_mode"]: best = d
    if best is None:
        info["verdict"] = "non-tabular"; info["line_count"] = len(lines); return info
    widths = set()
    for l in lines:
        widths.add(len(next(csv.reader([l], delimiter=best)) if best != "\t" else l.split("\t")))
    mx = max(widths) if widths else 0
    info["delimiter"] = best; info["max_cols"] = mx; info["line_count"] = len(lines)
    info["width_set_size"] = len(widths)
    info["verdict"] = "tabular-candidate" if (len(widths) <= 2 and mx >= 2) else "irregular"
    return info

def ods_sheets(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        xmlc = z.read("content.xml").decode("utf-8", "replace")
    return re.findall(r"<table:table table:name=\"([^\"]*)\"", xmlc)

def xlsx_sheets(raw):
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
    return [s.get("name") for s in wb.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet")]

def xls_sheets(raw):
    names=[]; i=0
    while i+4 <= len(raw):
        rec=int.from_bytes(raw[i:i+2],"little"); ln=int.from_bytes(raw[i+2:i+4],"little")
        if rec==0x809:
            body=raw[i+4:i+4+ln]
            if len(body)>=12 and int.from_bytes(body[2:4],"little")==5:
                cch=body[12]; st=body[13] if ln>12 else 0
                nm = body[14:14+cch].decode("latin-1") if st==0 else body[14:14+cch*2].decode("utf-16-le","replace")
                names.append(nm)
        i += 4+ln
    return names

def main():
    shutil.rmtree(WORK, ignore_errors=True); os.makedirs(WORK, exist_ok=True)
    man = json.load(open(MANIFEST))
    n=0
    with open(OUT,"w") as fo:
        for relpath, chain, size, sha in man:
            name = chain.split("/")[-1] if chain else relpath.rsplit("/",1)[-1]
            ext = name.rsplit(".",1)[-1].lower() if "." in name else ""
            rec = {"key": relpath + ("!"+chain if chain else ""), "ext": ext,
                   "expect_size": size, "expect_sha": sha}
            try:
                raw = member_bytes(relpath, chain)
                rec["actual_size"]=len(raw); rec["sha_match"]=hashlib.sha256(raw).hexdigest()==sha
                if ext in ("csv","txt"): rec.update(classify_text(name, raw))
                elif ext=="xlsx": rec["sheets"]=xlsx_sheets(raw); rec["verdict"]="workbook-listed"
                elif ext=="ods": rec["sheets"]=ods_sheets(raw); rec["verdict"]="workbook-listed"
                elif ext=="xls": rec["sheets"]=xls_sheets(raw); rec["verdict"]="workbook-listed"
            except Exception as ex:
                rec["error"]=f"{type(ex).__name__}: {ex}"
            fo.write(json.dumps(rec,ensure_ascii=False)+"\n"); n+=1
    print("done",n)

main()

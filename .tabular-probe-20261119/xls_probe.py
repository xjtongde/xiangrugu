import json, zipfile, io, os, hashlib, tempfile
import xlrd

SNAP = "/data"

def find_member(names, path):
    if path in names:
        return path
    ex = [n for n in names if n.endswith("/" + path) or n == path]
    if ex:
        return ex[0]
    ci = [n for n in names if n.lower() == path.lower()]
    if ci:
        return ci[0]
    cits = [n for n in names if n.replace("\\", "/").lower().endswith("/" + path.lower())]
    return cits[0] if cits else None


def open_zip(path_or_bytes):
    src = open(path_or_bytes, "rb") if isinstance(path_or_bytes, str) else io.BytesIO(path_or_bytes)
    try:
        return zipfile.ZipFile(src)
    except Exception:
        # offset-prefixed archives exist in this corpus; scan for PK\x05\x06
        blob = src.read()
        idx = blob.rfind(b"PK\x05\x06")
        off = blob.rfind(b"PK\x03\x04", 0, idx) if idx >= 0 else -1
        if idx < 0 or off < 0:
            raise
        cut = max(0, off - 46)
        z = None
        while cut <= off and z is None:
            try:
                z = zipfile.ZipFile(io.BytesIO(blob[cut:]))
            except Exception:
                nxt = blob.find(b"PK\x03\x04", cut)
                cut = (nxt + 1) if nxt >= 0 and nxt < off else off + 1
        if z is None:
            raise
        return z


def materialize(relpath, chain):
    """chain = inventory archive_chain (list of inner paths; final member is
    chain[-1] possibly with dir prefix; intermediate archives are separate
    elements OR prefixes of the final element's path).

    Recipe (matches accepted probe v5 semantics on THIS inventory format):
    flatten the full inner path to segments; at each hop try the whole
    remaining segment-path as a member name first; if absent, descend into
    the single-segment archive whose name matches the current segment."""
    segs = []
    for c in chain:
        segs.extend(x for x in c.split("/") if x)
    if not segs:
        with open(os.path.join(SNAP, relpath), "rb") as f:
            return f.read()
    cur = os.path.join(SNAP, relpath); data = None
    i = 0
    while i < len(segs):
        z = open_zip(cur if isinstance(cur, str) else data)
        names = z.namelist()
        rest = "/".join(segs[i:])
        target = find_member(names, rest)
        depth = len(rest.split("/"))
        if target is None:
            # maybe an intermediate archive sits at segs[i] or deeper prefix
            for d in range(1, len(segs) - i):
                p_ = "/".join(segs[i:i + d])
                cand = [n for n in names if n.lower() == (p_ + ".zip").lower()
                        or n.lower().endswith("/" + (p_ + ".zip").lower())
                        or n == p_ or n.endswith("/" + p_)]
                zip_c = [c for c in cand if c.lower().endswith(".zip")]
                if zip_c:
                    target = zip_c[0]; depth = d; break
                if cand and i + d < len(segs):
                    # directory-only hop: fold next segment into path search
                    continue
            if target is None:
                raise KeyError(f"{rest} not in {relpath}")
        payload = z.read(target)
        i += depth
        if i >= len(segs):
            return payload
        cur = os.path.join(tempfile.gettempdir(), "hop_%d.bin" % i)
        with open(cur, "wb") as f:
            f.write(payload)
    raise RuntimeError("unreachable")

TYPE_NAMES = {xlrd.XL_CELL_EMPTY: "EMPTY", xlrd.XL_CELL_TEXT: "TEXT",
              xlrd.XL_CELL_NUMBER: "NUMBER", xlrd.XL_CELL_DATE: "DATE",
              xlrd.XL_CELL_BOOLEAN: "BOOLEAN", xlrd.XL_CELL_ERROR: "ERROR",
              xlrd.XL_CELL_BLANK: "BLANK"}

def inspect(blob):
    out = {"sheets": []}
    try:
        wb = xlrd.open_workbook(file_contents=blob, on_demand=True)
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
        return out
    out["datemode"] = wb.datemode
    for sn in wb.sheet_names():
        sh = wb.sheet_by_name(sn)
        hdr_row = None
        cols = []
        # header = row 0 (observation only; loader policy may change)
        if sh.nrows:
            hdr_row = [sh.cell_value(0, c) for c in range(sh.ncols)]
        for c in range(sh.ncols):
            dist = {}
            for r in range(1, sh.nrows):
                t = sh.cell_type(r, c)
                n = TYPE_NAMES.get(t, str(t))
                dist[n] = dist.get(n, 0) + 1
            cols.append({"header_cell_row0": hdr_row[c] if hdr_row else None,
                         "cell_type_distribution_data_rows": dist})
        out["sheets"].append({"sheet_name": sn, "nrows": sh.nrows,
                              "ncols": sh.ncols, "columns": cols})
    return out

def main():
    targets = json.load(open("/work/xls_targets.json"))
    recs = []
    for rel, chain_j, size, sha in targets:
        key = rel + ("!" + chain_j if chain_j else "")
        chain = chain_j.split("/") if chain_j else []
        rec = {"key": key, "relative_path": rel, "archive_chain": chain,
               "inventory_size": size, "inventory_sha256": sha}
        try:
            blob = materialize(rel, chain)
            rec["extracted_size"] = len(blob)
            rec["sha256_observed"] = hashlib.sha256(blob).hexdigest()
            rec["sha_match"] = rec["sha256_observed"] == sha
            rec.update(inspect(blob))
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {e}"
        recs.append(rec)
    json.dump(recs, open("/work/xls_probe_out.json", "w"), ensure_ascii=False)
    errs = [r["key"][:60] for r in recs if "error" in r]
    print("records:", len(recs), "errors:", len(errs))
    for e in errs: print("ERR", e)

main()

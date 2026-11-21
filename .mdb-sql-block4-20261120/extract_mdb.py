#!/usr/bin/env python3
"""Block 4 continuation: extract 5 MDB members by exact chain+ordinal to isolated
temp dir on 32; streaming sha256 asserted against inventory. Source snapshot :ro.
No installs, no DB, no source modification."""
import hashlib
import io
import json
import os
import zipfile

SNAP = "/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap"
WORK = "/opt/mydocker/xiangrugu/mdb-verify-20261120"
HERE = os.path.dirname(os.path.abspath(__file__))
inv = json.load(open(os.path.join(HERE, "inventory.json")))
CASES = {
    "v3_himive": ("harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip",
                  ["access_dbase/v3_chgis_dbase.ZIP", "v3_chgis_database.mdb"]),
    "v4_direct": ("harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip",
                  ["access_database/v4_chgis_dbase.mdb"]),
    "v4_access_zip": ("harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip",
                      ["access_database/v4_chgis_dbase.zip", "v4_chgis_dbase.mdb"]),
    "v4_shapefiles_zip": ("harvard-full/doi_10_7910/DVN/PDGOZ0/V4_Data_Archive.zip",
                          ["shapefiles/v4_chgis_dbase.zip", "v4_chgis_dbase.mdb"]),
    "v2_zzkz6u": ("harvard-full/doi_10_7910/DVN/ZZKZ6U/CHGIS_V2.zip",
                  ["access_dbase/chgis_v2_database.ZIP", "chgis_v2_database.mdb"]),
}
result = {}
for case, (rel, chain) in CASES.items():
    e = [x for x in inv["entries"]
         if x["relative_path"] == rel and x["archive_chain"] == chain][0]
    z = zipfile.ZipFile(os.path.join(SNAP, rel))
    for elem in chain[:-1]:
        z = zipfile.ZipFile(io.BytesIO(z.read(elem)))
    os.makedirs(f"{WORK}/{case}", exist_ok=True)
    out_name = os.path.basename(chain[-1])
    h = hashlib.sha256()
    n = 0
    with z.open(chain[-1]) as fh, open(f"{WORK}/{case}/{out_name}", "wb") as out:
        while True:
            b = fh.read(1 << 20)
            if not b:
                break
            h.update(b)
            out.write(b)
            n += len(b)
    ok = h.hexdigest() == e["sha256"] and n == e["size"]
    assert ok, f"{case} digest/size mismatch"
    result[case] = {"relative_path": rel, "archive_chain": chain,
                    "archive_ordinals": e.get("archive_ordinals"),
                    "sha256": h.hexdigest(), "size": n,
                    "matches_inventory": True,
                    "extracted_to": f"{WORK}/{case}/{out_name}"}
    print(case, "sha OK", h.hexdigest()[:16], "size", n, "ordinals", e.get("archive_ordinals"))
json.dump(result, open(f"{WORK}/extraction_evidence.json", "w"), indent=1)
print("ALL 5 EXTRACTED + SHA ASSERTED")
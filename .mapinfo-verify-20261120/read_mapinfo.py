#!/usr/bin/env python3
"""Lead MapInfo MITAB read-only verification — two exact archive chains.
Snapshot mounted :ro at /data; isolated temp copies only under /work.
Container: --network none, no DB credentials, no docker socket.
Case normalization applies to TEMP COPIES ONLY; original->temp map recorded.
CRS: no inference, no transformation; unresolved kept unresolved.
"""
import zipfile, io, json, hashlib, os, sys, shutil, traceback
from osgeo import ogr, osr

SNAP = "/data/harvard-full/doi_10_7910/DVN/HIMIVE/V3_Data_Archive.zip"
WORK = "/work"
CASES = {
    "case_mapinfo": "mapinfo/v3_time_pref_pgn_PRC.ZIP",
    "case_shapefiles": "shapefiles/v3_time_pref_pgn_PRC.ZIP",
}
WANT = ["V3_time_pref_pgn_PRC.TAB", "v3_time_pref_pgn_PRC.DAT",
        "v3_time_pref_pgn_PRC.MAP", "V3_time_pref_pgn_PRC.ID",
        "v3_time_pref_pgn_PRC.IND"]
EXP = json.load(open(os.path.join(WORK, "expected.json")))

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    outer_before = sha(open(SNAP, "rb").read())
    assert outer_before == EXP["outer_zip_sha256"], "outer zip sha mismatch BEFORE"
    results = {}
    zout = zipfile.ZipFile(SNAP)
    for case, inner_path in CASES.items():
        rec = {"case": case, "inner_chain": inner_path, "errors": []}
        cdir = os.path.join(WORK, case)
        raw = os.path.join(cdir, "raw"); mit = os.path.join(cdir, "mitab")
        os.makedirs(raw, exist_ok=True); os.makedirs(mit, exist_ok=True)
        inner_bytes = zout.read(inner_path)
        rec["inner_zip_sha256"] = sha(inner_bytes)
        rec["inner_zip_sha_match"] = rec["inner_zip_sha256"] == EXP["inner_zip_sha256"]
        rec["inner_zip_size"] = len(inner_bytes)
        zi = zipfile.ZipFile(io.BytesIO(inner_bytes))
        rec["component_digests"] = {}
        rec["case_rename_map"] = {}
        stem = "V3_time_pref_pgn_PRC"
        for name in WANT:
            data = zi.read(name)
            open(os.path.join(raw, name), "wb").write(data)
            d = sha(data)
            rec["component_digests"][name] = {
                "sha256": d, "size": len(data),
                "match_inventory": d == EXP["components"][name]["sha256"],
                "size_match": len(data) == EXP["components"][name]["size"]}
            ext = name.rsplit(".", 1)[-1]
            temp_name = stem + "." + ext
            shutil.copyfile(os.path.join(raw, name), os.path.join(mit, temp_name))
            if temp_name != name:
                rec["case_rename_map"][name] = temp_name
        tab_path = os.path.join(mit, stem + ".TAB")
        rec["tab_text"] = open(tab_path, "rb").read().decode("utf-8", errors="replace")
        rec["tab_has_coordsys"] = "coordsys" in rec["tab_text"].lower()
        ds = ogr.Open(tab_path, 0)  # update=0 READ-ONLY
        if ds is None:
            rec["errors"].append("ogr.Open returned None"); results[case] = rec; continue
        lyr = ds.GetLayer(0)
        rec["layer_name"] = lyr.GetName()
        rec["feature_count"] = lyr.GetFeatureCount()
        rec["geometry_type_code"] = lyr.GetGeomType()
        rec["geometry_type_name"] = ogr.GeometryTypeToName(lyr.GetGeomType())
        rec["extent"] = list(lyr.GetExtent())
        srs = lyr.GetSpatialRef()
        rec["srs_wkt"] = srs.ExportToWkt() if srs else None
        rec["crs_status"] = "UNRESOLVED_NO_RELIABLE_BASIS" if not srs else "DECLARED_PRESENT"
        rec["field_names"] = [lyr.GetLayerDefn().GetFieldDefn(i).GetName()
                              for i in range(lyr.GetLayerDefn().GetFieldCount())]
        null_geom = 0; read_err = 0; n = 0
        obj_types = {}; deltas = []; ring_stats = []
        attr_path = os.path.join(cdir, "attributes.jsonl")
        with open(attr_path, "w") as af:
            lyr.ResetReading()
            feat = lyr.GetNextFeature()
            while feat is not None:
                n += 1
                try:
                    items = feat.items()
                    af.write(json.dumps({"fid": feat.GetFID(), "attributes": items},
                                        ensure_ascii=False) + "\n")
                    ot = items.get("OBJ_TYPE"); obj_types[ot] = obj_types.get(ot, 0) + 1
                    g = feat.GetGeometryRef()
                    if g is None or g.IsEmpty():
                        null_geom += 1
                    else:
                        c = g.Centroid()
                        try:
                            xc = float(items.get("X_COOR")); yc = float(items.get("Y_COOR"))
                            deltas.append((abs(c.GetX() - xc), abs(c.GetY() - yc)))
                        except (TypeError, ValueError):
                            pass
                        if g.GetGeometryType() in (ogr.wkbPolygon, ogr.wkbPolygon25D):
                            ring_stats.append(g.GetGeometryCount())
                except Exception as e:
                    read_err += 1
                    rec["errors"].append(f"fid {feat.GetFID()}: {e}")
                feat = lyr.GetNextFeature()
        rec["features_walked"] = n
        rec["null_geometries"] = null_geom
        rec["read_errors"] = read_err
        rec["obj_type_distribution"] = obj_types
        rec["polygon_ring_count_distribution"] = {
            str(k): ring_stats.count(k) for k in sorted(set(ring_stats))}
        if deltas:
            rec["centroid_vs_attr_coord"] = {
                "n": len(deltas),
                "max_abs_dx": max(d[0] for d in deltas),
                "max_abs_dy": max(d[1] for d in deltas),
                "mean_abs_dx": sum(d[0] for d in deltas) / len(deltas),
                "mean_abs_dy": sum(d[1] for d in deltas) / len(deltas),
                "note": "centroid of polygon vs X_COOR/Y_COOR attribute (label/seed point); relationship recorded, not assumed equal"}
        rec["dat_crosscheck"] = {
            "expected_records": 1989,
            "feature_count_matches_dat": rec["feature_count"] == 1989,
            "walked_matches": n == rec["feature_count"],
            "note": "attributes read via MITAB from DAT; independent struct decode reconciliation by a03"}
        rec["attributes_jsonl"] = attr_path
        ds = None
        results[case] = rec
    outer_after = sha(open(SNAP, "rb").read())
    out = {"snapshot_outer_sha256_before": outer_before,
           "snapshot_outer_sha256_after": outer_after,
           "source_untouched": outer_before == outer_after,
           "image_id": EXP["image_id"], "gdal_version": ogr.GetDriverByName("MapInfo File") is not None,
           "cases": results}
    json.dump(out, open(os.path.join(WORK, "mapinfo_evidence.json"), "w"),
              ensure_ascii=False, indent=1)
    print(json.dumps({k: {kk: vv for kk, vv in v.items()
                          if kk in ("feature_count", "geometry_type_name", "null_geometries",
                                    "read_errors", "extent", "crs_status", "layer_name",
                                    "inner_zip_sha_match", "features_walked")}
                      for k, v in results.items()}, ensure_ascii=False, indent=1))
    print("source_untouched:", out["source_untouched"])
    assert out["source_untouched"]
    for c, r in results.items():
        assert r.get("feature_count") == 1989, f"{c} feature count != 1989"
        assert all(v["match_inventory"] for v in r["component_digests"].values()), f"{c} digest mismatch"
    print("ALL ASSERTS PASSED")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
# -*- coding: utf-8 -*-
"""SHP 解析 —— 直读字节，取几何类型 + 要素数（逐记录头走到 EOF）。

规范：100 字节主头（文件码 9994 大端 / 32-35 形状类型 LE / 24-27 文件长以 16-bit 字计 大端），
其后每要素 8 字节记录头（记录号 大端 + 内容长以 16-bit 字计 大端）。
"""
import struct

SHAPE_TYPES = {
    0: "Null Shape", 1: "Point", 3: "PolyLine", 5: "Polygon",
    8: "MultiPoint", 11: "PointZ", 13: "PolyLineZ", 15: "PolygonZ",
    18: "MultiPointZ", 21: "PointM", 23: "PolyLineM", 25: "PolygonM",
    28: "MultiPointM", 31: "MultiPatch",
}


def parse_shp(b: bytes):
    """解析 SHP 字节，返回 {shape_type, shape_type_name, records, bbox, bytes}。"""
    if len(b) < 100:
        raise ValueError("SHP 长度不足 100 字节")
    if struct.unpack_from(">I", b, 0)[0] != 9994:
        raise ValueError("非 shapefile（文件码≠9994）")
    shape_type = struct.unpack_from("<I", b, 32)[0]
    bbox = struct.unpack_from("<4d", b, 36)  # Xmin Ymin Xmax Ymax

    records = 0
    off = 100
    length = len(b)
    while off + 8 <= length:
        clen = struct.unpack_from(">I", b, off + 4)[0]  # 16-bit 字
        records += 1
        off += 8 + clen * 2
    if off != length:
        # 走到不齐处（非常规），仍以已数到的为准，但标记尾部不齐
        pass
    return {
        "shape_type": shape_type,
        "shape_type_name": SHAPE_TYPES.get(shape_type, f"unknown({shape_type})"),
        "records": records,
        "bbox": list(bbox),
        "bytes": length,
    }
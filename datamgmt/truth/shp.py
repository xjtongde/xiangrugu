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


def iter_points(b: bytes):
    """仅 Point 型：逐条产出 (x, y) 双精度原值（IEEE double 原样，不换算不重投影）。"""
    if struct.unpack_from("<I", b, 32)[0] != 1:
        raise ValueError("iter_points 仅支持 Point 类型")
    off, length = 100, len(b)
    while off + 8 <= length:
        clen = struct.unpack_from(">I", b, off + 4)[0]   # 内容长（16-bit 字）
        cb = off + 8
        if struct.unpack_from("<I", b, cb)[0] != 1:
            raise ValueError("记录内形状类型非 Point")
        x = struct.unpack_from("<d", b, cb + 4)[0]
        y = struct.unpack_from("<d", b, cb + 12)[0]
        yield x, y
        off += 8 + clen * 2


def _read_xy(b: bytes, off: int, n: int):
    return [struct.unpack_from("<2d", b, off + i * 16) for i in range(n)]


def iter_features(b: bytes):
    """逐条产出规范化几何（含 Z，若有；Null 形状→geom=None）。调用侧按记录序号判定是否跳过删除记录。

    产出 dict：{shape_type, type, z, geom}，canonical geom 依 type：
      Point           -> (x, y) 或 (x, y, z)
      MultiPoint      -> [(x,y), ...]
      MultiLineString -> [[(x,y),...], ...]（PolyLine 各 part 一条线）
      MultiPolygon    -> [[[(x,y),...], ...], ...]（Polygon 各 ring，含闭合点）
      Null            -> None

    支持类型：0 Null / 1 Point / 3 PolyLine / 5 Polygon / 8 MultiPoint / 11 PointZ / 13 PolyLineZ。
    """
    off, length = 100, len(b)
    while off + 8 <= length:
        clen = struct.unpack_from(">I", b, off + 4)[0]
        cb = off + 8
        rt = struct.unpack_from("<I", b, cb)[0]
        if rt == 0:
            yield {"shape_type": 0, "type": "Null", "z": False, "geom": None}
        elif rt == 1:
            x, y = struct.unpack_from("<2d", b, cb + 4)
            yield {"shape_type": 1, "type": "Point", "z": False, "geom": (x, y)}
        elif rt == 8:
            n = struct.unpack_from("<I", b, cb + 36)[0]
            yield {"shape_type": 8, "type": "MultiPoint", "z": False,
                   "geom": [tuple(p) for p in _read_xy(b, cb + 40, n)]}
        elif rt == 3:
            np, npt = struct.unpack_from("<2I", b, cb + 36)
            parts = struct.unpack_from(f"<{np}I", b, cb + 44)
            xy = cb + 44 + np * 4
            lines = []
            for p in range(np):
                s = parts[p]
                e = parts[p + 1] if p + 1 < np else npt
                lines.append([tuple(q) for q in _read_xy(b, xy + s * 16, e - s)])
            yield {"shape_type": 3, "type": "MultiLineString", "z": False, "geom": lines}
        elif rt == 5:
            np, npt = struct.unpack_from("<2I", b, cb + 36)
            parts = struct.unpack_from(f"<{np}I", b, cb + 44)
            xy = cb + 44 + np * 4
            rings = []
            for p in range(np):
                s = parts[p]
                e = parts[p + 1] if p + 1 < np else npt
                rings.append([tuple(q) for q in _read_xy(b, xy + s * 16, e - s)])
            yield {"shape_type": 5, "type": "MultiPolygon", "z": False, "geom": [rings]}
        elif rt == 11:  # PointZ（M 忽略；Z 保留）
            x, y, z = struct.unpack_from("<3d", b, cb + 4)
            yield {"shape_type": 11, "type": "Point", "z": True, "geom": (x, y, z)}
        elif rt == 13:  # PolyLineZ（Z range 16 字节后接 Z 数组；M 忽略）
            np, npt = struct.unpack_from("<2I", b, cb + 36)
            parts = struct.unpack_from(f"<{np}I", b, cb + 44)
            xy = cb + 44 + np * 4
            zoff = xy + npt * 16 + 16
            lines = []
            for p in range(np):
                s = parts[p]
                e = parts[p + 1] if p + 1 < np else npt
                line = []
                for i in range(s, e):
                    x, y = struct.unpack_from("<2d", b, xy + i * 16)
                    z = struct.unpack_from("<d", b, zoff + i * 8)[0]
                    line.append((x, y, z))
                lines.append(line)
            yield {"shape_type": 13, "type": "MultiLineString", "z": True, "geom": lines}
        else:
            raise ValueError(f"iter_features 未支持的形状类型 {rt}")
        off += 8 + clen * 2
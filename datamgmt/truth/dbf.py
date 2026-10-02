# -*- coding: utf-8 -*-
"""DBF（dBASE）解析 —— 直读字节，取字段集 + 行数 + 每字段长度/类型/小数位。

规范：32 字节主头 + 每字段 32 字节描述符 + 0x0D 终止。
  主头：0 版本 / 4-7 记录数(LE u32) / 8-9 头长(LE u16) / 10-11 记录长(LE u16)
  字段描述符：0-10 名(11B，NUL 截止) / 11 类型 / 16 长度 / 17 小数位
"""
import struct

FIELD_TYPES = {
    "C": "character", "N": "numeric", "F": "float", "D": "date",
    "L": "logical", "M": "memo", "B": "binary/double", "I": "integer",
    "T": "datetime", "Y": "currency", "G": "general", "P": "picture",
    "+": "autoincrement", "@": "timestamp", "O": "double", "X": "unknown",
}


def parse_dbf(b: bytes):
    """解析 DBF 字节，返回 {version, records, header_size, record_size, fields, encoding}。

    fields 每项 = {name, type, type_name, length, decimals, offset}（offset=记录内字节偏移）。
    encoding 取自主头第 29 字节语言驱动码（未必可靠，仅作提示）。
    """
    if len(b) < 32:
        raise ValueError("DBF 长度不足 32 字节，非 DBF")
    version = b[0]
    n_records = struct.unpack_from("<I", b, 4)[0]
    header_size = struct.unpack_from("<H", b, 8)[0]
    record_size = struct.unpack_from("<H", b, 10)[0]
    lang = b[29]

    n_fields = (header_size - 32 - 1) // 32
    if n_fields < 0 or header_size > len(b):
        raise ValueError(f"DBF 头长异常 header={header_size} 文件={len(b)}")

    fields = []
    offset = 1  # 首字节系删除标记
    pos = 32
    for _ in range(n_fields):
        name_raw = b[pos:pos + 11]
        name = name_raw.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()
        ftype = chr(b[pos + 11]) if b[pos + 11] else "?"
        flen = b[pos + 16]
        fdec = b[pos + 17]
        fields.append({
            "name": name,
            "type": ftype,
            "type_name": FIELD_TYPES.get(ftype, "unknown"),
            "length": flen,
            "decimals": fdec,
            "offset": offset,
        })
        offset += flen
        pos += 32

    return {
        "version": version,
        "records": n_records,
        "header_size": header_size,
        "record_size": record_size,
        "fields": fields,
        "language_driver": lang,
    }
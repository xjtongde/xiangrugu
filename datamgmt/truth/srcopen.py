# -*- coding: utf-8 -*-
"""srcopen —— 源件 key 读取。key 形如：

    <相对zip路径>::[嵌套zip::...::]<最终成员名>

`::` 为层级分隔：首段是 usedata 下相对路径（外 zip），中间各段是逐层嵌套的内 zip 成员名，
末段是最终成员（shapefile 为「目录/基名」无扩展名；mapinfo 为带扩展名的完整成员名）。
只读源件；不缓存字节以免占用内存（调用方按需 close）。
"""
import io
import os
import zipfile

from . import roots


def open_nested(key):
    """逐层打开，返回 (最内层 zipfile.ZipFile, 最终成员名)。调用方负责 close。"""
    segs = key.split("::")
    z = zipfile.ZipFile(os.path.join(roots.usedata(), segs[0]))
    for inner in segs[1:-1]:
        b = z.read(inner)
        z.close()
        z = zipfile.ZipFile(io.BytesIO(b))
    return z, segs[-1]


def read_member(key, ext="", required=False):
    """读最终成员 + ext 的字节。ext 供 shapefile 拼 ".dbf/.shp/.prj/.cpg"；mapinfo 传 ext=''。"""
    z, member = open_nested(key)
    try:
        try:
            return z.read(member + ext)
        except KeyError:
            if required:
                raise
            return None
    finally:
        z.close()


def read_mapinfo_sibling(key, ext):
    """读 MapInfo 表同基名兄弟文件（.DAT/.MAP/.ID，大小写无关）。key 末段为 .TAB；ext 形如 '.dat'。"""
    z, member = open_nested(key)
    try:
        base = member[:-4] if member.lower().endswith(".tab") else member
        want = base.lower() + ext.lower()
        for n in z.namelist():
            if n.lower() == want:
                return z.read(n)
        return None
    finally:
        z.close()
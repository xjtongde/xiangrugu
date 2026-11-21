#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2：shp 头长度缺陷定点重探（lead 补正派工，基线 b39f8ed）。

缺陷：spatial_probe.py L97 `struct.unpack_from("<i", blob, 24)[0] * 2`
     —— SHP 主文件头 offset 24 文件长度为大端；且乘 2 后字段名 words 实为字节。

本脚本：
1) 把 spatial_probe.py L97 修为 `struct.unpack_from(">i", blob, 24)[0]`
   （保留 16 位字单位，不乘 2）。
2) 仅对 tasks.json header_tasks 中 705 件 .shp：从快照 :ro 隔离提取读头 100B，
   原地补丁 spatial_evidence.jsonl 的对应 shp 记录——
   file_length_words=大端字值；新增 file_length_bytes=words*2、
   length_match=(bytes==成员 size)。其余 2003 行逐字节不动，行序不变。
3) sha_match/shape_type/bbox/size 原值保留（size 以 jsonl 原值为准）。
4) 断言：锚点 asia_contour.shp words==68663434 bytes==137326868；
   705/705 length_match True；任何失配即停（非零退出）。

运行位置：镜像仓根（repo/），与 spatial_probe.py 相同的 SNAP=/data WORK 约定
由本脚本自带 member 读取器完成（宿主直跑，快照只读路径显式给出）。
"""
import hashlib
import io
import json
import os
import re
import shutil
import struct
import sys
import tempfile
import zipfile

REPO = "/opt/mydocker/xiangrugu/build-candidates/spatial-repro-20261120/repo"
PROBE_DIR = os.path.join(REPO, ".spatial-probe-20261120")
SNAP = "/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap"

OLD_LINE = 'rec["file_length_words"] = struct.unpack_from("<i", blob, 24)[0] * 2'
NEW_LINE = 'rec["file_length_words"] = struct.unpack_from(">i", blob, 24)[0]'


def outer_is_plain(relpath):
    return not relpath.lower().endswith((".zip", ".kmz"))


def member_bytes(relpath, chain_parts, leaf):
    """与 spatial_probe.member_bytes 同逻辑（复制而非 import：probe 常量指向容器路径）。"""
    raw_path = os.path.join(SNAP, relpath)
    parts = ([p for p in chain_parts.split("/") if p] if chain_parts else []) \
        + [x for x in leaf.split("/") if x]
    if not chain_parts and len(parts) == 1 and "/" in relpath \
            and not any(x == "" for x in leaf.split("/")) \
            and outer_is_plain(relpath):
        with open(raw_path, "rb") as fh:
            return fh.read()
    data = None
    i = 0
    while i < len(parts):
        z = zipfile.ZipFile(raw_path) if data is None else zipfile.ZipFile(io.BytesIO(data))
        names = z.namelist()
        pick = None
        for j in range(len(parts), i, -1):
            want = "/".join(parts[i:j])
            cand = [n for n in names if n == want]
            if not cand:
                cand = [n for n in names if n.lower() == want.lower()]
            if not cand and "/" in want:
                cand = [n for n in names if n.endswith("/" + want)]
            if cand:
                pick = (cand[0], j)
                break
        if pick is None:
            hop = None
            for j in range(i + 1, len(parts) + 1):
                want = "/".join(parts[i:j])
                cand = [n for n in names
                        if (n == want or n.endswith("/" + want))
                        and n.lower().endswith((".zip", ".kmz"))]
                if cand:
                    hop = (cand[0], j)
                    break
            if hop is None:
                raise KeyError("/".join(parts[i:]))
            data = z.read(hop[0])
            i = hop[1]
            continue
        nm, j = pick
        if j == len(parts):
            return z.read(nm)
        if nm.lower().endswith((".zip", ".kmz")):
            data = z.read(nm)
            i = j
            continue
        raise KeyError("not-an-archive:" + nm)
    raise RuntimeError("unreachable")


def main():
    # ---- 1) probe 源码修正 ----
    pp = os.path.join(PROBE_DIR, "spatial_probe.py")
    src = open(pp).read()
    assert OLD_LINE in src, "probe L97 现文本与预期缺陷行不符，停止"
    src = src.replace(OLD_LINE, NEW_LINE)
    tmp = pp + ".fixtmp"
    open(tmp, "w").write(src)
    os.replace(tmp, pp)
    print("[probe] L97 patched to big-endian words (no *2)")

    # ---- 2) 705 件 shp 重探头 100B ----
    tasks = json.load(open(os.path.join(PROBE_DIR, "tasks.json")))
    shp_tasks = [t for t in tasks["header_tasks"] if t[4] == ".shp"]
    assert len(shp_tasks) == 705, f"shp 任务数 {len(shp_tasks)} != 705"

    fresh = {}
    work = tempfile.mkdtemp(prefix="s2-shp-")
    try:
        for outer, chain, leaf, sha, ext in shp_tasks:
            key = outer + ("!" + "/".join(x for x in [chain, leaf] if x))
            blob = member_bytes(outer, chain, leaf)
            obs = hashlib.sha256(blob).hexdigest()
            if obs != sha:
                print(f"[STOP] sha 失配 {key}", file=sys.stderr)
                sys.exit(2)
            words, = struct.unpack_from(">i", blob[:100], 24)
            fresh[key] = {"file_length_words": words,
                          "file_length_bytes": words * 2,
                          "size_observed": len(blob)}
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # ---- 3) 原地补丁 jsonl：仅 shp 行，其余逐字节不动 ----
    jp = os.path.join(PROBE_DIR, "spatial_evidence.jsonl")
    raw_lines = open(jp, "rb").read().split(b"\n")
    trailing_nl = raw_lines[-1] == b""
    body = raw_lines[:-1] if trailing_nl else raw_lines
    patched = 0
    mismatches = []
    out_lines = []
    for lb in body:
        rec = json.loads(lb.decode("utf-8"))
        k = rec.get("key")
        if rec.get("ext") == ".shp" and k in fresh:
            f = fresh[k]
            rec["file_length_words"] = f["file_length_words"]
            rec["file_length_bytes"] = f["file_length_bytes"]
            ok = (f["file_length_bytes"] == rec.get("size"))
            rec["length_match"] = ok
            if not ok:
                mismatches.append((k, f["file_length_bytes"], rec.get("size")))
            new_lb = json.dumps(rec, ensure_ascii=False).encode("utf-8")
            out_lines.append(new_lb)
            patched += 1
        else:
            out_lines.append(lb)  # 逐字节原样
    assert patched == 705, f"补丁行数 {patched} != 705"
    if mismatches:
        for m in mismatches[:10]:
            print("[STOP] length_match False:", m, file=sys.stderr)
        sys.exit(3)

    # ---- 4) 锚点断言 ----
    anchor = [v for k, v in fresh.items() if k.endswith("asia_contour.shp")]
    assert len(anchor) == 1, f"锚点唯一性失败: {len(anchor)}"
    a = anchor[0]
    assert a["file_length_words"] == 68663434 and a["file_length_bytes"] == 137326868, \
        f"锚点值异常: {a}"

    tmpj = jp + ".s2tmp"
    with open(tmpj, "wb") as fh:
        fh.write(b"\n".join(out_lines))
        if trailing_nl:
            fh.write(b"\n")
    os.replace(tmpj, jp)

    new_sha = hashlib.sha256(open(jp, "rb").read()).hexdigest()
    print(json.dumps({
        "patched_shp_records": patched,
        "length_match_all_true": True,
        "anchor": {"words": a["file_length_words"], "bytes": a["file_length_bytes"]},
        "jsonl_sha256_new": new_sha,
        "probe_sha256_new": hashlib.sha256(open(pp, "rb").read()).hexdigest(),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

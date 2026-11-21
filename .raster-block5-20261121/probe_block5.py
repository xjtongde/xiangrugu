#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 5/6 块首盒：2522 候选逐件只读探测 + 分类登记。

输入 : /opt/mydocker/xiangrugu/build-candidates/raster-other-20261121/candidates.json
快照 : /opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap （只读使用，源件零触）
输出 : probe_evidence.json（同目录 --out）

纪律：
- 宿主侧仅 python3 stdlib；不装依赖、不建镜像、不写库、不执行源 SQL。
- chain 非空成员流式提取到 mktemp -d 隔离目录，sha 全量重算==声明值逐件断言。
- gdalinfo 用现有镜像 runtime-spatial-mapinfo-20261120-a，--rm --network none，挂载 :ro。
- 缺失项如实 null + 原因。
"""
import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

SNAP = "/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap"
GDAL_IMAGE = "xiangrugu:runtime-spatial-mapinfo-20261120-a"

# ---------------------------------------------------------------- magic 表
MAGICS = [
    (b"II*\x00", "TIFF_LE"),
    (b"MM\x00*", "TIFF_BE"),
    (b"\xff\xd8\xff", "JPEG"),
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"GIF87a", "GIF87a"),
    (b"GIF89a", "GIF89a"),
    (b"%PDF", "PDF"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "OLE_CFB"),
    (b"PK\x03\x04", "ZIP"),
    (b"PK\x05\x06", "ZIP_EMPTY"),
    (b"<?xml", "XML"),
    (b"\xef\xbb\xbf<?xml", "XML_BOM"),
    (b"\x1f\x8b", "GZIP"),
    (b"BZh", "BZIP2"),
    (b"7z\xbc\xaf\x27\x1c", "7Z"),
    (b"Rar!\x1a\x07", "RAR"),
    (b"BM", "BMP"),
    (b"ID3", "MP3_ID3"),
    (b"\x00\x00\x01\x00", "ICO"),
]

HTMLISH = re.compile(rb"^\s*<(?:!DOCTYPE\s+html|html|head|body|meta|table|title)\b", re.I)


def sniff_magic(head: bytes) -> str:
    for sig, name in MAGICS:
        if head.startswith(sig):
            return name
    if HTMLISH.match(head[:256]):
        return "HTML"
    # 纯文本启发：可打印比例
    probe = head[:512]
    try:
        probe.decode("utf-8")
        return "TEXT_UTF8"
    except UnicodeDecodeError:
        pass
    try:
        probe.decode("gbk")
        return "TEXT_GBK_LIKELY"
    except UnicodeDecodeError:
        pass
    printable = sum(1 for b in probe if 9 <= b <= 13 or 32 <= b <= 126 or b >= 128)
    return "TEXT_MOSTLY" if printable > len(probe) * 0.9 else "BINARY_UNKNOWN"


CLASSES = {
    "geo_raster", "ordinary_image", "documentation_license", "checksum_ledger",
    "structural_container", "sidecar_companion", "cache", "unknown",
}

IMG_MAGIC = {"JPEG", "PNG", "GIF87a", "GIF89a", "BMP", "ICO"}
TIF_MAGIC = {"TIFF_LE", "TIFF_BE"}
WORLD_EXTS = {"tfw", "tifw", "jgw", "jgwx", "pw", "wld"}
SIDECAR_EXTS = {"aux", "rrd", "ovr", "aux.xml", "qpj", "cpg", "cst", "csvt",
                "qml", "qgs", "qgz", "qgd", "lyr", "sbn", "sbx"}
DOC_EXTS = {"txt", "md", "htm", "html", "pdf", "doc", "rdf", "rels", "rtf"}

SHA_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def classify(ext: str, magic: str, leaf: str, has_world_binding: bool,
             sidecar_kind: str | None, text_purpose: str | None) -> tuple[str, str, list]:
    """返回 (class, purpose, gaps[])。扩展名仅线索，magic+内容为准。"""
    gaps: list = []
    e = (ext or "").lower()
    base = leaf.lower()

    if base == "thumbs.db":
        return "cache", "Windows 缩略图缓存，非业务数据", gaps
    if base.startswith("sha256sums") or (e in ("sha256", "sha512", "md5")):
        return "checksum_ledger", "校验账文件", gaps
    if magic in ("ZIP", "ZIP_EMPTY") or e in ("zip",):
        return "structural_container", "内层容器 ZIP（直接成员数按 inventory 登记，不解包）", gaps
    if magic == "OLE_CFB" and e in ("doc",):
        return "documentation_license", "OLE 复合文档（Word .doc），用途见文本面证据", gaps
    if e in ("aux", "rrd", "ovr") or base.endswith(".aux.xml") or sidecar_kind:
        return "sidecar_companion", sidecar_kind or f"{e} 伴随件（同 stem 绑定）", gaps
    if e in WORLD_EXTS:
        return "sidecar_companion", "世界文件（地理参考原声明载体）", gaps
    if magic in TIF_MAGIC or (e == "tif" and not gaps):
        cls = "geo_raster" if has_world_binding or e == "tif" else "geo_raster"
        return cls, "TIFF 栅格（CRS 依源声明，未证则 unresolved）", gaps
    if magic in IMG_MAGIC or e in ("jpg", "jpeg", "png", "gif", "bmp"):
        if has_world_binding:
            return "geo_raster", "带世界文件绑定的图像＝地理配准栅格", gaps
        return "ordinary_image", "普通图片（无地理参考绑定证据）", gaps
    if magic == "PDF":
        return "documentation_license", "PDF 说明/许可文档", gaps
    if e in ("wmf", "emf"):
        return "ordinary_image", "Windows 图元文件矢量图，读取能力未评估", gaps + ["tool_gap:wmf_reader"]
    if magic in ("XML", "XML_BOM") or e in ("xml", "rels", "rdf"):
        return "documentation_license", text_purpose or "XML 族：用途按内容判定", gaps
    if e in DOC_EXTS or magic in ("TEXT_UTF8", "TEXT_GBK_LIKELY", "TEXT_MOSTLY", "HTML"):
        return "documentation_license", text_purpose or "文本说明类", gaps
    return "unknown", "无法由 magic+扩展名+内容确证", gaps + ["unknown_identity"]


def read_head(path, n=512):
    with open(path, "rb") as f:
        return f.read(n)


def sha_stream(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_member(zip_path: str, ordinals: list, dest_dir: str) -> tuple[str, dict]:
    """按 archive_ordinals 逐层流式提取最末成员到 dest_dir，返回 (本地路径, 链注记)。"""
    cur = zip_path
    note = {}
    tmp_seq = []
    for depth, ordinal in enumerate(ordinals):
        out = os.path.join(dest_dir, f"L{depth}_{ordinal}.bin")
        with zipfile.ZipFile(cur) as zf:
            names = zf.namelist()
            if ordinal >= len(names):
                raise RuntimeError(f"ordinal {ordinal} out of range in {cur} ({len(names)} members)")
            member_name = names[ordinal]
            info = zf.getinfo(member_name)
            if info.is_dir():
                raise RuntimeError(f"member {member_name} is a directory entry")
            with zf.open(info) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
        tmp_seq.append({"layer": depth, "member_index": ordinal, "member_name": member_name,
                        "member_size": info.file_size})
        cur = out
    note["extract_chain"] = tmp_seq
    return cur, note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", default="/opt/mydocker/xiangrugu/build-candidates/raster-other-20261121/candidates.json")
    ap.add_argument("--out", default="/opt/mydocker/xiangrugu/build-candidates/raster-other-20261121/probe_evidence.json")
    ap.add_argument("--limit", type=int, default=0, help="调试用：只处理前 N 件")
    ap.add_argument("--only-ext", default="", help="调试用：逗号分隔扩展名过滤")
    args = ap.parse_args()

    items = json.load(open(args.candidates))
    if args.only_ext:
        keep = set(x.strip().lower() for x in args.only_ext.split(","))
        items = [i for i in items if (i.get("ext") or "").lower() in keep]
    if args.limit:
        items = items[: args.limit]

    work = tempfile.mkdtemp(prefix="blk5-probe-")
    results = []
    t0 = time.time()
    try:
        for idx, it in enumerate(items):
            rec = {
                "identity": {
                    "relative_path": it["relative_path"],
                    "archive_chain": it["archive_chain"],
                    "archive_ordinals": it["archive_ordinals"],
                    "leaf": it["leaf"],
                    "kind": it["kind"],
                    "candidate_source": it["candidate_source"],
                },
                "declared": {"size": it["size"], "sha256": it["sha256"], "signature": it["signature"]},
                "sha_verified": None,
                "magic": None,
                "class": None,
                "purpose": None,
                "raster_meta": None,
                "binding": None,
                "gaps": [],
            }
            try:
                if it["kind"] == "directory":
                    rec["class"] = "structural_container"
                    rec["purpose"] = "目录条目：structural 登记，不读字节"
                    rec["magic"] = "n/a_directory"
                    rec["sha_verified"] = "n/a_directory"
                    results.append(rec)
                    continue

                top = os.path.join(SNAP, it["relative_path"])
                local = None
                if not it["archive_chain"]:
                    local = top
                else:
                    local, note = extract_member(top, it["archive_ordinals"], work)
                    rec["extraction"] = note

                actual_sha = sha_stream(local)
                rec["sha_verified"] = bool(actual_sha == it["sha256"])
                if not rec["sha_verified"]:
                    rec["gaps"].append(f"SHA_MISMATCH actual={actual_sha}")
                    results.append(rec)
                    continue

                head = read_head(local)
                rec["magic"] = sniff_magic(head)
                rec["size_actual"] = os.path.getsize(local)
                if rec["size_actual"] != it["size"]:
                    rec["gaps"].append(f"SIZE_MISMATCH actual={rec['size_actual']}")

                # ---- 分类（world-file 绑定等同 stem 兄弟查找在阶段 B 回填）----
                cls, purpose, gaps = classify((it.get("ext") or ""), rec["magic"], it["leaf"],
                                              False, None, None)
                rec["class"], rec["purpose"], rec["gaps"] = cls, purpose, gaps
            except Exception as e:  # noqa: BLE001 —— 单件失败不吞整体，但必须留证
                rec["class"] = "unknown"
                rec["gaps"].append(f"probe_error:{type(e).__name__}:{e}")
            results.append(rec)
            if (idx + 1) % 250 == 0:
                json.dump(results, open(args.out + ".partial", "w"), ensure_ascii=False)
                print(f"[progress] {idx+1}/{len(items)} elapsed={time.time()-t0:.0f}s", flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    json.dump(results, open(args.out, "w"), ensure_ascii=False, indent=1)
    summary = {
        "total": len(results),
        "by_class": dict(collections.Counter(r["class"] for r in results)),
        "by_magic": dict(collections.Counter(r["magic"] for r in results)),
        "sha_mismatch": sum(1 for r in results if r["sha_verified"] is False),
        "errors": sum(1 for r in results if any(g.startswith("probe_error") for g in r["gaps"])),
        "elapsed_s": round(time.time() - t0, 1),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

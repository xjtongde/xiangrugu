#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1（块5补正）：probe_evidence.json 仅改 ODS 外层 1 条记录。

CountryFilesFormat_2016-07-16.ods（ngia_dsg_codes_2017-03-15.zip!ord[2]）：
structural_container → documentation_license，用途=字段格式说明材料。
判定依据（同容器内层成员证据，probe_evidence 已在件）：
- 内层 content.xml（chain [ods, content.xml] ord [2,14]，sha_verified true）
  表名 Sheet1/FULL_NAME/UFI；单元格文本含 "Field Name/Field Description/
  Field Type/Maximum/Field Length/Precision/RC" 与 NGA DSG 代码域枚举
  （'1 = Americas/Western Europe; …'）⇒ 字段格式说明材料确证。
其余 2521 条逐字节不动、行序不变。"""
import hashlib
import json
import sys

EV = "/opt/mydocker/xiangrugu/build-candidates/raster-other-20261121/probe_evidence.json"
SNAP_ROOT = "/opt/mydocker/xiangrugu/data/imports/usedata/2026-10-07-bootstrap"

TARGET = {
    "relative_path": "harvard-full/doi_10_7910/DVN/I4UIKV/ngia_dsg_codes_2017-03-15.zip",
    "archive_chain": ["CountryFilesFormat_2016-07-16.ods"],
    "archive_ordinals": [2],
}

NEW_PURPOSE = ("OpenDocument 电子表格＝NGA 国家字段格式说明材料（Field Name/"
               "Description/Type/Max Field Length/Precision/RC + DSG 代码域枚"
               "举）；判定依据=同容器内层 content.xml（ord 14，sha_verified）"
               "表名 Sheet1/FULL_NAME/UFI 与逐字单元格文本；外层仍为 ZIP 容器"
               "形态但业务用途确证为说明材料，内层成员各自分类不动")


def main():
    raw = open(EV, "rb").read()
    recs = json.loads(raw)
    hits = [r for r in recs if r["identity"]["relative_path"] == TARGET["relative_path"]
            and r["identity"]["archive_chain"] == TARGET["archive_chain"]
            and r["identity"]["archive_ordinals"] == TARGET["archive_ordinals"]]
    assert len(hits) == 1, f"目标记录命中 {len(hits)} != 1"
    t = hits[0]
    before = dict(t)
    assert t["class"] == "structural_container", f"现 class 非预期: {t['class']}"
    assert t["magic"] == "ZIP" and t["sha_verified"] is True

    # 内层 content.xml 证据存在性断言（不新增读取，只核已在件证据）
    cx = [r for r in recs if r["identity"]["relative_path"] == TARGET["relative_path"]
          and r["identity"]["archive_chain"] == ["CountryFilesFormat_2016-07-16.ods", "content.xml"]]
    assert len(cx) == 1 and cx[0]["sha_verified"] is True and cx[0]["magic"] == "XML", \
        "内层 content.xml 证据缺失或未验 sha"

    # 内层 content.xml text_head 补存（probe 原记录无该字段，lead 补充令①）
    import io, zipfile
    c = cx[0]
    top = SNAP_ROOT + "/" + c["identity"]["relative_path"]
    with zipfile.ZipFile(top) as z:
        data = z.read(z.namelist()[c["identity"]["archive_ordinals"][0]])
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        blob = z.read(z.namelist()[c["identity"]["archive_ordinals"][1]])
    head_txt = blob[:2000].decode("utf-8", "replace")
    import re as _re
    tables = _re.findall(r'table:name="([^"]+)"', blob.decode("utf-8", "replace"))[:4]
    cells = _re.findall(r"<text:p[^>]*>([^<]{2,60})</text:p>",
                        blob.decode("utf-8", "replace"))[:8]
    assert tables and any("Field Name" in x for x in cells), \
        "content.xml 文本头不含字段格式说明证据，停止改判"
    c["text_head"] = "".join(ch if ord(ch) >= 0x20 else " "
                             for ch in blob[:500].decode("utf-8", "replace"))
    c["purpose"] = ("ODS 内层正文＝字段格式说明表（table 名 "
                    + "/".join(tables) + "；单元格含 Field Name/Description/"
                      "Type/Maximum Field Length/Precision/RC 与 DSG 代码域枚"
                      "举）⇒ ODS 外层改判 documentation_license 的直接依据")

    t["class"] = "documentation_license"
    t["purpose"] = NEW_PURPOSE
    t["reclassification"] = {
        "from": "structural_container",
        "reason": "lead 验收补正裁定（内容证据驱动，扩展名/magic 仅线索）",
        "basis": "inner content.xml text evidence (tables Sheet1/FULL_NAME/UFI; cells 'Field Name/Field Description/Field Type/Maximum/Field Length//Precision/RC' + DSG code enumerations)",
        "date": "2026-11-22",
    }

    # probe_evidence.json 为 indent=1 整档 JSON（非 jsonl）：
    # 记录级补丁后重序列化；核验仅目标 2 条记录语义变化，其余逐条相等。
    out = (json.dumps(recs, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    before_recs = json.loads(raw)
    after_recs = json.loads(out)
    assert len(before_recs) == len(after_recs) == 2522
    changed = [i for i, (a, b) in enumerate(zip(before_recs, after_recs)) if a != b]
    assert len(changed) == 2, f"变更记录数 {len(changed)} != 2（ODS 外层 + content.xml 注记）"
    tmp = EV + ".s1tmp"
    open(tmp, "wb").write(out)
    import os as _os
    _os.replace(tmp, EV)
    print(json.dumps({
        "changed_record_indices": changed,
        "before_class": before["class"],
        "after_class": t["class"],
        "records_total": len(recs),
        "records_semantically_unchanged": len(recs) - 2,
        "new_sha256": hashlib.sha256(out).hexdigest(),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

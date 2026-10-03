# -*- coding: utf-8 -*-
"""build_decoding_yaml.py —— 由逐列编码普查(recon/encoding_survey.jsonl)重排 decoding.yaml（段B）。

结构（decode.py 无改动、按 - id:/default:/exceptions: 解析）：
    layers:
      - id: "<图层名小写>"
        default: { encoding: "<该层非ASCII列众数，ASCII-only 层取 utf-8>" }
        exceptions: { "<enc>": [<偏离列>] }
每图层一条；ASCII 列无需例外（ASCII ⊂ 任一编码，解码一致）。只读 recon，不读源件。
"""
import collections
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATAMGMT = os.path.dirname(HERE)
CONFIG = os.path.join(DATAMGMT, "config")
RECON = os.path.join(DATAMGMT, "recon")


def main():
    layers = []
    for line in open(os.path.join(CONFIG, "sources.yaml"), encoding="utf-8"):
        s = line.strip()
        if s.startswith("- ") and '"carrier": "shapefile"' in s:
            e = json.loads(s[2:])
            layers.append(e["target"].split(".", 1)[1].lower())

    truth = collections.defaultdict(dict)
    for line in open(os.path.join(RECON, "encoding_survey.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        if not r["has_nonascii"]:
            continue
        truth[r["target"].split(".", 1)[1].lower()][r["col"]] = r["detected"]

    out = [
        "# 段B 逐图层解码判定表：default=该层非ASCII列众数编码，exceptions=偏离列。",
        "# 由 maintenance/survey_encoding.py 直读源件字节生成；importer/verifier 各自独立解码（§6.1）。",
        "layers:",
    ]
    n_exc = 0
    for L in sorted(set(layers)):
        cols = truth.get(L, {})
        default = collections.Counter(cols.values()).most_common(1)[0][0] if cols else "utf-8"
        excs = collections.defaultdict(list)
        for c, enc in cols.items():
            if enc != default:
                excs[enc].append(c)
        out.append(f"  - id: {json.dumps(L)}")
        out.append("    default:")
        out.append(f"      encoding: {json.dumps(default)}")
        if excs:
            out.append("    exceptions:")
            for enc in sorted(excs):
                cols_list = ", ".join(json.dumps(c) for c in sorted(excs[enc]))
                out.append(f"      {json.dumps(enc)}: [{cols_list}]")
        else:
            out.append("    exceptions: {}")
        n_exc += sum(len(v) for v in excs.values())

    with open(os.path.join(CONFIG, "decoding.yaml"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("图层数:", len(set(layers)), "| 异常列数:", n_exc)


if __name__ == "__main__":
    main()
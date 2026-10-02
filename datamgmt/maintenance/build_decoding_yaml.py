# -*- coding: utf-8 -*-
"""build_decoding_yaml.py —— 由列级普查(recon/column_encoding.jsonl)生成 decoding.yaml（§5.4）。

规则（判定法 §5.4 ①②③④ 之机器落地）：
  族默认：文件名标记(_gbk/_gb/_gb2312→GBK；_big5→Big5；_utf→UTF-8) 优先；
          无标记 → 族内 C 列「big5-only 数 vs gbk-only 数」多数定（多数仍不决→未定）。
  逐列：
    ascii          → 通透（无编码判定需）
    utf-8          → utf-8
    single-byte:latin → cp1252（拉丁变音；§5.4 威妥玛例）
    single-byte:dense → 未定（不装）
    cjk-needs-pin  → 含 utf-8→utf-8；之后 gbk-only→GBK、big5-only→Big5、两者皆有→族默认
  产出：config/decoding.yaml ＋ recon/decoding_families.json（供审）。
只读 recon，不读源件。
"""
import collections
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATAMGMT = os.path.dirname(HERE)
CONFIG = os.path.join(DATAMGMT, "config")
RECON = os.path.join(DATAMGMT, "recon")


def doi(z):
    m = re.search(r'doi_10_7910/DVN/([A-Za-z0-9]+)', z)
    return m.group(1) if m else '?'


def marker(r):
    k = (r.get('zip', '') + r.get('layer', '')).lower()
    if 'big5' in k:
        return 'big5'
    if 'gbk' in k or '_gb' in k or 'gb2312' in k:
        return 'gbk'
    if '_utf' in k:
        return 'utf8'
    return None


def resolve_col(c):
    v = c.get('verdict')
    if v == 'ascii':
        return 'ascii', None
    if v == 'utf-8':
        return 'utf-8', None
    if v == 'single-byte:latin':
        return 'cp1252', '散点高位字节＝拉丁变音（cp1252/latin-1 同区，取 cp1252）'
    if v == 'single-byte:dense':
        return None, '高占比高位字节却无多字节信号 → 未定，不装'
    if v == 'cjk-needs-pin':
        mc = c.get('multi_clean', [])
        if 'utf-8' in mc and not (set(mc) & {'gbk', 'big5', 'cp932'}):
            return 'utf-8', None
        g = 'gbk' in mc
        b = 'big5' in mc
        if g and not b:
            return 'GBK', None
        if b and not g:
            return 'Big5', None
        if g and b:
            return 'AMBIG', 'gbk/big5 皆可解，取族默认'
        return None, '仅 cp932 可解 → 未定，不装'
    return None, '未知 verdict: ' + v


# 语义命名规则（§5.4③ 交叉定谳）：CJK 默认族内，拼音/英文/罗马化令牌列 → cp1252，
# 即便抽样全 ASCII（防罕见 ü/î 被按 CJK 解码而毁）。
_ROMAN_TOKENS = {'py', 'pinyin', 'ascii', 'eng', 'rom', 'roman', 'wade', 'wadegiles', 'gy', 'romanization'}


def is_romanization(name):
    return any(t in _ROMAN_TOKENS for t in name.lower().split('_'))


def q(s):
    return json.dumps(s, ensure_ascii=False)   # 双引号 YAML 标量（合法 YAML）


def emit(yml):
    L = [
        f"title: {q(yml['title'])}",
        f"generator: {q(yml['generator'])}",
        f"default_cp1252_note: {q(yml['default_cp1252_note'])}",
        f"undetermined_policy: {q(yml['undetermined_policy'])}",
        "families:",
    ]
    for f in yml['families']:
        L.append(f"  - id: {q(f['id'])}")
        L.append(f"    doi: {q(f['doi'])}")
        L.append(f"    marker: {f['marker'] if f['marker'] else 'null'}")
        L.append(f"    layers: {f['layers']}")
        L.append("    default:")
        L.append(f"      encoding: {q(f['default']['encoding'])}")
        L.append(f"      evidence: {q(f['default']['evidence'])}")
        if f['exceptions']:
            L.append("    exceptions:")
            for enc, cols in f['exceptions'].items():
                flow = "[" + ", ".join(q(c) for c in cols) + "]"
                L.append(f"      {q(enc)}: {flow}")
        else:
            L.append("    exceptions: {}")
        und = f['undetermined']
        flow = "[" + ", ".join(q(c) for c in und) + "]" if und else "[]"
        L.append(f"    undetermined: {flow}")
    return "\n".join(L) + "\n"


def main():
    rows = [json.loads(l) for l in open(os.path.join(RECON, "column_encoding.jsonl"), encoding="utf-8")]
    fam = collections.defaultdict(lambda: {'layers': 0, 'cols': collections.defaultdict(list)})
    for r in rows:
        if 'columns' not in r:
            continue
        m = marker(r)
        key = (doi(r['zip']), m)
        fam[key]['layers'] += 1
        for n, c in r['columns'].items():
            fam[key]['cols'][n].append(c)

    families = []
    for (d, m), f in sorted(fam.items(), key=lambda kv: (kv[0][0], kv[0][1] or '')):
        # 族默认
        if m == 'gbk':
            default = 'GBK'
        elif m == 'big5':
            default = 'Big5'
        elif m == 'utf8':
            default = 'utf-8'
        else:
            big5_only = gbk_only = 0
            for n, cs in f['cols'].items():
                for c in cs:
                    if c.get('verdict') == 'cjk-needs-pin':
                        mc = c.get('multi_clean', [])
                        if 'big5' in mc and 'gbk' not in mc:
                            big5_only += 1
                        if 'gbk' in mc and 'big5' not in mc:
                            gbk_only += 1
            if max(big5_only, gbk_only) == 0:
                default = 'GBK'   # 无 CJK 列，默认无意义，取 GBK 占位
            elif big5_only >= gbk_only:
                default = 'Big5'
            else:
                default = 'GBK'

        # 逐列例外
        exc = collections.defaultdict(list)
        undet = []
        for n, cs in f['cols'].items():
            # 取该列在族内的多数 verdict
            encs = [resolve_col(c)[0] for c in cs]
            count = collections.Counter(e for e in encs if e)
            if not count:
                continue
            enc = count.most_common(1)[0][0]
            if enc == 'ascii' and default in ('GBK', 'Big5') and is_romanization(n):
                enc = 'cp1252'      # 语义命名规则
            if enc in ('ascii', default):
                continue
            if enc == 'AMBIG':
                enc = default   # 族默认
                continue
            if enc is None:
                undet.append(n)
            else:
                exc[enc].append(n)

        families.append({
            "id": f"DOI_{d}_{m or 'nomark'}",
            "doi": d, "marker": m, "layers": f['layers'],
            "default": {"encoding": default,
                        "evidence": (f"文件名标记={m}" if m else
                                     "无标记；族内 big5-only/gbk-only 多数裁决＋字符实证（如 Hartwell CHARACTER_=藍田縣=Big5）")},
            "exceptions": {k: sorted(set(v)) for k, v in sorted(exc.items())},
            "undetermined": sorted(undet),
        })

    yml = {
        "title": "列级解码判定表（§5.4）——阶段二生成",
        "generator": "datamgmt/maintenance/build_decoding_yaml.py",
        "default_cp1252_note": "single-byte:latin 例外统一取 cp1252（§5.4 威妥玛 ü=0xFC 例证；cp1252 系 Windows 西欧默认）",
        "undetermined_policy": "undetermined 列显式不装（§5.4④ 宁缺勿错），装载时应在证书声明缺列",
        "families": families,
    }
    os.makedirs(CONFIG, exist_ok=True)
    with open(os.path.join(CONFIG, "decoding.yaml"), "w", encoding="utf-8") as fh:
        fh.write(emit(yml))
    with open(os.path.join(RECON, "decoding_families.json"), "w", encoding="utf-8") as fh:
        json.dump(yml, fh, ensure_ascii=False, indent=2)

    n_exc = sum(len(f['exceptions']) for f in families)
    n_und = sum(len(f['undetermined']) for f in families)
    print(f"族数={len(families)} | 例外族={n_exc} | 未定列族内项={n_und}")
    for f in families:
        if f['exceptions'] or f['undetermined']:
            print(f"  {f['id']:26s} default={f['default']['encoding']:6s} exc={f['exceptions']} undet={len(f['undetermined'])}列")


if __name__ == "__main__":
    main()
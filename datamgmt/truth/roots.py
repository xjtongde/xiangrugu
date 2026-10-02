# -*- coding: utf-8 -*-
"""统一根装载：P-17 根只许出自 config/roots.yaml，代码不硬编码绝对路径。

优先 yaml.safe_load；无 pyyaml 时按 roots.yaml（我方自维护、结构稳定）做最小提取。
"""
import os
import re
import sys

_ROOTS = os.path.join(os.path.dirname(__file__), "..", "config", "roots.yaml")
_ROOTS = os.path.realpath(_ROOTS)


def load(key):
    """key ∈ {'usedata', 'download'}：返回对应根绝对路径。"""
    txt = open(_ROOTS, encoding="utf-8").read()
    try:
        import yaml  # type: ignore
        d = yaml.safe_load(txt)
        return d["roots"][key]["path"]
    except ImportError:
        lines = txt.splitlines()
        for i, ln in enumerate(lines):
            if re.match(r"^  " + key + r":\s*(#.*)?$", ln):
                for ln2 in lines[i + 1:i + 3]:
                    m = re.match(r"^\s+path:\s*(\S+)\s*(#.*)?$", ln2)
                    if m:
                        return m.group(1)
        sys.exit(f"truth.roots: 无法从 config/roots.yaml 提取 roots.{key}.path")


def usedata():
    return load("usedata")


def download():
    return load("download")
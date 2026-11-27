#!/usr/bin/env python3
"""Assertion: every artifact claiming "X was verified" pins the version X lives in.

a02 第十六轮提的第四问，机器化：
  1. 各 evidence 的 code_pin、report.verify_commit、命令 --code-commit 三者相等；
  2. 被测加固（runner/entry 的改动）不晚于该 code_pin —— 等值检查查不出这一条，
     因为错位时三处可以自洽地都写着旧值，只有拿"加固发生在哪个提交"比对才暴露。

退出码 0 = 一致；1 = 不一致。
"""
import json, pathlib, re, subprocess, sys

V = pathlib.Path(__file__).resolve().parent
REPO = V.parent


# Resolve the repository ONCE from this file's location, and refuse to run if that
# does not land in a git work tree. Without this guard the assertions below would be
# evaluated against empty strings and silently pass -- the "looks verified" failure
# this script exists to prevent. (Found by a02: a copy of this file run from a
# detached worktree resolved REPO to a non-repo and skipped the load-bearing check.)
GIT_DIR = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--git-dir"],
                         capture_output=True, text=True)
if GIT_DIR.returncode != 0:
    print(json.dumps({"ok": False,
                      "problems": [f"not a git work tree: {REPO}"],
                      "detail": GIT_DIR.stderr.strip()[:200]}, ensure_ascii=False))
    raise SystemExit(1)


def git(*args):
    proc = subprocess.run(["git", "-C", str(REPO), *args],
                          capture_output=True, text=True)
    return proc.stdout.strip()


def main():
    report = json.loads((V / "report.json").read_text(encoding="utf-8"))
    claim = report["verify_commit"]
    problems = []

    pins = {}
    for ev in sorted((V / "evidence").glob("*.json")):
        d = json.loads(ev.read_text(encoding="utf-8"))
        pin = (d.get("code_pin") or {}).get("commit")
        if pin:
            pins[ev.name] = pin
            if pin != claim:
                problems.append(f"{ev.name}: code_pin={pin[:12]} != report.verify_commit={claim[:12]}")

    cmd = V / "actual-isolation-command.sh"
    if cmd.exists():
        m = re.search(r"--code-commit\s+([0-9a-f]{40})", cmd.read_text(encoding="utf-8"))
        if m and m.group(1) != claim:
            problems.append(f"actual-isolation-command.sh: --code-commit={m.group(1)[:12]} != {claim[:12]}")

    # The load-bearing part: the code under test must not postdate the pin.
    for path in ("datamgmt/src/xiangrugu_datamgmt/cbdb_social_addr_runner.py",
                 "datamgmt/src/xiangrugu_datamgmt/cbdb_social_addr_entry.py"):
        last = git("log", "-1", "--format=%H", claim, "--", path)
        head = git("log", "-1", "--format=%H", "HEAD", "--", path)
        # Fail CLOSED. An empty result means the commit or the path could not be
        # resolved (shallow clone, bad pin, wrong tree). Treating that as "no
        # problem" is exactly the silent-pass this check is meant to rule out.
        if not last or not head:
            problems.append(
                f"{path}: cannot resolve last-change commits "
                f"(pinned={bool(last)}, head={bool(head)}) — refusing to pass")
        elif last != head:
            problems.append(
                f"{path}: last change in pinned tree {last[:12]} != last change at HEAD "
                f"{head[:12]} — evidence may predate a later fix")

    print(json.dumps({"verify_commit": claim, "evidence_pins": pins,
                      "distinct_pins": sorted(set(pins.values())),
                      "problems": problems, "ok": not problems},
                     ensure_ascii=False, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())

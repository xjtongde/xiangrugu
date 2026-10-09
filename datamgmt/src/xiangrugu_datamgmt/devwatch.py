"""Run development tests whenever the controlled source mirror changes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


IGNORED_PARTS = frozenset({".git", "__pycache__", ".pytest_cache", "data", "usedata"})
WATCHED_NAMES = frozenset({"Dockerfile", ".dockerignore", ".devwatch-probe"})
WATCHED_SUFFIXES = frozenset({".md", ".py", ".toml", ".yaml", ".yml", ".in", ".lock", ".ps1", ".sh"})


def snapshot(root: Path) -> dict[str, tuple[int, int]]:
    """Return a cheap, deterministic signature of development inputs."""
    result: dict[str, tuple[int, int]] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in IGNORED_PARTS for part in relative.parts) or not path.is_file():
            continue
        if path.name not in WATCHED_NAMES and path.suffix not in WATCHED_SUFFIXES:
            continue
        stat = path.stat()
        result[relative.as_posix()] = (stat.st_mtime_ns, stat.st_size)
    return result


def write_status(path: Path, *, run: int, returncode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {
                "run": run,
                "returncode": returncode,
                "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/workspace"))
    parser.add_argument("--tests", nargs="+", default=["datamgmt/tests/unit"])
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument(
        "--status",
        type=Path,
        default=Path(os.environ.get("XIANGRUGU_DEV_STATUS", "/data/var/devwatch/status.json")),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stopping = False

    def request_stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    previous: dict[str, tuple[int, int]] | None = None
    run = 0
    while not stopping:
        current = snapshot(args.root)
        if current != previous:
            run += 1
            print(f"devwatch: change detected; test run {run}", flush=True)
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", *args.tests, "-q"],
                cwd=args.root,
                check=False,
            )
            write_status(args.status, run=run, returncode=completed.returncode)
            print(f"devwatch: test run {run} exited {completed.returncode}", flush=True)
            previous = current
        time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

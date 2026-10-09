"""One-shot bridge invoked by the trusted host transport, with no source mount."""
import argparse
from pathlib import Path
import sys

from .config import ConfigError, load_config
from .snapshots import SnapshotError, StreamSnapshot, canonical_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "copy", "check", "finish"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--source-path", required=True)
    parser.add_argument("--device", type=int, required=True)
    parser.add_argument("--inode", type=int, required=True)
    parser.add_argument("--vcs-ref", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--reserve-bytes", type=int, default=10 * 1024**3)
    args = parser.parse_args()
    try:
        config = load_config(args.config, environ={})
        if str(config.source.path) != args.source_path:
            raise SnapshotError("Host source path differs from authority configuration")
        run = StreamSnapshot(
            source_path=args.source_path, snapshot_root=config.snapshot_root,
            evidence_root=config.evidence_root, snapshot_id=args.snapshot_id,
            vcs_ref=args.vcs_ref, image_digest=args.image_digest, reserve_bytes=args.reserve_bytes,
            source_identity={"resolved_path": args.source_path, "device": args.device, "inode": args.inode},
        )
        if args.phase == "finish":
            certificate = run.finish()
            print(canonical_json({"status": "VERIFIED", "manifest_sha256": certificate["manifest_sha256"],
                                  "members": len(certificate["members"])}))
        else:
            getattr(run, args.phase)(sys.stdin.buffer)
            print(canonical_json({"phase": args.phase, "status": "OK"}))
        return 0
    except (SnapshotError, ConfigError, OSError):
        print("Snapshot transfer refused; no new completion certificate.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

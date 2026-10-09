"""Copy authoritative source bytes into independently verified project snapshots."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tarfile


class SnapshotError(ValueError):
    pass


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def inventory(root: Path) -> list[dict]:
    if root.is_symlink() or not root.is_dir():
        raise SnapshotError("Input must be an existing directory, not a symbolic link")
    members = []
    def fail_on_walk_error(error):
        raise SnapshotError("A source or snapshot directory cannot be enumerated") from None

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=fail_on_walk_error):
        for name in sorted(dirs + files):
            member = Path(directory) / name
            mode = member.lstat().st_mode
            relative = member.relative_to(root).as_posix()
            if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise SnapshotError("Symbolic links and special members require explicit disposition")
            entry = {"path": relative, "kind": "directory" if stat.S_ISDIR(mode) else "file"}
            if entry["kind"] == "file":
                entry.update(size=member.stat().st_size, sha256=sha256_file(member))
            members.append(entry)
    return sorted(members, key=lambda entry: entry["path"])


def source_identity(source: Path, expected: Path) -> dict:
    if not source.is_absolute() or source != expected or source.resolve(strict=True) != expected:
        raise SnapshotError("Source does not match the configured authority path")
    if not source.is_dir() or source.is_symlink():
        raise SnapshotError("Source is not a regular directory")
    metadata = source.stat()
    return {"resolved_path": str(source), "device": metadata.st_dev, "inode": metadata.st_ino}


def write_json_exclusive(path: Path, value) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(canonical_json(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def create_snapshot(
    source: Path, *, expected_source: Path, snapshot_root: Path, evidence_root: Path,
    snapshot_id: str, vcs_ref: str, image_digest: str, reserve_bytes: int = 0,
) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", snapshot_id):
        raise SnapshotError("Invalid snapshot identifier")
    if not re.fullmatch(r"[0-9a-f]{40}", vcs_ref) or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_digest):
        raise SnapshotError("Valid Git revision and image digest are required")
    if reserve_bytes < 0:
        raise SnapshotError("Disk reserve must not be negative")
    try:
        identity = source_identity(source, expected_source)
        for output in (snapshot_root, evidence_root):
            resolved = output.resolve()
            if not output.is_absolute() or resolved == source or source in resolved.parents or resolved in source.parents:
                raise SnapshotError("Output roots must be separate from the authority")
            if resolved != output:
                raise SnapshotError("Output roots must not traverse symbolic links")
        if snapshot_root == evidence_root or snapshot_root in evidence_root.parents or evidence_root in snapshot_root.parents:
            raise SnapshotError("Snapshot and evidence roots must be separate")
        before = inventory(source)
        snapshot_root.mkdir(parents=True, exist_ok=True)
        evidence_root.mkdir(parents=True, exist_ok=True)
        destination = snapshot_root / snapshot_id
        staging = snapshot_root / ("." + snapshot_id + ".incomplete")
        certificate_path = evidence_root / (snapshot_id + ".json")
        failed_path = evidence_root / (snapshot_id + ".failed.json")
        if any(path.exists() or path.is_symlink() for path in (destination, staging, certificate_path, failed_path)):
            raise SnapshotError("Snapshot identifier already exists; choose a new version")
        required = sum(entry.get("size", 0) for entry in before)
        if shutil.disk_usage(snapshot_root).free < required + reserve_bytes:
            raise SnapshotError("Insufficient free space for snapshot and reserve")
        # Exclusive reservation blocks concurrent writers using this snapshot ID.
        staging.mkdir()
        started = datetime.now(timezone.utc).isoformat()
        try:
            for entry in before:
                target = staging / entry["path"]
                if entry["kind"] == "directory":
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source / entry["path"], target, follow_symlinks=False)
            if inventory(staging) != before:
                raise SnapshotError("Copied members differ from authority manifest")
            if inventory(source) != before or source_identity(source, expected_source) != identity:
                raise SnapshotError("Authority changed during copying")
            if destination.exists() or destination.is_symlink():
                raise SnapshotError("Destination appeared during copying")
            staging.rename(destination)
            certificate = {
                "version": 1, "snapshot_id": snapshot_id, "source_path": str(source),
                "source_identity": identity, "members": before,
                "manifest_sha256": digest(before), "vcs_ref": vcs_ref,
                "image_digest": image_digest, "started_at": started,
                "verified_at": datetime.now(timezone.utc).isoformat(), "status": "VERIFIED",
            }
            write_json_exclusive(certificate_path, certificate)
            return certificate
        except (OSError, SnapshotError) as error:
            write_json_exclusive(failed_path, {"snapshot_id": snapshot_id, "status": "FAILED", "reason": type(error).__name__})
            raise SnapshotError("Snapshot failed; partial copy retained, no completion certificate") from None
    except OSError:
        raise SnapshotError("Source or output cannot be accessed") from None


def verify_snapshot(root: Path, certificate_path: Path, *, expected_source: Path) -> dict:
    try:
        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
        if certificate["version"] != 1 or certificate["status"] != "VERIFIED":
            raise SnapshotError("Snapshot lacks a valid completion certificate")
        if certificate["source_path"] != str(expected_source) or certificate["snapshot_id"] != root.name:
            raise SnapshotError("Snapshot certificate refers to another origin or version")
        members = certificate["members"]
        if digest(members) != certificate["manifest_sha256"] or inventory(root) != members:
            raise SnapshotError("Snapshot content or manifest changed")
        return certificate
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        raise SnapshotError("Snapshot or certificate is missing or invalid") from None


def read_snapshot_tar(stream, *, destination: Path | None = None,
                      max_bytes: int = 64 * 1024**3, max_members: int = 100_000) -> list[dict]:
    """Receive a restricted USTAR transport; never use archive extraction APIs.

    Host GNU tar must use --format=ustar --hard-dereference. Extended headers,
    sparse files, links and special files are deliberately unsupported.
    """
    def exact(size):
        chunks = []
        remaining = size
        while remaining:
            chunk = stream.read(remaining)
            if not chunk:
                raise SnapshotError("Truncated source transport")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    if max_bytes < 0 or max_members < 1:
        raise SnapshotError("Invalid transport budget")
    if destination is not None and (destination.is_symlink() or not destination.is_dir() or any(destination.iterdir())):
        raise SnapshotError("Receiver requires a new empty staging directory")
    members, seen, total, headers = [], set(), 0, 0
    root_seen = False
    try:
        while True:
            header = exact(512)
            if header == bytes(512):
                if exact(512) != bytes(512):
                    raise SnapshotError("Invalid transport terminator")
                # GNU tar pads the last record with zeros; disallow extra archives.
                padding = 0
                while chunk := stream.read(1024):
                    padding += len(chunk)
                    if any(chunk) or padding > 64 * 1024:
                        raise SnapshotError("Unexpected transport trailing bytes")
                if not root_seen:
                    raise SnapshotError("Source root header is missing")
                return sorted(members, key=lambda entry: entry["path"])
            headers += 1
            if headers > max_members + 1:
                raise SnapshotError("Transport member budget exceeded")
            member = tarfile.TarInfo.frombuf(header, "utf-8", "strict")
            if header[257:263] != b"ustar\x00" or member.type not in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE):
                raise SnapshotError("Only ordinary USTAR files and directories are supported")
            name = member.name
            if name in (".", "./") and member.isdir() and not root_seen and headers == 1:
                if member.size != 0:
                    raise SnapshotError("Directory payload is forbidden")
                root_seen = True
                continue
            if not root_seen:
                raise SnapshotError("Source root must be the first member")
            if name.startswith("./"):
                name = name[2:]
            if member.isdir() and name.endswith("/"):
                name = name[:-1]
            if (not name or name.startswith("/") or "\\" in name or "\x00" in name
                    or any(part in ("", ".", "..") for part in name.split("/"))):
                raise SnapshotError("Noncanonical source transport path")
            if name in seen:
                raise SnapshotError("Duplicate source transport path")
            seen.add(name)
            if member.size < 0 or member.size > 8 * 1024**3 or total + member.size > max_bytes:
                raise SnapshotError("Transport byte budget exceeded")
            entry = {"path": name, "kind": "directory" if member.isdir() else "file"}
            target = destination / name if destination is not None else None
            if member.isdir():
                if member.size:
                    raise SnapshotError("Directory payload is forbidden")
                if target is not None:
                    target.mkdir(parents=True, exist_ok=True)
            else:
                total += member.size
                hasher = hashlib.sha256()
                output = None
                if target is not None:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    output = target.open("xb")
                try:
                    remaining = member.size
                    while remaining:
                        chunk = exact(min(remaining, 1024 * 1024))
                        hasher.update(chunk)
                        if output is not None:
                            output.write(chunk)
                        remaining -= len(chunk)
                    if output is not None:
                        output.flush()
                        os.fsync(output.fileno())
                finally:
                    if output is not None:
                        output.close()
                if any(exact((-member.size) % 512)):
                    raise SnapshotError("Invalid file padding")
                entry.update(size=member.size, sha256=hasher.hexdigest())
            members.append(entry)
    except (OSError, UnicodeError, tarfile.HeaderError):
        raise SnapshotError("Source transport is invalid or inaccessible") from None


class StreamSnapshot:
    """Three source reads and independent disk reads before any certificate."""

    def __init__(self, *, source_path: str, snapshot_root: Path, evidence_root: Path,
                 snapshot_id: str, vcs_ref: str, image_digest: str,
                 source_identity: dict, reserve_bytes: int = 0):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", snapshot_id):
            raise SnapshotError("Invalid snapshot identifier")
        if not re.fullmatch(r"[0-9a-f]{40}", vcs_ref) or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_digest):
            raise SnapshotError("Valid revision and image digest required")
        source = Path(source_path)
        if not source.is_absolute() or ".." in source.parts or reserve_bytes < 0:
            raise SnapshotError("Invalid source or disk reserve")
        if (source_identity.get("resolved_path") != source_path
                or any(type(source_identity.get(key)) is not int for key in ("device", "inode"))):
            raise SnapshotError("Host-observed source identity is required")
        for output in (snapshot_root, evidence_root):
            if (not output.is_absolute() or output.resolve() != output or source == output
                    or source in output.parents or output in source.parents):
                raise SnapshotError("Output roots must be separate canonical directories")
        if snapshot_root == evidence_root or snapshot_root in evidence_root.parents or evidence_root in snapshot_root.parents:
            raise SnapshotError("Snapshot and evidence roots must be separate")
        self.identity = dict(source_identity)
        self.reserve = reserve_bytes
        self.root, self.evidence = snapshot_root, evidence_root
        self.staging = snapshot_root / ("." + snapshot_id + ".incomplete")
        self.destination = snapshot_root / snapshot_id
        self.prepared = evidence_root / (snapshot_id + ".prepared.json")
        self.copied = evidence_root / (snapshot_id + ".copied.json")
        self.checked = evidence_root / (snapshot_id + ".checked.json")
        self.failed = evidence_root / (snapshot_id + ".failed.json")
        self.certificate = evidence_root / (snapshot_id + ".json")
        self.provenance = {"snapshot_id": snapshot_id, "source_path": source_path,
                           "vcs_ref": vcs_ref, "image_digest": image_digest,
                           "source_status": "dirty", "source_identity": self.identity}

    def prepare(self, stream):
        self.root.mkdir(parents=True, exist_ok=True)
        self.evidence.mkdir(parents=True, exist_ok=True)
        if any(path.exists() or path.is_symlink() for path in (
                self.destination, self.staging, self.prepared, self.copied, self.checked, self.failed, self.certificate)):
            raise SnapshotError("Snapshot identifier already exists")
        self.staging.mkdir()  # Exclusive reservation; interrupted transfers stay visible.
        try:
            members = read_snapshot_tar(stream)
            if shutil.disk_usage(self.root).free < sum(item.get("size", 0) for item in members) + self.reserve:
                raise SnapshotError("Insufficient disk space and reserve")
            write_json_exclusive(self.prepared, {
                **self.provenance, "members": members, "manifest_sha256": digest(members),
                "started_at": datetime.now(timezone.utc).isoformat(),
            })
        except (OSError, SnapshotError):
            self._fail("prepare")
            raise

    def _before(self):
        if self.failed.exists() or self.certificate.exists() or self.destination.exists():
            raise SnapshotError("Failed or completed version cannot be reused")
        try:
            before = json.loads(self.prepared.read_text(encoding="utf-8"))
            if (any(before.get(key) != value for key, value in self.provenance.items())
                    or digest(before["members"]) != before["manifest_sha256"]
                    or not self.staging.is_dir() or self.staging.is_symlink()):
                raise SnapshotError("Snapshot provenance changed")
            return before
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            raise SnapshotError("Prepared evidence is missing or invalid") from None

    def _fail(self, phase):
        if not self.failed.exists():
            write_json_exclusive(self.failed, {"snapshot_id": self.provenance["snapshot_id"],
                                              "status": "FAILED", "phase": phase})

    def copy(self, stream):
        before = self._before()
        try:
            if self.copied.exists():
                raise SnapshotError("Copy phase already completed")
            if shutil.disk_usage(self.root).free < sum(item.get("size", 0) for item in before["members"]) + self.reserve:
                raise SnapshotError("Disk budget changed")
            received = read_snapshot_tar(stream, destination=self.staging)
            if received != before["members"] or inventory(self.staging) != before["members"]:
                raise SnapshotError("Source or copied members changed")
            write_json_exclusive(self.copied, {"manifest_sha256": digest(received)})
        except (OSError, SnapshotError):
            self._fail("copy")
            raise

    def check(self, stream):
        before = self._before()
        try:
            receipt = json.loads(self.copied.read_text(encoding="utf-8"))
            after = read_snapshot_tar(stream)
            if (receipt != {"manifest_sha256": before["manifest_sha256"]}
                    or after != before["members"] or inventory(self.staging) != before["members"]):
                raise SnapshotError("Source or snapshot changed after copy")
            write_json_exclusive(self.checked, {"manifest_sha256": digest(after)})
        except (OSError, KeyError, TypeError, json.JSONDecodeError, SnapshotError):
            self._fail("check")
            raise SnapshotError("Snapshot failed; no completion certificate") from None

    def finish(self):
        # The deployment wrapper calls this ONLY after every pipe exits zero.
        before = self._before()
        try:
            receipt = json.loads(self.checked.read_text(encoding="utf-8"))
            if (receipt != {"manifest_sha256": before["manifest_sha256"]}
                    or inventory(self.staging) != before["members"]):
                raise SnapshotError("Final snapshot check failed")
            certificate = {**before, "version": 1, "status": "VERIFIED",
                           "transport": "gnu-tar-ustar-stdin-v1", "source_passes": 3,
                           "verified_at": datetime.now(timezone.utc).isoformat()}
            self.staging.rename(self.destination)
            write_json_exclusive(self.certificate, certificate)
            return certificate
        except (OSError, KeyError, TypeError, json.JSONDecodeError, SnapshotError):
            self._fail("finish")
            raise SnapshotError("Snapshot failed; no completion certificate") from None

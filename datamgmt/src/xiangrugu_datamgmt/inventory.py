"""Read-only, deterministic inventory. Incomplete evidence is never success.

Scan a stable, verified snapshot. Temporary spools live outside the source tree;
archive paths are evidence only and are never filesystem extraction targets.
"""
from dataclasses import asdict, dataclass
import hashlib
import heapq
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import zipfile
import zlib

from .archive import ArchiveLimit, preflight_zip
from .identity import canonical_relative_path
from .signatures import detect_signature


@dataclass(frozen=True)
class InventoryEntry:
    relative_path: str
    archive_chain: tuple[str, ...] = ()
    archive_ordinals: tuple[int, ...] = ()
    kind: str = "file"
    size: int | None = None
    sha256: str | None = None
    signature: str = "unknown"


@dataclass(frozen=True)
class InventoryIssue:
    code: str
    relative_path: str
    archive_chain: tuple[str, ...] = ()
    archive_ordinals: tuple[int, ...] = ()
    detail: str = ""
    blocking: bool = True


@dataclass(frozen=True)
class ChecksumAssertion:
    ledger: str
    line: int
    raw_name: str
    target: str
    expected_sha256: str
    matched: bool
    archive_chain: tuple[str, ...] = ()
    archive_ordinals: tuple[int, ...] = ()


@dataclass(frozen=True)
class InventoryManifest:
    entries: tuple[InventoryEntry, ...]
    issues: tuple[InventoryIssue, ...]
    checksums: tuple[ChecksumAssertion, ...]
    limits: tuple[tuple[str, int], ...]

    @property
    def complete(self):
        return not any(issue.blocking for issue in self.issues)

    def canonical_bytes(self):
        return json.dumps({"version": 1, "complete": self.complete, **asdict(self)},
                          ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @property
    def sha256(self):
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


class InventoryBuilder:
    def __init__(self, *, max_member_bytes=8 * 1024**3, max_total_bytes=64 * 1024**3,
                 max_members=100000, max_depth=8, max_ratio=1000,
                 max_central_bytes=16 * 1024**2, max_checksum_bytes=8 * 1024**2,
                 temp_root="/data/var"):
        self.temp_root = Path(temp_root)
        if not self.temp_root.is_absolute():
            raise ValueError("temp_root must be absolute")
        self.limits = dict(max_member_bytes=max_member_bytes, max_total_bytes=max_total_bytes,
                           max_members=max_members, max_depth=max_depth, max_ratio=max_ratio,
                           max_central_bytes=max_central_bytes, max_checksum_bytes=max_checksum_bytes)
        for name, value in self.limits.items():
            if type(value) is not int or value < (0 if name == "max_depth" else 1):
                raise ValueError(f"invalid {name}")

    def scan(self, root) -> InventoryManifest:
        # State belongs to a scan, so a builder can be safely reused.
        return _Scan(self.limits, self.temp_root).run(Path(root))


class _Scan:
    def __init__(self, limits, temp_root):
        self.limits = limits
        self.temp_root = temp_root
        self.entries = []
        self.issues = []
        self.ledgers = []
        self.count = 0
        self.total = 0
        self.checksum_total = 0

    def issue(self, code, entry, detail="", blocking=True):
        self.issues.append(InventoryIssue(code, entry.relative_path, entry.archive_chain,
                                          entry.archive_ordinals, detail, blocking))

    def reserve(self, entry):
        if self.count >= self.limits["max_members"]:
            self.issue("count_limit", entry)
            return False
        self.count += 1
        return True

    def run(self, root):
        location = InventoryEntry(".", kind="directory")
        try:
            if root.absolute() != root.resolve() or not stat.S_ISDIR(root.lstat().st_mode):
                self.issue("unsafe_root", location)
            elif self.temp_root.resolve().is_relative_to(root.resolve()):
                self.issue("unsafe_temp_root", location)
            else:
                self.directory(root, "")
        except OSError as error:
            self.issue("read_error", location, f"errno={error.errno}")
        checksums = self.parse_ledgers()
        key = lambda entry: (entry.relative_path, entry.archive_ordinals, entry.archive_chain)
        return InventoryManifest(tuple(sorted(self.entries, key=key)),
                                 tuple(sorted(self.issues, key=lambda issue: (*key(issue), issue.code, issue.detail))),
                                 tuple(checksums), tuple(sorted(self.limits.items())))

    def collisions(self, names, parent):
        seen = set()
        folded = set()
        for name in names:
            if name in seen:
                self.issue("duplicate_member", parent, name)
            elif name.casefold() in folded:
                self.issue("case_collision", parent, name)
            seen.add(name)
            folded.add(name.casefold())

    def directory(self, path, relative):
        parent = InventoryEntry(relative or ".", kind="directory")
        try:
            with os.scandir(path) as directory:
                remaining = self.limits["max_members"] - self.count
                children = heapq.nsmallest(remaining + 1, directory, key=lambda child: child.name)
                if len(children) > remaining:
                    self.issue("count_limit", parent)
        except OSError as error:
            self.issue("read_error", parent, f"errno={error.errno}")
            return
        self.collisions([child.name for child in children], parent)
        for child in children:
            name = f"{relative}/{child.name}" if relative else child.name
            entry = InventoryEntry(name)
            if not self.reserve(entry):
                return
            try:
                metadata = child.stat(follow_symlinks=False)
                if stat.S_ISLNK(metadata.st_mode):
                    self.entries.append(InventoryEntry(name, kind="symlink"))
                    self.issue("symlink", entry)
                elif stat.S_ISDIR(metadata.st_mode):
                    self.entries.append(InventoryEntry(name, kind="directory"))
                    self.directory(Path(child.path), name)
                elif stat.S_ISREG(metadata.st_mode):
                    fd = os.open(child.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                    with os.fdopen(fd, "rb") as stream:
                        before = os.fstat(stream.fileno())
                        if not stat.S_ISREG(before.st_mode) or (before.st_dev, before.st_ino) != (metadata.st_dev, metadata.st_ino):
                            self.issue("source_changed", entry)
                            self.entries.append(entry)
                            continue
                        self.read_member(stream, entry, before.st_size)
                        after = os.fstat(stream.fileno())
                        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                            self.issue("source_changed", entry)
                else:
                    self.entries.append(InventoryEntry(name, kind="special"))
                    self.issue("special_file", entry)
            except OSError as error:
                self.entries.append(entry)
                self.issue("read_error", entry, f"errno={error.errno}")

    def read_member(self, stream, entry, declared_size):
        if self.total > self.limits["max_total_bytes"] or declared_size > self.limits["max_total_bytes"] - self.total:
            self.entries.append(InventoryEntry(entry.relative_path, entry.archive_chain, entry.archive_ordinals, size=declared_size))
            self.issue("total_limit", entry)
            return
        if declared_size > self.limits["max_member_bytes"]:
            self.entries.append(InventoryEntry(entry.relative_path, entry.archive_chain, entry.archive_ordinals, size=declared_size))
            self.issue("member_limit", entry)
            return
        digest = hashlib.sha256()
        size = 0
        prefix = b""
        name = entry.archive_chain[-1] if entry.archive_chain else entry.relative_path
        is_checksum = PurePosixPath(name).name.startswith("SHA256SUMS")
        # Bounded memory then explicit cache-root spill, never source-tree writes.
        with tempfile.SpooledTemporaryFile(max_size=1024**2, mode="w+b", dir=self.temp_root) as spool:
            while True:
                chunk = stream.read(min(65536, self.limits["max_member_bytes"] - size + 1,
                                        self.limits["max_total_bytes"] - self.total + 1))
                if not chunk:
                    break
                size += len(chunk)
                self.total += len(chunk)
                if size > self.limits["max_member_bytes"] or self.total > self.limits["max_total_bytes"]:
                    self.entries.append(entry)
                    self.issue("member_limit" if size > self.limits["max_member_bytes"] else "total_limit", entry)
                    return
                if not prefix:
                    prefix = chunk[:32]
                digest.update(chunk)
                if detect_signature(prefix) == "zip" or (is_checksum and size <= self.limits["max_checksum_bytes"]):
                    spool.write(chunk)
            signature = detect_signature(prefix)
            observed = InventoryEntry(entry.relative_path, entry.archive_chain, entry.archive_ordinals,
                                      size=size, sha256=digest.hexdigest(), signature=signature)
            self.entries.append(observed)
            if size != declared_size:
                self.issue("size_mismatch", observed)
            if name.lower().endswith(".zip") and signature != "zip":
                self.issue("extension_mismatch", observed, blocking=False)
            if is_checksum:
                if self.checksum_total + size > self.limits["max_checksum_bytes"]:
                    self.issue("checksum_limit", observed)
                else:
                    spool.seek(0)
                    self.ledgers.append((observed, spool.read()))
                    self.checksum_total += size
            if signature == "zip":
                self.archive(spool, observed)

    def archive(self, stream, parent):
        if len(parent.archive_chain) >= self.limits["max_depth"]:
            self.issue("depth_limit", parent)
            return
        try:
            preflight_zip(stream, remaining_members=self.limits["max_members"] - self.count,
                          max_central_bytes=self.limits["max_central_bytes"])
            with zipfile.ZipFile(stream) as archive:
                infos = archive.infolist()
                # CPython 3.11 keeps the pre-NUL original name in orig_filename.
                self.collisions([info.orig_filename for info in infos], parent)
                for ordinal, info in enumerate(infos):
                    name = info.orig_filename
                    entry = InventoryEntry(parent.relative_path, (*parent.archive_chain, name),
                                           (*parent.archive_ordinals, ordinal))
                    if not self.reserve(entry):
                        return
                    try:
                        canonical_relative_path(name[:-1] if name.endswith("/") else name)
                    except ValueError:
                        self.entries.append(entry)
                        self.issue("unsafe_path", entry)
                        continue
                    mode = info.external_attr >> 16
                    if stat.S_ISLNK(mode):
                        self.entries.append(InventoryEntry(entry.relative_path, entry.archive_chain, entry.archive_ordinals, kind="symlink"))
                        self.issue("symlink", entry)
                        continue
                    if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                        self.entries.append(entry)
                        self.issue("special_file", entry)
                        continue
                    if info.is_dir():
                        self.entries.append(InventoryEntry(entry.relative_path, entry.archive_chain, entry.archive_ordinals, kind="directory"))
                        continue
                    if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                        self.entries.append(entry)
                        self.issue("unsupported_compression", entry, str(info.compress_type))
                        continue
                    if info.file_size > max(1, info.compress_size) * self.limits["max_ratio"]:
                        self.entries.append(entry)
                        self.issue("ratio_limit", entry)
                        continue
                    try:
                        # ZipInfo (not filename) preserves duplicate physical members.
                        with archive.open(info) as member:
                            self.read_member(member, entry, info.file_size)
                    except (OSError, RuntimeError, ValueError, NotImplementedError, zipfile.BadZipFile, zlib.error) as error:
                        self.entries.append(entry)
                        self.issue("archive_error", entry, type(error).__name__)
        except ArchiveLimit as error:
            self.issue(error.code, parent)
        except (OSError, RuntimeError, ValueError, NotImplementedError, zipfile.BadZipFile, zlib.error) as error:
            self.issue("archive_error", parent, type(error).__name__)

    def parse_ledgers(self):
        assertions = []
        index = {}
        for entry in self.entries:
            index.setdefault((entry.relative_path, entry.archive_chain), []).append(entry)
        for ledger, raw in sorted(self.ledgers, key=lambda item: (item[0].relative_path, item[0].archive_ordinals)):
            if b"\0" in raw:
                self.issue("checksum_nul", ledger, f"count={raw.count(bytes([0]))}")
            seen = set()
            lines = raw.split(b"\n")
            for number, line in enumerate(lines, 1):
                if number == len(lines) and not line:
                    continue  # one terminal newline, not a skipped blank record
                if number > self.limits["max_members"]:
                    self.issue("checksum_count_limit", ledger)
                    break
                context = f"line={number}"
                try:
                    text = line.decode("utf-8", errors="strict")
                except UnicodeError:
                    self.issue("checksum_encoding", ledger, context)
                    continue
                match = re.fullmatch(r"(\S+) ([ *])(.*)", text)
                if not match:
                    self.issue("checksum_line", ledger, context)
                    continue
                expected, _, raw_name = match.groups()
                if not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
                    self.issue("checksum_digest", ledger, context)
                    continue
                name = raw_name[2:] if raw_name.startswith("./") else raw_name
                try:
                    canonical_relative_path(name)
                except ValueError:
                    self.issue("checksum_path", ledger, context)
                    continue
                if name in seen:
                    self.issue("checksum_duplicate", ledger, context)
                seen.add(name)
                if ledger.archive_chain:
                    target = str(PurePosixPath(ledger.archive_chain[-1]).parent / name)
                    chain = (*ledger.archive_chain[:-1], target)
                    candidates = index.get((ledger.relative_path, chain), [])
                    # Restrict to this physical enclosing archive, not same-name duplicates.
                    candidates = [entry for entry in candidates if entry.archive_ordinals[:-1] == ledger.archive_ordinals[:-1]]
                else:
                    target = str(PurePosixPath(ledger.relative_path).parent / name)
                    candidates = index.get((target, ()), [])
                matched = len(candidates) == 1 and candidates[0].sha256 == expected.lower()
                if not matched:
                    self.issue("checksum_missing" if not candidates else "checksum_mismatch", ledger, context)
                assertions.append(ChecksumAssertion(ledger.relative_path, number, raw_name, target, expected.lower(), matched,
                                                     ledger.archive_chain, ledger.archive_ordinals))
        return assertions

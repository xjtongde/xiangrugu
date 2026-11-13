"""Bounded external sorting in a private, descriptor-relative scratch area."""
from dataclasses import dataclass
import hashlib
import heapq
import os
from pathlib import Path
import secrets
import shutil
import stat
import struct
import time

from .unordered_values import (UnorderedLimits, UnorderedValueError,
                               encode_unordered_row, validate_unordered_frame)


@dataclass
class SortProgress:
    accepted_rows: int = 0
    field_count: int = 0
    frame_bytes: int = 0
    input_complete: bool = False
    sort_complete: bool = False


@dataclass
class SortStats:
    peak_temp_bytes: int = 0
    peak_temp_files: int = 0
    peak_chunk_bytes: int = 0
    peak_chunk_rows: int = 0
    elapsed_seconds: float = 0


@dataclass
class _File:
    name: str
    identity: tuple
    size: int
    count: int
    digest: object


def partition_for_row(frame: bytes) -> int:
    return hashlib.sha256(frame).digest()[0] >> 4


def _identity(st):
    return st.st_dev, st.st_ino


def _close(iterator):
    close = getattr(iterator, "close", None)
    if close is not None:
        close()


class SortWorkspace:
    def __init__(self, parent: Path, limits: UnorderedLimits, *, cancelled=None):
        self.parent, self.limits, self.cancelled = Path(parent), limits, cancelled
        self.progress, self.stats = {}, SortStats()
        self.cleanup_complete = False
        self.path = None
        self._fd = self._parent_fd = None
        self._files, self._bytes, self._seq = {}, 0, 0
        self._start = time.monotonic()

    def check(self):
        self.stats.elapsed_seconds = time.monotonic() - self._start
        if self.stats.elapsed_seconds >= self.limits.max_seconds:
            raise UnorderedValueError("timeout")
        if self.cancelled is not None:
            try:
                value = self.cancelled()
            except Exception as error:
                raise UnorderedValueError("input_error") from error
            if type(value) is not bool:
                raise UnorderedValueError("input_error")
            if value:
                raise UnorderedValueError("cancelled")

    def __enter__(self):
        self.check()
        p = self.parent
        if not p.is_absolute() or p.parts[:3] != ("/", "data", "var") or ".." in p.parts:
            raise UnorderedValueError("scratch_path")
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        try:
            for part in p.parts[1:]:
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = nxt
            self._parent_fd, fd = fd, None
            name = "unordered-" + secrets.token_hex(16)
            os.mkdir(name, mode=0o700, dir_fd=self._parent_fd)
            self.path = p / name
            self._fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                               dir_fd=self._parent_fd)
            self._directory_identity = _identity(os.fstat(self._fd))
            return self
        except OSError:
            if self._parent_fd is not None:
                os.close(self._parent_fd)
                self._parent_fd = None
            raise UnorderedValueError("scratch_path") from None
        finally:
            if fd is not None:
                os.close(fd)

    def _verified_open(self, file, flags):
        try:
            fd = os.open(file.name, flags | os.O_NOFOLLOW, dir_fd=self._fd)
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or _identity(st) != file.identity:
                os.close(fd)
                raise UnorderedValueError("temp_corrupt")
            return fd
        except OSError:
            raise UnorderedValueError("temp_corrupt") from None

    def create(self):
        self.check()
        if len(self._files) >= self.limits.max_temp_files:
            raise UnorderedValueError("budget")
        self._seq += 1
        name = f"frames-{self._seq}"
        try:
            fd = os.open(name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                         0o600, dir_fd=self._fd)
            try:
                file = _File(name, _identity(os.fstat(fd)), 0, 0, hashlib.sha256())
            finally:
                os.close(fd)
        except OSError:
            raise UnorderedValueError("io_error") from None
        self._files[name] = file
        self.stats.peak_temp_files = max(self.stats.peak_temp_files, len(self._files))
        return file

    def append(self, file, frame):
        self.check()
        if self._bytes + len(frame) > self.limits.max_temp_bytes:
            raise UnorderedValueError("budget")
        if shutil.disk_usage(self.path).free < len(frame):
            raise UnorderedValueError("disk_full")
        fd = self._verified_open(file, os.O_WRONLY | os.O_APPEND)
        try:
            if os.fstat(fd).st_size != file.size or os.write(fd, frame) != len(frame):
                raise UnorderedValueError("io_error")
        except OSError:
            raise UnorderedValueError("io_error") from None
        finally:
            os.close(fd)
        file.size += len(frame)
        file.count += 1
        file.digest.update(frame)
        self._bytes += len(frame)
        self.stats.peak_temp_bytes = max(self.stats.peak_temp_bytes, self._bytes)

    def delete(self, file):
        st = os.stat(file.name, dir_fd=self._fd, follow_symlinks=False)
        if not stat.S_ISREG(st.st_mode) or _identity(st) != file.identity:
            raise UnorderedValueError("cleanup_error")
        os.unlink(file.name, dir_fd=self._fd)
        self._bytes -= file.size
        del self._files[file.name]

    def read(self, file, schema, *, ordered):
        fd = self._verified_open(file, os.O_RDONLY)
        digest, count, size, last = hashlib.sha256(), 0, 0, None
        def exact(n):
            chunks, left = [], n
            while left:
                self.check()
                data = os.read(fd, left)
                if not data:
                    raise UnorderedValueError("temp_corrupt")
                chunks.append(data)
                left -= len(data)
            return b"".join(chunks)
        try:
            if os.fstat(fd).st_size != file.size:
                raise UnorderedValueError("temp_corrupt")
            while size < file.size:
                self.check()
                h = exact(13)
                n = struct.unpack(">Q", h[5:13])[0]
                if n > self.limits.max_row_bytes or size+13+n > file.size:
                    raise UnorderedValueError("temp_corrupt")
                frame = h + exact(n)
                validate_unordered_frame(schema, frame, limits=self.limits)
                if ordered and last is not None and frame < last:
                    raise UnorderedValueError("temp_corrupt")
                last = frame if ordered else None
                count += 1
                size += len(frame)
                digest.update(frame)
                yield frame
            if count != file.count or size != file.size or digest.digest() != file.digest.digest():
                raise UnorderedValueError("temp_corrupt")
        except OSError:
            raise UnorderedValueError("io_error") from None
        finally:
            os.close(fd)

    def __exit__(self, exc_type, exc, tb):
        failed = False
        try:
            for file in list(self._files.values()):
                try:
                    self.delete(file)
                except (OSError, UnorderedValueError):
                    failed = True
            st = os.stat(self.path.name, dir_fd=self._parent_fd, follow_symlinks=False)
            if _identity(st) != self._directory_identity or not stat.S_ISDIR(st.st_mode):
                failed = True
            if not failed:
                os.rmdir(self.path.name, dir_fd=self._parent_fd)
                self.cleanup_complete = True
        except OSError:
            failed = True
        finally:
            os.close(self._fd)
            os.close(self._parent_fd)
            self._fd = self._parent_fd = None
        if failed:
            raise UnorderedValueError("cleanup_error") from None
        return False


class SortedRows:
    def __init__(self, workspace, schema, file, side):
        self._workspace, self._schema, self._file, self._side = workspace, schema, file, side
        p = workspace.progress[side]
        self.row_count, self.field_count = p.accepted_rows, p.field_count
        self.stream_bytes = p.frame_bytes + 81
        self._used = False

    def iter_frames(self):
        if self._used:
            raise UnorderedValueError("input_error")
        self._used = True
        count, size = 0, 0
        for frame in self._workspace.read(self._file, self._schema, ordered=True):
            count += 1
            size += len(frame)
            yield frame
        if count != self.row_count or size+81 != self.stream_bytes:
            raise UnorderedValueError("temp_corrupt")
        self._workspace.progress[self._side].sort_complete = True


def _merge(workspace, schema, files):
    if len(files) == 1:
        return files[0]
    out = workspace.create()
    readers = [workspace.read(f, schema, ordered=True) for f in files]
    try:
        for frame in heapq.merge(*readers):
            workspace.append(out, frame)
    finally:
        for reader in readers:
            reader.close()
    for file in files:
        workspace.delete(file)
    return out


def sort_rows(schema, rows, *, workspace: SortWorkspace, side: str) -> SortedRows:
    if side not in ("source", "target") or side in workspace.progress or workspace._fd is None:
        raise UnorderedValueError("structure")
    p = workspace.progress[side] = SortProgress()
    buckets = {}
    limits = workspace.limits
    try:
        if len(schema.columns) > limits.max_columns or limits.max_stream_bytes < 81:
            raise UnorderedValueError("budget")
        while True:
            workspace.check()
            try:
                values = next(rows)
            except StopIteration:
                p.input_complete = True
                break
            except Exception as error:
                raise UnorderedValueError("input_error") from error
            if p.accepted_rows >= limits.max_rows:
                raise UnorderedValueError("budget")
            frame = encode_unordered_row(schema, values, limits=limits)
            if p.frame_bytes + len(frame) + 81 > limits.max_stream_bytes:
                raise UnorderedValueError("budget")
            bucket = partition_for_row(frame)
            if type(bucket) is not int or not 0 <= bucket < 16:
                raise UnorderedValueError("input_error")
            if bucket not in buckets:
                buckets[bucket] = workspace.create()
            workspace.append(buckets[bucket], frame)
            p.accepted_rows += 1
            p.field_count += len(schema.columns)
            p.frame_bytes += len(frame)
    except UnorderedValueError as error:
        raise UnorderedValueError(error.code, side=side, scan_index=p.accepted_rows+1,
                                  column_key=error.column_key) from error
    finally:
        try:
            _close(rows)
        except Exception:
            raise UnorderedValueError("input_error", side=side) from None
    runs = []
    for bucket in buckets.values():
        chunk, size = [], 0
        def flush():
            out = workspace.create()
            for frame in sorted(chunk):
                workspace.append(out, frame)
            runs.append(out)
        reader = workspace.read(bucket, schema, ordered=False)
        try:
            for frame in reader:
                if chunk and (len(chunk) >= limits.chunk_rows or size+len(frame) > limits.chunk_bytes):
                    flush()
                    chunk, size = [], 0
                chunk.append(frame)
                size += len(frame)
                workspace.stats.peak_chunk_rows = max(workspace.stats.peak_chunk_rows, len(chunk))
                workspace.stats.peak_chunk_bytes = max(workspace.stats.peak_chunk_bytes, size)
            if chunk:
                flush()
        finally:
            reader.close()
        workspace.delete(bucket)
    if not runs:
        runs = [workspace.create()]
    while len(runs) > 1:
        runs = [_merge(workspace, schema, runs[i:i+limits.merge_fan_in])
                for i in range(0, len(runs), limits.merge_fan_in)]
    return SortedRows(workspace, schema, runs[0], side)

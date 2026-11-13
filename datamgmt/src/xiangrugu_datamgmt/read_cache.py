"""Fixed cache advice for complete sequential reads in approved readonly batches.

This is neither a byte budget nor an authorization gate. Advice never replaces
hashing, and failure cannot silently select the old caching behavior.
"""
import hashlib
import os


class ReadCachePolicy:
    WINDOW_BYTES = 64*1024*1024

    def __init__(self):
        if not hasattr(os, 'posix_fadvise') or not hasattr(os, 'POSIX_FADV_DONTNEED'):
            raise ValueError('read_cache_unavailable')
        try:
            self.page_bytes = os.sysconf('SC_PAGESIZE')
        except (OSError, ValueError):
            raise ValueError('read_cache_unavailable') from None
        if (type(self.page_bytes) is not int or self.page_bytes <= 0
                or self.WINDOW_BYTES % self.page_bytes):
            raise ValueError('read_cache_unavailable')
        self.bytes_read = self.completed_hashes = self.advice_calls = self.advised_bytes = 0

    def _release(self, fd, start, size):
        try:
            os.posix_fadvise(fd, start, size, os.POSIX_FADV_DONTNEED)
        except OSError:
            raise ValueError('read_cache_advice') from None
        self.advice_calls += 1
        self.advised_bytes += size

    def hash_file(self, path, *, guard=lambda: None):
        digest = hashlib.sha256()
        consumed = released = 0
        guard()
        with path.open('rb') as stream:
            while True:
                guard()
                chunk = stream.read(min(1024*1024, self.WINDOW_BYTES))
                if not chunk:
                    break
                guard()
                digest.update(chunk)
                consumed += len(chunk)
                self.bytes_read += len(chunk)
                if consumed-released >= self.WINDOW_BYTES:
                    end = consumed//self.page_bytes*self.page_bytes
                    self._release(stream.fileno(), released, end-released)
                    released = end
                    guard()
            # Partial final pages stay cached; no unread bytes are advised.
            end = consumed//self.page_bytes*self.page_bytes
            if end > released:
                self._release(stream.fileno(), released, end-released)
            guard()
        self.completed_hashes += 1
        return digest.hexdigest()

    def evidence(self):
        return dict(method='posix-fadvise-consumed-pages-v1',
            window_bytes=self.WINDOW_BYTES, page_bytes=self.page_bytes,
            bytes_read=self.bytes_read, completed_hashes=self.completed_hashes,
            advice_calls=self.advice_calls, advised_bytes=self.advised_bytes)


def require_read_cache(policy):
    if policy is not None and type(policy) is not ReadCachePolicy:
        raise ValueError('read_cache_policy')

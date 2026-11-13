"""Bounded, fresh request reads for the strict project controller."""

import ctypes
import errno
from functools import lru_cache
import os
from pathlib import Path
import stat
import sys

from .batch_execution import read_metadata


class _OpenHow(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in ('flags', 'mode', 'resolve')]


def _linux_openat2():
    if (sys.platform != 'linux' or os.uname().machine != 'x86_64'
            or ctypes.sizeof(ctypes.c_void_p) != 8 or not hasattr(os, 'O_PATH')):
        return None
    try:
        syscall = ctypes.CDLL(None, use_errno=True).syscall
    except (OSError, AttributeError):
        return None
    syscall.argtypes = (ctypes.c_long, ctypes.c_int, ctypes.c_char_p,
                        ctypes.POINTER(_OpenHow), ctypes.c_size_t)
    syscall.restype = ctypes.c_long
    return syscall


_openat2 = _linux_openat2()
_SYS_OPENAT2_X86_64 = 437
_AT_FDCWD = -100
_RESOLVE_NO_SYMLINKS = 0x04
_how = _OpenHow(getattr(os, 'O_PATH', 0) | getattr(os, 'O_CLOEXEC', 0), 0, _RESOLVE_NO_SYMLINKS)
_how_pointer = ctypes.pointer(_how)
_how_size = ctypes.sizeof(_how)
_unavailable = frozenset({errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP, errno.EPERM})
_max_bytes = 1024**2


@lru_cache(maxsize=32)
def _encoded_path(path):
    encoded = os.fsencode(path)
    if not path.is_absolute() or b'\0' in encoded:
        raise ValueError('metadata_path_or_budget')
    return encoded


def _open_path(path):
    if _openat2 is None:
        return None
    fd = _openat2(_SYS_OPENAT2_X86_64, _AT_FDCWD, _encoded_path(path), _how_pointer, _how_size)
    if fd >= 0:
        return fd
    error = ctypes.get_errno()
    if error in _unavailable:
        return None
    if error == errno.ELOOP:
        raise ValueError('metadata_path_or_budget')
    raise OSError(error, os.strerror(error), path)


def _reopen(fd):
    # O_PATH lets us reject special files before acquiring a readable handle.
    return open(f'/proc/self/fd/{fd}', 'rb',
                opener=lambda path, flags: os.open(path, flags | os.O_NONBLOCK | os.O_NOCTTY))


def read_request(path):
    """Use a fresh kernel path walk, with the checked reader on unsupported hosts."""
    if not isinstance(path, Path):
        path = Path(path)
    fd = _open_path(path)
    if fd is None:
        return read_metadata(path)
    try:
        current = os.fstat(fd)
        if not stat.S_ISREG(current.st_mode) or current.st_size > _max_bytes:
            raise ValueError('metadata_path_or_budget')
        try:
            stream = _reopen(fd)
        except (FileNotFoundError, NotADirectoryError):
            return read_metadata(path)
        with stream:
            reopened = os.fstat(stream.fileno())
            if (reopened.st_dev, reopened.st_ino) != (current.st_dev, current.st_ino):
                raise ValueError('metadata_path_or_budget')
            raw = stream.read(_max_bytes + 1)
        if len(raw) > _max_bytes:
            raise ValueError('metadata_budget')
        return raw
    finally:
        os.close(fd)

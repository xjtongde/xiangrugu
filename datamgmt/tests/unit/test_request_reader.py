"""Request-reader protection tests on owned temporary files."""
import errno
import os

import pytest


@pytest.fixture
def reader():
    from xiangrugu_datamgmt import request_reader
    return request_reader


def test_supported_fast_path_reopens_current_regular_file(reader, tmp_path, monkeypatch):
    path = tmp_path / 'request.json'
    path.write_bytes(b'first')
    fd = reader._open_path(path)
    if fd is None:
        pytest.skip('openat2 unavailable in this environment')
    os.close(fd)
    monkeypatch.setattr(reader, 'read_metadata', lambda _: pytest.fail('unexpected fallback'))
    assert reader.read_request(path) == b'first'
    replacement = tmp_path / 'replacement'
    replacement.write_bytes(b'second')
    replacement.replace(path)
    assert reader.read_request(path) == b'second'
    path.unlink()
    path.symlink_to(tmp_path / 'missing')
    with pytest.raises(ValueError, match='metadata_path_or_budget'):
        reader.read_request(path)


@pytest.mark.parametrize('kind', ['parent-link', 'fifo', 'oversize'])
def test_request_reader_refuses_unsafe_paths(reader, tmp_path, kind):
    path = tmp_path / 'request.json'
    if kind == 'parent-link':
        path.symlink_to(tmp_path, target_is_directory=True)
        path /= 'missing'
    elif kind == 'fifo':
        os.mkfifo(path)
    else:
        path.write_bytes(b'x' * (1024**2 + 1))
    with pytest.raises(ValueError, match='metadata_path_or_budget'):
        reader.read_request(path)


def test_unsupported_syscall_uses_checked_fallback(reader, tmp_path, monkeypatch):
    def unavailable(*args):
        reader.ctypes.set_errno(errno.ENOSYS)
        return -1

    monkeypatch.setattr(reader, '_openat2', unavailable)
    path = tmp_path / 'request.json'
    path.write_bytes(b'first')
    assert reader.read_request(path) == b'first'
    path.unlink()
    path.symlink_to(tmp_path / 'missing')
    with pytest.raises(ValueError, match='metadata_path_or_budget'):
        reader.read_request(path)


def test_missing_proc_fd_uses_fallback_and_closes_descriptor(reader, tmp_path, monkeypatch):
    path = tmp_path / 'request.json'
    path.write_bytes(b'first')
    fd = os.open(path, os.O_RDONLY)
    monkeypatch.setattr(reader, '_open_path', lambda _: fd)

    def unavailable(*args):
        raise FileNotFoundError(errno.ENOENT, 'missing proc fd')

    monkeypatch.setattr(reader, '_reopen', unavailable)
    assert reader.read_request(path) == b'first'
    with pytest.raises(OSError) as error:
        os.fstat(fd)
    assert error.value.errno == errno.EBADF


def test_reopened_descriptor_must_refer_to_validated_inode(reader, tmp_path, monkeypatch):
    request = tmp_path / 'request.json'
    other = tmp_path / 'other.json'
    request.write_bytes(b'first')
    other.write_bytes(b'first')
    monkeypatch.setattr(reader, '_open_path', lambda _: os.open(request, os.O_RDONLY))
    monkeypatch.setattr(reader, '_reopen', lambda _: other.open('rb'))
    with pytest.raises(ValueError, match='metadata_path_or_budget'):
        reader.read_request(request)


def test_growth_after_open_still_has_bounded_read(reader, tmp_path, monkeypatch):
    path = tmp_path / 'request.json'
    path.write_bytes(b'x')
    monkeypatch.setattr(reader, '_open_path', lambda _: os.open(path, os.O_RDONLY))

    def grow(_):
        path.write_bytes(b'x' * (1024**2 + 2))
        return path.open('rb')

    monkeypatch.setattr(reader, '_reopen', grow)
    with pytest.raises(ValueError, match='metadata_budget'):
        reader.read_request(path)

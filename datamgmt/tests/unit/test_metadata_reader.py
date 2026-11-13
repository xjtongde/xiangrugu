"""Metadata freshness and rejection semantics survive lexical path reuse."""
import io
import os
from pathlib import Path

import pytest

from xiangrugu_datamgmt import batch_execution as module


def test_one_regular_stat_and_fresh_symlink_chain_per_call(tmp_path, monkeypatch):
    path = tmp_path / 'request.json'
    path.write_bytes(b'first')
    actual_stat = os.stat
    calls = []
    def observed(p, *args, **kwargs):
        calls.append((os.fspath(p), kwargs.get('follow_symlinks', True)))
        return actual_stat(p, *args, **kwargs)
    monkeypatch.setattr(os, 'stat', observed)
    expected = {str(p) for p in (path, *path.parents)}
    for _ in range(2):
        calls.clear()
        assert module.read_metadata(path) == b'first'
        observed_calls = calls.copy()
        assert [p for p, follow in observed_calls if follow] == [str(path)]
        assert {p for p, follow in observed_calls if not follow} == expected


@pytest.mark.parametrize('as_string', [False, True])
def test_each_call_reads_current_bytes(tmp_path, as_string):
    path = tmp_path / 'request.json'
    argument = str(path) if as_string else path
    path.write_bytes(b'first')
    assert module.read_metadata(argument) == b'first'
    path.write_bytes(b'changed')
    assert module.read_metadata(argument) == b'changed'
    path.write_bytes(b'')
    assert module.read_metadata(argument) == b''


def test_cached_leaf_replaced_by_symlink_is_rejected(tmp_path):
    path = tmp_path / 'request.json'
    path.write_bytes(b'first')
    assert module.read_metadata(path) == b'first'
    path.unlink()
    target = tmp_path / 'other'
    target.write_bytes(b'first')
    path.symlink_to(target)
    with pytest.raises(ValueError, match='metadata_path_or_budget'):
        module.read_metadata(path)


@pytest.mark.parametrize('missing_leaf', [False, True])
def test_cached_parent_replaced_by_symlink_keeps_rejection_order(tmp_path, missing_leaf):
    parent = tmp_path / 'parent'
    parent.mkdir()
    path = parent / 'request.json'
    path.write_bytes(b'first')
    assert module.read_metadata(path) == b'first'
    moved = tmp_path / 'moved'
    parent.rename(moved)
    if missing_leaf:
        (moved / 'request.json').unlink()
    parent.symlink_to(moved, target_is_directory=True)
    with pytest.raises(ValueError, match='metadata_path_or_budget'):
        module.read_metadata(path)


def test_current_size_and_type_checked_after_cached_read(tmp_path):
    path = tmp_path / 'request.json'
    path.write_bytes(b'x' * 1024**2)
    assert len(module.read_metadata(path)) == 1024**2
    path.write_bytes(b'x' * (1024**2 + 1))
    with pytest.raises(ValueError, match='metadata_path_or_budget'):
        module.read_metadata(path)
    path.unlink()
    path.mkdir()
    with pytest.raises(ValueError, match='metadata_path_or_budget'):
        module.read_metadata(path)


def test_missing_leaf_and_enotdir_keep_os_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        module.read_metadata(tmp_path / 'missing')
    parent = tmp_path / 'file'
    parent.write_bytes(b'x')
    with pytest.raises(NotADirectoryError):
        module.read_metadata(parent / 'child')


def test_new_read_permission_error_not_cached(tmp_path):
    path = tmp_path / 'request.json'
    path.write_bytes(b'x')
    assert module.read_metadata(path) == b'x'
    path.chmod(0)
    try:
        with pytest.raises(PermissionError):
            module.read_metadata(path)
    finally:
        path.chmod(0o600)


def test_growth_after_stat_stays_bounded(tmp_path, monkeypatch):
    path = tmp_path / 'request.json'
    path.write_bytes(b'x')
    sizes = []
    class Growing(io.BytesIO):
        def read(self, size=-1):
            sizes.append(size)
            return super().read(size)
    monkeypatch.setattr(Path, 'open', lambda *a, **k: Growing(b'x' * (1024**2 + 2)))
    with pytest.raises(ValueError, match='metadata_budget'):
        module.read_metadata(path)
    assert sizes == [1024**2 + 1]


def test_relative_path_rejected_before_filesystem_probe(monkeypatch):
    monkeypatch.setattr(os, 'stat', lambda *a, **k: pytest.fail('unexpected stat'))
    with pytest.raises(ValueError, match='metadata_path_or_budget'):
        module.read_metadata('relative')


def test_fifo_rejected_before_open(tmp_path, monkeypatch):
    path = tmp_path / 'pipe'
    os.mkfifo(path)
    monkeypatch.setattr(Path, 'open', lambda *a, **k: pytest.fail('unexpected FIFO open'))
    with pytest.raises(ValueError, match='metadata_path_or_budget'):
        module.read_metadata(path)


def test_lexical_cache_is_bounded(tmp_path):
    module._metadata_path_chain.cache_clear()
    for index in range(40):
        path = tmp_path / str(index)
        path.write_bytes(str(index).encode())
        assert module.read_metadata(path) == str(index).encode()
    info = module._metadata_path_chain.cache_info()
    assert info.maxsize == 32
    assert info.currsize == 32

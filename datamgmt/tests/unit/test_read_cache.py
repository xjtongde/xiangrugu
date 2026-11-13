"""Cache hints must never replace complete reads, hashes or failure gates."""
import hashlib
import importlib
import json
import os
from pathlib import Path

import pytest

from test_project_task_control import project_task_args
from test_task_control import task_args, readonly_request, batch_request, canary_args, args, allow_unit_mounts
from test_sqlite_batch_expectations import fixture, run


def policy(monkeypatch):
    module = importlib.import_module('xiangrugu_datamgmt.read_cache')
    monkeypatch.setattr(module.ReadCachePolicy, 'WINDOW_BYTES', 65536)
    return module.ReadCachePolicy()


@pytest.mark.parametrize('size', [0, 17, 4095, 4096, 65536, 65537, 131089])
def test_exact_digest_and_only_consumed_complete_pages(tmp_path, monkeypatch, size):
    cache = policy(monkeypatch)
    data = (bytes(range(256))*513)[:size]
    file = tmp_path/'source'
    file.write_bytes(data)
    before = file.stat()
    calls = []
    monkeypatch.setattr(os, 'posix_fadvise', lambda fd, offset, length, advice:
        calls.append((offset, length, advice, os.fstat(fd).st_size)))
    assert cache.hash_file(file) == hashlib.sha256(data).hexdigest()
    assert file.read_bytes() == data
    assert (file.stat().st_mtime_ns, file.stat().st_ctime_ns) == (before.st_mtime_ns, before.st_ctime_ns)
    page = os.sysconf('SC_PAGESIZE')
    cursor = 0
    for offset, length, advice, observed_size in calls:
        assert offset == cursor and length > 0
        assert offset % page == length % page == 0
        assert offset+length <= size and observed_size == size
        assert advice == os.POSIX_FADV_DONTNEED
        cursor += length
    assert cursor == size//page*page
    assert cache.evidence()['bytes_read'] == size
    assert cache.evidence()['completed_hashes'] == 1


def test_multiple_windows_are_not_collapsed_into_whole_file_advice(tmp_path, monkeypatch):
    cache = policy(monkeypatch)
    file = tmp_path/'source'
    file.write_bytes(b'x'*(3*65536+19))
    calls = []
    monkeypatch.setattr(os, 'posix_fadvise', lambda fd, start, size, advice: calls.append((start, size)))
    cache.hash_file(file)
    assert calls == [(0,65536), (65536,65536), (131072,65536)]


def test_advice_failure_has_no_completed_digest(tmp_path, monkeypatch):
    cache = policy(monkeypatch)
    file = tmp_path/'source'
    file.write_bytes(b'x'*65536)
    def fail(*args):
        raise OSError('private source path must not escape')
    monkeypatch.setattr(os, 'posix_fadvise', fail)
    with pytest.raises(ValueError, match='^read_cache_advice$'):
        cache.hash_file(file)
    assert cache.evidence()['completed_hashes'] == 0


def test_unsupported_platform_fails_before_read(tmp_path, monkeypatch):
    module = importlib.import_module('xiangrugu_datamgmt.read_cache')
    monkeypatch.delattr(os, 'posix_fadvise')
    with pytest.raises(ValueError, match='^read_cache_unavailable$'):
        module.ReadCachePolicy()


def test_cancel_during_digest_does_not_advise_unread_bytes(tmp_path, monkeypatch):
    cache = policy(monkeypatch)
    file = tmp_path/'source'
    file.write_bytes(b'x'*262144)
    calls = []
    monkeypatch.setattr(os, 'posix_fadvise', lambda fd, start, size, advice: calls.append((start,size)))
    def guard():
        if calls:
            raise ValueError('cancelled')
    with pytest.raises(ValueError, match='cancelled'):
        cache.hash_file(file, guard=guard)
    assert calls == [(0,65536)]
    assert cache.evidence()['completed_hashes'] == 0


def test_default_snapshot_hash_never_uses_advice(tmp_path, monkeypatch):
    from xiangrugu_datamgmt.snapshots import sha256_file
    file=tmp_path/'source'
    file.write_bytes(b'unchanged default')
    monkeypatch.setattr(os, 'posix_fadvise', lambda *a: pytest.fail('default used hints'))
    assert sha256_file(file) == hashlib.sha256(file.read_bytes()).hexdigest()


def test_snapshot_cache_mode_still_rejects_modified_or_extra_member(tmp_path, monkeypatch):
    from xiangrugu_datamgmt.snapshots import inventory, digest, verify_snapshot
    cache = policy(monkeypatch)
    root=tmp_path/'snapshot'
    root.mkdir()
    file=root/'member'
    file.write_bytes(b'x'*65536)
    members=inventory(root)
    certificate=tmp_path/'certificate.json'
    certificate.write_text(json.dumps(dict(version=1,status='VERIFIED',source_path='/never-read',
        snapshot_id=root.name,members=members,manifest_sha256=digest(members))))
    verify_snapshot(root,certificate,expected_source=Path('/never-read'),read_cache=cache)
    file.write_bytes(b'y'*65536)
    with pytest.raises(ValueError):
        verify_snapshot(root,certificate,expected_source=Path('/never-read'),read_cache=cache)
    file.write_bytes(b'x'*65536)
    (root/'extra').write_bytes(b'new member')
    with pytest.raises(ValueError):
        verify_snapshot(root,certificate,expected_source=Path('/never-read'),read_cache=cache)


def test_batch_cache_mode_keeps_two_complete_hashes_and_independent_values(tmp_path, monkeypatch):
    path,objects,scratch=fixture(tmp_path)
    cache=policy(monkeypatch)
    default=run(path,objects,scratch)
    report=run(path,objects,scratch,read_cache=cache)
    # Wall time is not part of a reproducible value expectation.
    for result in (default,report):
        for obj in result['objects']:
            obj['sort_stats'].pop('elapsed_seconds')
    assert report == default
    assert cache.evidence()['completed_hashes'] == 2
    assert cache.evidence()['bytes_read'] == 2*path.stat().st_size


@pytest.mark.parametrize('failure', ['advice','source_change','sidecar','cancel'])
def test_cached_batch_failure_cannot_return_partial_answer(tmp_path, monkeypatch, failure):
    from xiangrugu_datamgmt import sqlite_expectations
    path,objects,scratch=fixture(tmp_path)
    cache=policy(monkeypatch)
    stopped=False
    original=sqlite_expectations._summarize_rows
    def after_object(*a,**kw):
        nonlocal stopped
        result=original(*a,**kw)
        if failure=='source_change':
            data=path.read_bytes(); path.unlink(); path.write_bytes(data)
        elif failure=='sidecar':
            path.with_name(path.name+'-wal').write_bytes(b'x')
        else:
            stopped=True
        return result
    if failure=='advice':
        monkeypatch.setattr(os,'posix_fadvise',lambda *a: (_ for _ in ()).throw(OSError('advice')))
    else:
        monkeypatch.setattr(sqlite_expectations,'_summarize_rows',after_object)
    with pytest.raises(ValueError):
        run(path,objects,scratch,read_cache=cache,cancelled=lambda: stopped)
    assert list(scratch.iterdir()) == []


def test_trusted_project_controller_selects_fixed_policy_and_records_it(project_task_args, monkeypatch):
    from xiangrugu_datamgmt import task_control
    allow_unit_mounts(monkeypatch)
    stage=task_control.execute_controlled_batch(**project_task_args)
    result=json.loads(stage.read_text())
    assert result['read_cache']['method']=='posix-fadvise-consumed-pages-v1'
    assert result['read_cache']['window_bytes']==67108864
    assert result['read_cache']['completed_hashes'] >= 3
    assert result['file_digest_passes']==2 and result['full_snapshot_verified_this_run']


def test_request_cannot_add_cache_flags(task_args, monkeypatch):
    from xiangrugu_datamgmt import task_control
    allow_unit_mounts(monkeypatch)
    request=json.loads(task_args['request_file'].read_text())
    request['read_cache']={'skip_digest':True}
    task_args['request_file'].write_text(json.dumps(request))
    task_args['expected_request_sha256']=hashlib.sha256(task_args['request_file'].read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='request'):
        task_control.execute_controlled_batch(**task_args)

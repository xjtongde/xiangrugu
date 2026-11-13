"""Cancellation after the last cleaned object must not under-report completion."""
import json
from pathlib import Path
import sys

import pytest

from test_task_failure_evidence import cli_args
from test_task_control import task_args, readonly_request, batch_request, canary_args, args, renew, allow_unit_mounts


@pytest.mark.parametrize('cause,domain,code', [
    ('cancel', 'sqlite', 'cancelled'), ('deadline', 'control', 'lifecycle_timeout')])
def test_last_object_completed_before_tail_failure_has_accurate_phase_and_count(
        task_args, monkeypatch, capsys, cause, domain, code):
    from xiangrugu_datamgmt import task_control
    from xiangrugu_datamgmt.value_sort import SortWorkspace
    from xiangrugu_datamgmt.sqlite_values import _BatchSource, SQLiteValueReadError
    allow_unit_mounts(monkeypatch)
    cleaned_and_checked = False
    original_check = SortWorkspace.check
    original_guard = _BatchSource.guard
    def checked(self):
        nonlocal cleaned_and_checked
        original_check(self)
        if self.cleanup_complete:
            cleaned_and_checked = True
    def tail_guard(self):
        if cleaned_and_checked:
            if cause == 'cancel':
                raise SQLiteValueReadError('cancelled')
            raise ValueError('lifecycle_timeout')
        return original_guard(self)
    monkeypatch.setattr(SortWorkspace, 'check', checked)
    monkeypatch.setattr(_BatchSource, 'guard', tail_guard)
    monkeypatch.setattr(sys, 'argv', cli_args(task_args))
    request = json.loads(task_args['request_file'].read_text())
    assert task_control.main() == 1
    failure = json.loads(capsys.readouterr().out)['failure']
    assert (failure['domain'], failure['code']) == (domain, code)
    assert failure['stage'] == 'batch_digest_after'
    assert failure['completed_objects'] == 1
    assert failure['object_index'] is None
    assert not Path(request['output']).exists()
    assert not Path(request['output']).with_name('.' + Path(request['output']).name + '.incomplete').exists()

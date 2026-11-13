"""Select externally authorized, pinned source-only tasks; default to artificial."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import signal
import time

from .batch_execution import read_metadata, _json, _check_cancel
from .readonly_batch import execute_readonly_batch, _hash, _require_readonly_mount, _path
from .request_reader import read_request
from .task_failure import FailureTrace
from .snapshots import write_json_exclusive


class _ArtificialRequestGuard:
    """Bound heavy checks to 100ms at guard calls; light gates remain immediate."""
    def __init__(self, *, check_metadata, cancelled, started, lifecycle_seconds, clock=None):
        self.check_metadata, self.cancelled = check_metadata, cancelled
        self.started, self.lifecycle_seconds = started, lifecycle_seconds
        self.clock = time.monotonic if clock is None else clock
        if type(started) not in (int, float) or not math.isfinite(started):
            raise ValueError('input_error')
        self._last_clock, self._checked_at = started, None

    def _light(self):
        try:
            now = self.clock()
        except Exception:
            raise ValueError('input_error') from None
        if type(now) not in (int, float) or not math.isfinite(now) or now < self._last_clock:
            raise ValueError('input_error')
        self._last_clock = now
        if now-self.started >= self.lifecycle_seconds:
            raise ValueError('lifecycle_timeout')
        stopped = self.cancelled()
        if type(stopped) is not bool:
            raise ValueError('input_error')
        if stopped:
            raise ValueError('cancelled')
        return now

    def __call__(self, *, force=False):
        now = self._light()
        if force or self._checked_at is None or now-self._checked_at >= 0.1:
            self.check_metadata()
            self._light()
            # Failed/slow checks never renew an unchecked window.
            self._checked_at = now
        return False


def execute_controlled_batch(*, request_file, expected_request_sha256,
        expected_approval_sha256, expected_roots_sha256, actual_image,
        lifecycle_seconds=1800, cancelled=lambda: False, authorized_source_mode='artificial', progress=None):
    """Expected pins are external inputs, not values learned from the request.

    The host controller supplies an image identity obtained from Docker inspect.
    Neither digest pins nor an approved JSON prove human authorization; selection
    still belongs to the authorized operator. Project snapshot mode requires an
    explicit external selection; the request itself cannot enable that mode.
    """
    started = time.monotonic()
    if progress is not None:
        progress('task_preflight')
    if authorized_source_mode not in ('artificial', 'project_snapshot'):
        raise ValueError('controller_source_mode')
    if type(lifecycle_seconds) is not int or not 1 <= lifecycle_seconds <= 1800:
        raise ValueError('lifecycle_budget')
    _check_cancel(cancelled)
    if not all(_hash(value) for value in (expected_request_sha256,
                                         expected_approval_sha256, expected_roots_sha256)):
        raise ValueError('controller_pin')
    request_path = Path(request_file)
    raw = read_metadata(request_path)
    if hashlib.sha256(raw).hexdigest() != expected_request_sha256:
        raise ValueError('controller_request_identity')
    request = _json(raw)
    if type(request) is not dict:
        raise ValueError('real_execution_closed')
    if request.get('source_mode') != authorized_source_mode:
        if request.get('source_mode') == 'project_snapshot':
            raise ValueError('real_execution_closed')
        raise ValueError('controller_source_mode')
    if (type(request.get('lifecycle_seconds')) is not int
            or request['lifecycle_seconds'] != lifecycle_seconds):
        raise ValueError('lifecycle_budget')
    if (request.get('approval_sha256') != expected_approval_sha256
            or request.get('roots_sha256') != expected_roots_sha256):
        raise ValueError('controller_pin')
    if (type(actual_image) is not dict
            or actual_image.keys() != {'image_id', 'git_revision', 'user', 'source_status'}
            or actual_image['image_id'] != request.get('image_id')
            or actual_image['git_revision'] != request.get('git_revision')
            or actual_image['user'] != '10001:10001'
            or actual_image['source_status'] not in ('clean', 'dirty')):
        raise ValueError('controller_image_identity')
    _require_readonly_mount(request_path)
    controller_evidence=dict(controller_request_sha256=expected_request_sha256,
        controller_verified_image=dict(actual_image),controller_lifecycle_seconds=lifecycle_seconds)
    partition_metadata=None
    if authorized_source_mode=='project_snapshot':
        budget_path=_path(request['budget_file']);budget_raw=read_metadata(budget_path)
        if hashlib.sha256(budget_raw).hexdigest()!=request['budget_sha256']:
            raise ValueError('input_identity')
        budget=_json(budget_raw)
        if type(budget) is dict and budget.get('group')=='large':
            from .project_partition import validate_project_partition_request
            partition_metadata=validate_project_partition_request(request=request,
                controller_evidence=controller_evidence,cancelled=cancelled)
    read_current = read_request if authorized_source_mode == 'project_snapshot' else read_metadata

    def check_metadata():
        if read_current(request_path) != raw:
            raise ValueError('controller_request_changed')
        _require_readonly_mount(request_path)
    if authorized_source_mode == 'artificial':
        guard = _ArtificialRequestGuard(check_metadata=check_metadata, cancelled=cancelled,
            started=started, lifecycle_seconds=lifecycle_seconds)
        def boundary(stage, **details):
            guard(force=True)
            if progress is not None:
                progress(stage, **details)
        batch_progress = dict(progress=boundary)
    else:
        # Real request checks remain per-call; partition inputs are rechecked at boundaries.
        def guard():
            if time.monotonic()-started >= lifecycle_seconds:
                raise ValueError('lifecycle_timeout')
            check_metadata()
            return cancelled()
        def boundary(stage, **details):
            _check_cancel(guard)
            if progress is not None:progress(stage,**details)
            if partition_metadata is not None:
                from .project_partition import recheck_project_partition_metadata
                recheck_project_partition_metadata(partition_metadata,cancelled=guard)
        batch_progress = dict(progress=boundary)
    _check_cancel(guard)
    stage = execute_readonly_batch(request, cancelled=guard,
        **batch_progress,
        controller_evidence=controller_evidence)
    if authorized_source_mode == 'artificial':
        guard(force=True)
    elif partition_metadata is not None:
        from .project_partition import recheck_project_partition_metadata
        recheck_project_partition_metadata(partition_metadata,cancelled=guard)
    if authorized_source_mode=='project_snapshot':
        boundary('task_staged')
    elif progress is not None:
        progress('task_staged')
    return stage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--request-sha256', required=True)
    parser.add_argument('--approval-sha256', required=True)
    parser.add_argument('--roots-sha256', required=True)
    parser.add_argument('--image-id', required=True)
    parser.add_argument('--git-revision', required=True)
    parser.add_argument('--image-user', required=True)
    parser.add_argument('--source-status', required=True)
    parser.add_argument('--lifecycle-seconds', type=int, required=True)
    parser.add_argument('--failure-evidence', type=Path)
    parser.add_argument('--authorized-source-mode', choices=('artificial', 'project_snapshot'),
                        default='artificial')
    args = parser.parse_args()
    stopped = False
    def stop(signum, frame):
        nonlocal stopped
        stopped = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    trace = FailureTrace()
    diagnostic_path_ready = False
    try:
        if args.failure_evidence is not None:
            path = args.failure_evidence
            if (not path.is_absolute() or path.parent.resolve(strict=True) != path.parent
                    or path.exists() or path.is_symlink() or path == args.request):
                raise ValueError('output_path')
            diagnostic_path_ready = True
        execute_controlled_batch(request_file=args.request, expected_request_sha256=args.request_sha256,
            expected_approval_sha256=args.approval_sha256, expected_roots_sha256=args.roots_sha256,
            actual_image=dict(image_id=args.image_id, git_revision=args.git_revision,
                              user=args.image_user, source_status=args.source_status),
            lifecycle_seconds=args.lifecycle_seconds,
            authorized_source_mode=args.authorized_source_mode,
            cancelled=lambda: stopped, progress=trace.advance)
        status = ('CONTROLLED_SOURCE_ONLY_TASK_STAGED' if args.authorized_source_mode == 'project_snapshot'
                  else 'CONTROLLED_ARTIFICIAL_TASK_STAGED')
        print(json.dumps(dict(status=status, real_execution_ready=False)))
        return 0
    except Exception as error:
        failure = trace.failure(error, args.request_sha256, args.authorized_source_mode)
        saved = False
        if diagnostic_path_ready:
            try:
                write_json_exclusive(args.failure_evidence, failure)
                saved = True
            except (OSError, ValueError):
                pass
        status = ('CONTROLLED_SOURCE_ONLY_TASK_FAILED' if args.authorized_source_mode == 'project_snapshot'
                  else 'CONTROLLED_ARTIFICIAL_TASK_FAILED')
        print(json.dumps(dict(status=status, reason=failure['code'], failure=failure,
                              diagnostic_saved=saved)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

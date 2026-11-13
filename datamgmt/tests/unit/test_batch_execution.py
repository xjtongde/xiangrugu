"""Synthetic execution must bind inputs and never publish partial answers."""
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import pytest
import yaml

from test_sqlite_structure_probe import args
from test_sqlite_expectation_probe import canary_args
from xiangrugu_datamgmt.sqlite_values import SQLiteValueLimits
from xiangrugu_datamgmt.unordered_values import UnorderedLimits


def implementation():
    from xiangrugu_datamgmt import batch_execution
    return batch_execution


def bind(path, document):
    path.write_text(json.dumps(document), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def batch_request(canary_args):
    root = Path(canary_args.roots).parent
    config = yaml.safe_load(Path(canary_args.roots).read_text())
    config["roots"]["usedata"]["path"] = str(root / "authority-never-read")
    Path(canary_args.roots).write_text(yaml.safe_dump(config))
    certificate = json.loads(Path(canary_args.certificate).read_text())
    certificate["source_path"] = config["roots"]["usedata"]["path"]
    canary_args.certificate_sha256 = bind(Path(canary_args.certificate), certificate)
    scope = json.loads(Path(canary_args.scope_file).read_text())
    scope.update(source_read_authorized=False, synthetic_data_authorized=True)
    canary_args.scope_sha256 = bind(Path(canary_args.scope_file), scope)
    budget = dict(version=1, synthetic_only=True, max_seconds=60,
        read_limits=asdict(SQLiteValueLimits(max_rows=100, max_file_bytes=1048576)),
        sort_limits=asdict(UnorderedLimits(max_rows=100, max_temp_bytes=64*1024**2)))
    budget_path = root / "budget.json"
    return dict(vars(canary_args), synthetic_root=str(root), synthetic_only=True,
        roots_sha256=hashlib.sha256(Path(canary_args.roots).read_bytes()).hexdigest(),
        budget_file=str(budget_path), budget_sha256=bind(budget_path, budget))


def test_staging_only_then_exclusive_publication(batch_request):
    module = implementation()
    staged = module.execute_batch(batch_request)
    final = Path(batch_request["output"])
    assert not final.exists()
    result = json.loads(staged.read_text())
    assert result["complete"] and result["file_digest_passes"] == 2
    assert result["synthetic_only"] and result["full_snapshot_verified_this_run"]
    assert result["objects"][0]["expected_count"] == 0
    assert not result["ready_for_import"]
    module.publish_batch(staged, final)
    assert json.loads(final.read_text()) == result
    with pytest.raises(FileExistsError):
        module.publish_batch(staged, final)


@pytest.mark.parametrize("field", ["roots_sha256", "scope_sha256", "budget_sha256", "certificate_sha256"])
def test_unbound_inputs_fail_before_reading(batch_request, field, monkeypatch):
    module = implementation()
    monkeypatch.setattr(module, "verify_snapshot", lambda *a, **k: pytest.fail("too early"))
    batch_request[field] = "0"*64
    with pytest.raises(ValueError):
        module.execute_batch(batch_request)
    assert not Path(batch_request["output"]).exists()


@pytest.mark.parametrize("change", ["real", "duplicate", "extra", "huge_budget", "outside", "alias", "empty"])
def test_malformed_scope_or_budget_is_rejected_before_snapshot(batch_request, change, monkeypatch):
    module = implementation()
    scope_path = Path(batch_request["scope_file"])
    scope = json.loads(scope_path.read_text())
    if change == "real":
        scope["source_read_authorized"] = True
    elif change == "duplicate":
        scope["objects"].append(scope["objects"][0])
    elif change == "extra":
        scope["surprise"] = True
    elif change == "empty":
        scope["objects"] = []
    elif change == "huge_budget":
        path = Path(batch_request["budget_file"])
        budget = json.loads(path.read_text())
        budget["sort_limits"]["max_temp_bytes"] = 2**40
        batch_request["budget_sha256"] = bind(path, budget)
    elif change == "outside":
        batch_request["synthetic_root"] = str(Path(batch_request["synthetic_root"]) / "scratch")
    else:
        batch_request["output"] = batch_request["scope_file"]
    batch_request["scope_sha256"] = bind(scope_path, scope)
    monkeypatch.setattr(module, "verify_snapshot", lambda *a, **k: pytest.fail("too early"))
    with pytest.raises((ValueError, FileExistsError)):
        module.execute_batch(batch_request)


def test_snapshot_extra_member_blocks_batch(batch_request):
    root = Path(batch_request["synthetic_root"]) / "snapshots" / batch_request["snapshot_id"]
    (root / "unlisted").write_text("artificial")
    with pytest.raises(ValueError):
        implementation().execute_batch(batch_request)
    assert not Path(batch_request["output"]).exists()


def test_metadata_change_after_batch_never_stages(batch_request, monkeypatch):
    module = implementation()
    original = module.summarize_sqlite_batch
    def changing(*a, **kw):
        result = original(*a, **kw)
        Path(batch_request["budget_file"]).write_text("{}")
        return result
    monkeypatch.setattr(module, "summarize_sqlite_batch", changing)
    with pytest.raises(ValueError):
        module.execute_batch(batch_request)
    assert not Path(batch_request["output"]).exists()


def test_fsync_and_cancel_fail_before_publication(batch_request, monkeypatch):
    module = implementation()
    staged = module.execute_batch(batch_request)
    final = Path(batch_request["output"])
    with pytest.raises(ValueError):
        module.publish_batch(staged, final, cancelled=lambda: True)
    monkeypatch.setattr(module.os, "fsync", lambda fd: (_ for _ in ()).throw(OSError("synthetic")))
    with pytest.raises(OSError):
        module.publish_batch(staged, final)
    assert not final.exists()


def test_artificial_two_table_worker_produces_only_staging(tmp_path):
    from xiangrugu_datamgmt import synthetic_batch_probe
    staged = synthetic_batch_probe.run(tmp_path, image_id="sha256:"+"1"*64, git_revision="2"*40)
    report = json.loads(staged.read_text())
    assert [o["expected_count"] for o in report["objects"]] == [5, 0]
    assert report["file_digest_passes"] == 2
    assert not staged.with_name("batch.json").exists()


def test_bad_identity_rejected_before_snapshot(batch_request, monkeypatch):
    module = implementation()
    path = Path(batch_request["scope_file"])
    scope = json.loads(path.read_text())
    scope["objects"][0]["source_object_id"] = "1"*64
    batch_request["scope_sha256"] = bind(path, scope)
    monkeypatch.setattr(module, "verify_snapshot", lambda *a, **k: pytest.fail("too early"))
    with pytest.raises(ValueError):
        module.execute_batch(batch_request)

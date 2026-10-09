from pathlib import Path
import shutil

import pytest

from xiangrugu_datamgmt.snapshots import SnapshotError, create_snapshot, verify_snapshot, inventory


@pytest.fixture
def sample(tmp_path):
    source = tmp_path / "authority"
    source.mkdir()
    (source / "nested").mkdir()
    (source / "empty").mkdir()
    (source / "nested" / "原件.bin").write_bytes(b"original\x00\xff\n")
    return source, tmp_path / "snapshots", tmp_path / "evidence"


def create(sample, **kwargs):
    source, snapshots, evidence = sample
    return create_snapshot(source, expected_source=source, snapshot_root=snapshots, evidence_root=evidence, snapshot_id="v1", vcs_ref="1" * 40, image_digest="sha256:" + "2" * 64, **kwargs)


def test_copy_preserves_source_bytes_and_empty_directories(sample):
    source, snapshots, evidence = sample
    before = inventory(source)
    certificate = create(sample)
    assert inventory(source) == before == inventory(snapshots / "v1")
    assert (snapshots / "v1" / "empty").is_dir()
    assert certificate["source_path"] == str(source)
    assert verify_snapshot(snapshots / "v1", evidence / "v1.json", expected_source=source)["snapshot_id"] == "v1"


@pytest.mark.parametrize("change", ["changed", "missing", "extra"])
def test_modified_snapshot_is_rejected(sample, change):
    create(sample)
    source, snapshots, evidence = sample
    root = snapshots / "v1"
    member = root / "nested" / "原件.bin"
    if change == "changed":
        member.write_bytes(b"different")
    elif change == "missing":
        member.unlink()
    else:
        (root / "unexpected").write_bytes(b"extra")
    with pytest.raises(SnapshotError):
        verify_snapshot(root, evidence / "v1.json", expected_source=source)


def test_wrong_source_does_not_create_a_copy(sample):
    source, snapshots, evidence = sample
    with pytest.raises(SnapshotError):
        create_snapshot(source, expected_source=source.parent / "wrong", snapshot_root=snapshots, evidence_root=evidence, snapshot_id="v1", vcs_ref="1" * 40, image_digest="sha256:" + "2" * 64)
    assert not snapshots.exists()


def test_symlinks_are_rejected(sample):
    source, _, evidence = sample
    (source / "link").symlink_to(source / "nested" / "原件.bin")
    with pytest.raises(SnapshotError):
        create(sample)
    assert not (evidence / "v1.json").exists()


def test_existing_snapshot_is_never_overwritten(sample):
    create(sample)
    with pytest.raises(SnapshotError):
        create(sample)


def test_source_change_during_copy_blocks_completion(sample, monkeypatch):
    source, _, evidence = sample
    original = shutil.copyfile
    def changing_copy(src, dst, **kwargs):
        result = original(src, dst, **kwargs)
        Path(src).write_bytes(b"concurrent source update")
        return result
    monkeypatch.setattr(shutil, "copyfile", changing_copy)
    with pytest.raises(SnapshotError):
        create(sample)
    assert not (evidence / "v1.json").exists()
    assert (evidence / "v1.failed.json").is_file()


def test_copy_interruption_blocks_completion(sample, monkeypatch):
    _, _, evidence = sample
    def interrupted(*args, **kwargs):
        raise OSError("synthetic interruption")
    monkeypatch.setattr(shutil, "copyfile", interrupted)
    with pytest.raises(SnapshotError):
        create(sample)
    assert not (evidence / "v1.json").exists()


def test_insufficient_space_blocks_copy(sample, monkeypatch):
    monkeypatch.setattr(shutil, "disk_usage", lambda _: type("Usage", (), {"free": 0})())
    with pytest.raises(SnapshotError):
        create(sample)


def test_unreadable_directory_is_not_silently_omitted(sample):
    source, _, evidence = sample
    restricted = source / "nested"
    restricted.chmod(0)
    try:
        with pytest.raises(SnapshotError):
            create(sample)
        assert not (evidence / "v1.json").exists()
    finally:
        restricted.chmod(0o755)


def test_missing_certificate_is_rejected(sample):
    source, snapshots, evidence = sample
    create(sample)
    (evidence / "v1.json").unlink()
    with pytest.raises(SnapshotError):
        verify_snapshot(snapshots / "v1", evidence / "v1.json", expected_source=source)


def test_output_inside_authority_is_rejected(sample):
    source, _, evidence = sample
    with pytest.raises(SnapshotError):
        create_snapshot(source, expected_source=source, snapshot_root=source / "output", evidence_root=evidence, snapshot_id="v1", vcs_ref="1" * 40, image_digest="sha256:" + "2" * 64)


@pytest.mark.parametrize("identifier", ["../escape", "/absolute", ".", "bad/name"])
def test_invalid_snapshot_identifiers(sample, identifier):
    source, snapshots, evidence = sample
    with pytest.raises(SnapshotError):
        create_snapshot(source, expected_source=source, snapshot_root=snapshots, evidence_root=evidence, snapshot_id=identifier, vcs_ref="1" * 40, image_digest="sha256:" + "2" * 64)

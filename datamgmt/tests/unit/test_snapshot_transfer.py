"""Transport failures must never produce a verified snapshot."""
import io
import tarfile
from pathlib import Path
import subprocess
import sys
import yaml

import pytest

from xiangrugu_datamgmt import snapshots


def archive(entries):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as writer:
        root = tarfile.TarInfo(".")
        root.type = tarfile.DIRTYPE
        writer.addfile(root)
        for name, payload, kind in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = len(payload) if kind == tarfile.REGTYPE else 0
            writer.addfile(member, io.BytesIO(payload) if member.isfile() else None)
    stream.seek(0)
    return stream


def sample(payload=b"abc"):
    return archive([("./empty", b"", tarfile.DIRTYPE), ("./data", payload, tarfile.REGTYPE)])


def read(stream, **kwargs):
    assert hasattr(snapshots, "read_snapshot_tar"), "restricted stream receiver is missing"
    return snapshots.read_snapshot_tar(stream, **kwargs)


def test_stream_preserves_empty_directory_and_hashes_raw_bytes(tmp_path):
    members = read(sample(), destination=tmp_path)
    assert members == [
        {"path": "data", "kind": "file", "size": 3,
         "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"},
        {"path": "empty", "kind": "directory"},
    ]
    assert (tmp_path / "data").read_bytes() == b"abc"
    assert (tmp_path / "empty").is_dir()


@pytest.mark.parametrize("name,kind", [
    ("../escape", tarfile.REGTYPE), ("/absolute", tarfile.REGTYPE),
    ("a\\b", tarfile.REGTYPE), ("link", tarfile.SYMTYPE),
    ("hard", tarfile.LNKTYPE), ("fifo", tarfile.FIFOTYPE),
])
def test_stream_rejects_unsafe_members(tmp_path, name, kind):
    with pytest.raises(snapshots.SnapshotError):
        read(archive([(name, b"", kind)]), destination=tmp_path)
    assert not (tmp_path.parent / "escape").exists()


def test_stream_rejects_duplicate_members():
    with pytest.raises(snapshots.SnapshotError):
        read(archive([("a", b"a", tarfile.REGTYPE), ("a", b"b", tarfile.REGTYPE)]))


@pytest.mark.parametrize("transform", [
    lambda data: data[:1025], lambda data: data[:2048],
    lambda data: data + b"garbage",
])
def test_stream_rejects_truncation_and_trailing_bytes(transform):
    with pytest.raises(snapshots.SnapshotError):
        read(io.BytesIO(transform(sample().getvalue())))


def test_stream_enforces_budget_before_writing_payload(tmp_path):
    with pytest.raises(snapshots.SnapshotError):
        read(sample(), destination=tmp_path, max_bytes=2)
    assert not (tmp_path / "data").exists()


def transfer(tmp_path):
    assert hasattr(snapshots, "StreamSnapshot"), "three-pass snapshot protocol is missing"
    return snapshots.StreamSnapshot(
        source_path="/authority/usedata", snapshot_root=tmp_path / "copies",
        evidence_root=tmp_path / "evidence", snapshot_id="2026-10-07-test",
        vcs_ref="1" * 40, image_digest="sha256:" + "2" * 64,
        source_identity={"resolved_path": "/authority/usedata", "device": 71, "inode": 123},
    )


def test_three_passes_and_independent_copy_read_produce_certificate(tmp_path):
    run = transfer(tmp_path)
    run.prepare(sample())
    run.copy(sample())
    run.check(sample())
    assert not (tmp_path / "evidence/2026-10-07-test.json").exists()
    certificate = run.finish()
    assert certificate["status"] == "VERIFIED"
    assert certificate["source_status"] == "dirty"
    assert snapshots.verify_snapshot(
        tmp_path / "copies/2026-10-07-test", tmp_path / "evidence/2026-10-07-test.json",
        expected_source=Path("/authority/usedata"),
    ) == certificate


@pytest.mark.parametrize("phase", ["copy", "finish", "disk"])
def test_changed_source_or_corrupted_copy_cannot_be_certified(tmp_path, phase):
    run = transfer(tmp_path)
    run.prepare(sample())
    if phase == "copy":
        with pytest.raises(snapshots.SnapshotError):
            run.copy(sample(b"changed"))
    else:
        run.copy(sample())
        if phase == "disk":
            (tmp_path / "copies/.2026-10-07-test.incomplete/data").write_bytes(b"bad")
        with pytest.raises(snapshots.SnapshotError):
            run.check(sample(b"changed") if phase == "finish" else sample())
    assert not (tmp_path / "evidence/2026-10-07-test.json").exists()
    assert not (tmp_path / "copies/2026-10-07-test").exists()


def test_existing_version_is_never_overwritten(tmp_path):
    run = transfer(tmp_path)
    run.prepare(sample())
    with pytest.raises(snapshots.SnapshotError):
        transfer(tmp_path).prepare(sample())


def test_identity_change_cannot_be_certified(tmp_path):
    run = transfer(tmp_path)
    run.prepare(sample())
    run.copy(sample())
    changed = transfer(tmp_path)
    changed.identity["inode"] = 999
    with pytest.raises(snapshots.SnapshotError):
        changed.check(sample())
    assert not (tmp_path / "evidence/2026-10-07-test.json").exists()


def test_copy_damage_between_check_and_certify_is_rejected(tmp_path):
    run = transfer(tmp_path)
    run.prepare(sample())
    run.copy(sample())
    run.check(sample())
    (tmp_path / "copies/.2026-10-07-test.incomplete/data").write_bytes(b"bad")
    with pytest.raises(snapshots.SnapshotError):
        run.finish()
    assert not (tmp_path / "evidence/2026-10-07-test.json").exists()


def test_cli_phases_cannot_skip_source_checks(tmp_path):
    config = yaml.safe_load((Path(__file__).resolve().parents[2] / "config/roots.yaml").read_text())
    config["deployment"]["source_snapshots"]["container_root"] = str(tmp_path / "copies")
    config["deployment"]["source_snapshots"]["container_evidence_root"] = str(tmp_path / "evidence")
    path = tmp_path / "roots.yaml"
    path.write_text(yaml.safe_dump(config))
    command = [sys.executable, "-m", "xiangrugu_datamgmt.snapshot_transfer",
               "--config", str(path), "--snapshot-id", "2026-10-07-cli",
               "--source-path", "/mnt/wd61workmetadata/usedata", "--device", "71", "--inode", "123",
               "--vcs-ref", "1" * 40, "--image-digest", "sha256:" + "2" * 64, "--reserve-bytes", "0"]
    before = subprocess.run(command + ["finish"], capture_output=True)
    assert before.returncode != 0
    for phase in ("prepare", "copy", "check", "finish"):
        result = subprocess.run(command + [phase], input=sample().getvalue() if phase != "finish" else b"", capture_output=True)
        assert result.returncode == 0, result.stderr.decode()
    assert (tmp_path / "evidence/2026-10-07-cli.json").exists()

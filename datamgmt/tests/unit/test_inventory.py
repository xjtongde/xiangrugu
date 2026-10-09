import hashlib
import io
import os
from pathlib import Path
import tempfile
import zipfile

import pytest


def builder(**limits):
    from xiangrugu_datamgmt.inventory import InventoryBuilder
    limits.setdefault("temp_root", tempfile.gettempdir())
    return InventoryBuilder(**limits)


def zip_bytes(members):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in members:
            archive.writestr(name, content)
    return output.getvalue()


def codes(manifest):
    return {issue.code for issue in manifest.issues}


def tree_state(root):
    return [(p.relative_to(root).as_posix(), p.lstat().st_mode, p.lstat().st_mtime_ns,
             hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() and not p.is_symlink() else None)
            for p in sorted(root.rglob("*"))]


def test_plain_empty_unknown_and_deterministic_readonly_manifest(tmp_path):
    (tmp_path / "empty").write_bytes(b"")
    (tmp_path / "plain.bin").write_bytes(b"abc")
    (tmp_path / "emptydir").mkdir()
    before = tree_state(tmp_path)
    first, second = builder().scan(tmp_path), builder().scan(tmp_path)
    assert first.complete
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.sha256 == hashlib.sha256(first.canonical_bytes()).hexdigest()
    members = {entry.relative_path: entry for entry in first.entries}
    assert members["plain.bin"].sha256 == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert members["empty"].size == 0
    assert members["emptydir"].kind == "directory"
    assert members["plain.bin"].signature == "unknown"
    assert tree_state(tmp_path) == before
    with pytest.raises((AttributeError, TypeError)):
        members["empty"].size = 2


def test_signature_drives_nested_archives_not_suffix(tmp_path):
    nested = zip_bytes([("数据.csv", b"a,b\n1,2\n"), ("empty/", b"")])
    (tmp_path / "Mixed.ZIP.zip").write_bytes(zip_bytes([("inside.bin", nested)]))
    (tmp_path / "fake.zip").write_bytes(b"plain")
    result = builder().scan(tmp_path)
    assert result.complete
    assert "extension_mismatch" in codes(result)
    inner = next(entry for entry in result.entries if entry.archive_chain == ("inside.bin", "数据.csv"))
    assert inner.relative_path == "Mixed.ZIP.zip"
    assert inner.size == 8
    assert inner.archive_ordinals == (0, 0)
    assert any(entry.archive_chain == ("inside.bin", "empty/") and entry.kind == "directory" for entry in result.entries)


def test_symlinks_special_files_and_case_collisions_are_explicit(tmp_path):
    (tmp_path / "A.txt").write_bytes(b"A")
    (tmp_path / "a.txt").write_bytes(b"a")
    (tmp_path / "link").symlink_to("A.txt")
    os.mkfifo(tmp_path / "fifo")
    result = builder().scan(tmp_path)
    assert not result.complete
    assert {"symlink", "special_file", "case_collision"} <= codes(result)
    assert next(entry for entry in result.entries if entry.relative_path == "link").sha256 is None


def test_unreadable_member_and_directory_are_not_omitted(tmp_path):
    file = tmp_path / "locked"
    file.write_bytes(b"secret fixture")
    directory = tmp_path / "denied"
    directory.mkdir()
    (directory / "child").write_bytes(b"x")
    file.chmod(0)
    directory.chmod(0)
    try:
        result = builder().scan(tmp_path)
        assert not result.complete
        assert "read_error" in codes(result)
        assert {"locked", "denied"} <= {entry.relative_path for entry in result.entries}
    finally:
        file.chmod(0o600)
        directory.chmod(0o700)


@pytest.mark.parametrize("limit, value, expected", [
    ("max_member_bytes", 100, "member_limit"),
    ("max_total_bytes", 150, "total_limit"),
    ("max_members", 1, "count_limit"),
    ("max_depth", 0, "depth_limit"),
    ("max_ratio", 2, "ratio_limit"),
])
def test_zip_resource_limits_never_claim_complete(tmp_path, limit, value, expected):
    (tmp_path / "bomb.zip").write_bytes(zip_bytes([("big", b"0" * 10000), ("other", b"x")]))
    result = builder(**{limit: value}).scan(tmp_path)
    assert not result.complete
    assert expected in codes(result)


def test_duplicate_and_traversing_zip_members_keep_physical_identity(tmp_path):
    with pytest.warns(UserWarning, match="Duplicate"):
        raw = zip_bytes([("same", b"a"), ("same", b"b"), ("../escape", b"bad")])
    (tmp_path / "data.zip").write_bytes(raw)
    result = builder().scan(tmp_path)
    assert not result.complete
    assert {"duplicate_member", "unsafe_path"} <= codes(result)
    same = [entry for entry in result.entries if entry.archive_chain == ("same",)]
    assert len(same) == 2
    assert same[0].sha256 != same[1].sha256
    assert {entry.archive_ordinals for entry in same} == {(0,), (1,)}
    assert not (tmp_path.parent / "escape").exists()


def test_corrupt_zip_is_recorded_with_original_digest(tmp_path):
    raw = b"PK\x03\x04bad"
    (tmp_path / "bad").write_bytes(raw)
    result = builder().scan(tmp_path)
    assert not result.complete
    assert "archive_error" in codes(result)
    assert result.entries[0].sha256 == hashlib.sha256(raw).hexdigest()


def test_checksum_raw_digest_and_every_anomaly_are_preserved(tmp_path):
    (tmp_path / "x").write_bytes(b"abc")
    digest = b"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    raw = digest + b"  x\n" + digest + b" *x\n" + digest + b"  ../escape\nnot-a-hash  z\nbad line\n" + b"\0" * 5
    (tmp_path / "SHA256SUMS-b2").write_bytes(raw)
    result = builder().scan(tmp_path)
    assert not result.complete
    assert {"checksum_nul", "checksum_duplicate", "checksum_path", "checksum_digest", "checksum_line"} <= codes(result)
    ledger = next(entry for entry in result.entries if entry.relative_path == "SHA256SUMS-b2")
    assert ledger.sha256 == hashlib.sha256(raw).hexdigest()
    assert any(issue.code == "checksum_nul" and issue.detail == "count=5" for issue in result.issues)


@pytest.mark.parametrize("line, expected", [
    (b"a" * 64 + b"  missing\n", "checksum_missing"),
    (b"a" * 64 + b"  x\n", "checksum_mismatch"),
    (b"a" * 64 + b"  \xff\n", "checksum_encoding"),
])
def test_checksum_missing_mismatching_and_invalid_encoding(tmp_path, line, expected):
    (tmp_path / "x").write_bytes(b"abc")
    (tmp_path / "SHA256SUMS").write_bytes(line)
    result = builder().scan(tmp_path)
    assert not result.complete
    assert expected in codes(result)


def test_valid_checksum_uses_ledger_parent_and_keeps_assertions(tmp_path):
    directory = tmp_path / "nested"
    directory.mkdir()
    (directory / "x").write_bytes(b"abc")
    (directory / "SHA256SUMS").write_bytes(b"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad  ./x\n")
    result = builder().scan(tmp_path)
    assert result.complete
    assert len(result.checksums) == 1
    assert result.checksums[0].target == "nested/x"
    assert result.checksums[0].matched is True


def test_builder_reuse_does_not_accumulate_scan_state(tmp_path):
    (tmp_path / "x").write_bytes(b"abc")
    scanner = builder()
    assert scanner.scan(tmp_path).canonical_bytes() == scanner.scan(tmp_path).canonical_bytes()


@pytest.mark.parametrize("limits", [{"max_members": 0}, {"max_member_bytes": -1}, {"max_depth": -1}, {"max_ratio": 0}])
def test_invalid_resource_limits_are_rejected(limits):
    with pytest.raises(ValueError):
        builder(**limits)


def test_exhausted_budget_never_fabricates_empty_digest(tmp_path):
    (tmp_path / "a").write_bytes(b"1234")
    (tmp_path / "b").write_bytes(b"x")
    result = builder(max_total_bytes=3).scan(tmp_path)
    assert not result.complete
    entries = {entry.relative_path: entry for entry in result.entries}
    assert entries["a"].sha256 is None
    # Rejecting a before reading leaves budget for b. Never invent an empty hash.
    assert entries["b"].sha256 == "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881"


def test_temp_directory_inside_source_is_rejected_without_writing(tmp_path, monkeypatch):
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    (tmp_path / "archive.zip").write_bytes(zip_bytes([("x", b"x")]))
    before = tree_state(tmp_path)
    result = builder().scan(tmp_path)
    assert not result.complete
    assert "unsafe_temp_root" in codes(result)
    assert tree_state(tmp_path) == before


def test_zip_nul_name_keeps_original_name_not_cpython_truncation(tmp_path):
    raw = zip_bytes([("aXb", b"x")]).replace(b"aXb", b"a\0b")
    (tmp_path / "nul.zip").write_bytes(raw)
    result = builder().scan(tmp_path)
    assert not result.complete
    assert "unsafe_path" in codes(result)
    assert any(entry.archive_chain == ("a\0b",) for entry in result.entries)
    assert not any(entry.archive_chain == ("a",) for entry in result.entries)


def test_zip_bad_crc_cannot_receive_a_completed_digest(tmp_path):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("x", b"ABCXYZ")
    (tmp_path / "crc.zip").write_bytes(output.getvalue().replace(b"ABCXYZ", b"ABCXYQ"))
    result = builder().scan(tmp_path)
    assert not result.complete
    assert "archive_error" in codes(result)
    assert next(entry for entry in result.entries if entry.archive_chain == ("x",)).sha256 is None


def test_central_directory_limit_is_checked_before_zip_metadata(tmp_path):
    (tmp_path / "archive.zip").write_bytes(zip_bytes([("long_name", b"x")]))
    result = builder(max_central_bytes=1).scan(tmp_path)
    assert not result.complete
    assert "central_limit" in codes(result)
    assert len(result.entries) == 1


@pytest.mark.parametrize("prefix, expected", [
    (b"SQLite format 3\0", "sqlite"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "ole"),
    (b"II*\0", "tiff"), (b"MM\0*", "tiff"), (b"%PDF-", "pdf"),
])
def test_media_signatures_are_byte_observations(tmp_path, prefix, expected):
    (tmp_path / "misleading.csv").write_bytes(prefix + b"example")
    result = builder().scan(tmp_path)
    assert result.entries[0].signature == expected


def test_nested_checksum_is_scoped_to_physical_container(tmp_path):
    ledger = b"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad  x\n"
    (tmp_path / "archive.zip").write_bytes(zip_bytes([("dir/x", b"abc"), ("dir/SHA256SUMS", ledger)]))
    result = builder().scan(tmp_path)
    assert result.complete
    assert result.checksums[0].matched
    assert result.checksums[0].target == "dir/x"


def test_symlink_root_cannot_be_scanned(tmp_path):
    (tmp_path / "dir").mkdir()
    (tmp_path / "link").symlink_to("dir", target_is_directory=True)
    result = builder().scan(tmp_path / "link")
    assert not result.complete
    assert "unsafe_root" in codes(result)


def test_plain_files_do_not_need_temporary_disk_copies(tmp_path, monkeypatch):
    import tempfile
    forbidden = tmp_path.parent / "forbidden-temp"
    forbidden.mkdir()
    forbidden.chmod(0)
    monkeypatch.setattr(tempfile, "tempdir", str(forbidden))
    (tmp_path / "plain.bin").write_bytes(b"x" * (2 * 1024**2))
    try:
        result = builder().scan(tmp_path)
        assert result.complete
        assert result.entries[0].size == 2 * 1024**2
        assert result.entries[0].sha256 is not None
    finally:
        forbidden.chmod(0o700)


def test_checksum_line_budget_preserves_raw_digest_and_marks_incomplete(tmp_path):
    raw = b"\n" * 5
    (tmp_path / "SHA256SUMS").write_bytes(raw)
    result = builder(max_members=2).scan(tmp_path)
    assert not result.complete
    assert "checksum_count_limit" in codes(result)
    assert result.entries[0].sha256 == hashlib.sha256(raw).hexdigest()
    assert len(result.issues) <= 3


def test_zip64_end_record_is_explicitly_blocked(tmp_path):
    import struct
    raw = bytearray(zip_bytes([]))
    struct.pack_into("<HH", raw, 8, 65535, 65535)
    (tmp_path / "zip64.zip").write_bytes(raw)
    result = builder().scan(tmp_path)
    assert not result.complete
    assert "unsupported_zip64" in codes(result)


def test_filesystem_member_limit_keeps_partial_evidence(tmp_path):
    for name in ("a", "b", "c"):
        (tmp_path / name).write_bytes(b"x")
    result = builder(max_members=1).scan(tmp_path)
    assert not result.complete
    assert "count_limit" in codes(result)
    assert len(result.entries) == 1


def test_empty_zip_is_still_a_container(tmp_path):
    (tmp_path / "empty.zip").write_bytes(zip_bytes([]))
    result = builder().scan(tmp_path)
    assert result.complete
    assert result.entries[0].signature == "zip"


def test_partial_manifest_is_independent_of_directory_creation_order(tmp_path):
    left, right = tmp_path / "left", tmp_path / "right"
    left.mkdir()
    right.mkdir()
    for name in ("a", "b", "c"):
        (left / name).write_bytes(b"x")
    for name in ("c", "b", "a"):
        (right / name).write_bytes(b"x")
    assert builder(max_members=1).scan(left).canonical_bytes() == builder(max_members=1).scan(right).canonical_bytes()


def test_checksum_cache_budget_is_scan_wide(tmp_path):
    (tmp_path / "SHA256SUMS-a").write_bytes(b"bad\n")
    (tmp_path / "SHA256SUMS-b").write_bytes(b"bad\n")
    result = builder(max_checksum_bytes=4).scan(tmp_path)
    assert not result.complete
    assert "checksum_limit" in codes(result)
    assert len([issue for issue in result.issues if issue.code == "checksum_line"]) == 1


@pytest.mark.parametrize("compression", [zipfile.ZIP_LZMA, zipfile.ZIP_BZIP2])
def test_unbudgeted_compression_methods_are_explicitly_blocked(tmp_path, compression):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=compression) as archive:
        archive.writestr("x", b"abc")
    (tmp_path / "archive.zip").write_bytes(output.getvalue())
    result = builder().scan(tmp_path)
    assert not result.complete
    assert "unsupported_compression" in codes(result)
    assert next(entry for entry in result.entries if entry.archive_chain == ("x",)).sha256 is None


def test_explicit_cache_root_is_not_silently_replaced_by_system_tmp(tmp_path):
    # A ZIP >1 MiB forces spooling. A missing cache directory must fail closed.
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("x", b"x" * (2 * 1024**2))
    (tmp_path / "archive.zip").write_bytes(output.getvalue())
    result = builder(temp_root=tmp_path.parent / "missing-cache").scan(tmp_path)
    assert not result.complete
    assert "read_error" in codes(result)

"""Exercise the development probe's actual byte-read and reference boundaries."""
import hashlib
from pathlib import Path
import runpy

import pytest

from test_text_values import projection


def probe():
    # Same relative layout in /workspace and /app candidate test image.
    return runpy.run_path(str(Path(__file__).parents[3] / "scripts" / "prepare-text-source-values.py"))


def test_probe_reads_only_bounded_regular_member(tmp_path):
    (tmp_path / "fixture.tab").write_bytes(b"h\nx\n")
    assert probe()["read_regular"](tmp_path, "fixture.tab", 4) == b"h\nx\n"
    with pytest.raises(ValueError, match="file_budget"):
        probe()["read_regular"](tmp_path, "fixture.tab", 3)


@pytest.mark.parametrize("relative", ["../fixture.tab", "/fixture.tab", "a//b", "./fixture.tab"])
def test_probe_rejects_escaping_or_noncanonical_path(tmp_path, relative):
    with pytest.raises(ValueError, match="path"):
        probe()["read_regular"](tmp_path, relative, 10)


def test_probe_rejects_symlink_member_and_parent(tmp_path):
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "fixture.tab").write_bytes(b"h\nx\n")
    (tmp_path / "link").symlink_to(tmp_path / "real", target_is_directory=True)
    (tmp_path / "member.tab").symlink_to(tmp_path / "real" / "fixture.tab")
    for relative in ("link/fixture.tab", "member.tab"):
        with pytest.raises(ValueError, match="symlink"):
            probe()["read_regular"](tmp_path, relative, 10)


def test_probe_independent_reference_preserves_empty_and_checks_prior_evidence():
    obj, decision = projection()
    obj["source_value_evidence"] = {
        "ordered_strings_sha256_including_header":
            hashlib.sha256(b'["h"]\n[""]\n').hexdigest()}
    summary, fields = probe()["independent_reference"](b'h\n""\n', obj, decision)
    assert fields == 1
    assert summary["row_count"] == 1 and summary["field_count"] == 2
    assert summary["stream_bytes"] == 114
    obj["source_value_evidence"]["ordered_strings_sha256_including_header"] = "0"*64
    with pytest.raises(ValueError, match="prior_reading_evidence"):
        probe()["independent_reference"](b'h\n""\n', obj, decision)

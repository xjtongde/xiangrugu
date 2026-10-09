"""Candidate checks must not waive strict inventory errors or authorize import."""
from dataclasses import replace
import hashlib
import importlib

import pytest

from xiangrugu_datamgmt.inventory import InventoryBuilder


def api():
    spec = importlib.util.find_spec("xiangrugu_datamgmt.checksum_candidates")
    assert spec is not None, "checksum candidate preview API is not implemented"
    return importlib.import_module(spec.name)


@pytest.fixture
def evidence(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "relocated").mkdir()
    (source / "publisher").mkdir()
    payload = b"original payload\n"
    digest = hashlib.sha256(payload).hexdigest()
    (source / "relocated" / "item.bin").write_bytes(payload)
    nul_raw = f"{digest}  relocated/item.bin\n".encode() + b"\x00" * 3
    binding_raw = f"{digest}  item.bin\n".encode()
    (source / "SHA256SUMS").write_bytes(nul_raw)
    (source / "publisher" / "SHA256SUMS.txt").write_bytes(binding_raw)
    manifest = InventoryBuilder(temp_root=tmp_path).scan(source)
    policy = {
        "version": 1, "status": "draft", "release_id": "2026-10-07-synthetic",
        "source_version": "synthetic", "inventory_sha256": manifest.sha256,
        "rules": [
            {"rule_id": "nul", "kind": "trailing_nul", "ledger": "SHA256SUMS",
             "raw_sha256": hashlib.sha256(nul_raw).hexdigest(), "raw_size": len(nul_raw),
             "valid_lines": 1, "trailing_nul_bytes": 3, "reason": "fixture tail"},
            {"rule_id": "binding", "kind": "exact_path_binding",
             "ledger": "publisher/SHA256SUMS.txt",
             "raw_sha256": hashlib.sha256(binding_raw).hexdigest(), "raw_size": len(binding_raw),
             "line": 1, "raw_name": "item.bin", "declared_target": "publisher/item.bin",
             "resolved_target": "relocated/item.bin", "expected_sha256": digest,
             "expected_size": len(payload), "reason": "explicit fixture binding"},
        ],
    }
    return manifest, policy, {"SHA256SUMS": nul_raw, "publisher/SHA256SUMS.txt": binding_raw}


def preview(evidence):
    manifest, policy, raw = evidence
    module = api()
    return module.preview_checksum_candidates(manifest, module.ChecksumCandidates.model_validate(policy), raw)


def test_preview_preserves_strict_evidence_and_never_authorizes_runtime(evidence):
    manifest, _, raw = evidence
    before = manifest.canonical_bytes(), dict(raw)
    result = preview(evidence)
    assert result["candidate_checks_passed"] is True
    assert result["runtime_applied"] is False
    assert result["ready_for_import"] is False
    assert result["strict_inventory_complete"] is False
    assert result["strict_issue_count"] == 3
    assert result["checks"][0]["trailing_nul_bytes"] == 3
    binding = result["checks"][1]
    assert binding["declared_target"] == "publisher/item.bin"
    assert binding["resolved_target"] == "relocated/item.bin"
    assert before == (manifest.canonical_bytes(), raw)


@pytest.mark.parametrize("field,value", [
    ("raw_sha256", "0" * 64), ("raw_size", 1),
    ("valid_lines", 2), ("trailing_nul_bytes", 4),
])
def test_nul_candidate_rejects_changed_assertion(evidence, field, value):
    evidence[1]["rules"][0][field] = value
    with pytest.raises(ValueError):
        preview(evidence)


@pytest.mark.parametrize("field,value", [
    ("line", 2), ("raw_name", "other.bin"), ("declared_target", "elsewhere/item.bin"),
    ("resolved_target", "absent/item.bin"), ("expected_sha256", "0" * 64),
    ("expected_size", 1), ("raw_sha256", "0" * 64),
])
def test_binding_candidate_has_no_name_or_hash_search_fallback(evidence, field, value):
    evidence[1]["rules"][1][field] = value
    with pytest.raises(ValueError):
        preview(evidence)


def test_rejects_changed_ledger_bytes(evidence):
    evidence[2]["SHA256SUMS"] += b"x"
    with pytest.raises(ValueError, match="raw ledger"):
        preview(evidence)


def test_rejects_changed_inventory(evidence):
    evidence[1]["inventory_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="inventory"):
        preview(evidence)


@pytest.mark.parametrize("changed_raw", ["inner_nul", "nonzero_tail", "short_tail", "bad_prefix"])
def test_nul_requires_exact_tail_even_when_raw_digest_is_relocked(evidence, changed_raw):
    manifest, policy, raw = evidence
    original = raw["SHA256SUMS"]
    changes = {
        "inner_nul": b"\0" + original[1:],
        "nonzero_tail": original[:-1] + b"x",
        "short_tail": original[:-1],
        "bad_prefix": b"z" + original[1:],
    }
    updated = changes[changed_raw]
    digest = hashlib.sha256(updated).hexdigest()
    raw["SHA256SUMS"] = updated
    changed = replace(manifest, entries=tuple(
        replace(e, size=len(updated), sha256=digest) if e.relative_path == "SHA256SUMS" else e
        for e in manifest.entries))
    policy["inventory_sha256"] = changed.sha256
    policy["rules"][0].update(raw_size=len(updated), raw_sha256=digest)
    with pytest.raises(ValueError, match="prefix|NUL"):
        preview((changed, policy, raw))


@pytest.mark.parametrize("change", ["duplicate", "size", "digest"])
def test_binding_requires_unique_exact_inventory_target(evidence, change):
    manifest, policy, raw = evidence
    target = next(e for e in manifest.entries if e.relative_path == "relocated/item.bin")
    if change == "duplicate":
        entries = manifest.entries + (target,)
    else:
        altered = replace(target, **({"size": 1} if change == "size" else {"sha256": "0" * 64}))
        entries = tuple(altered if e is target else e for e in manifest.entries)
    changed = replace(manifest, entries=entries)
    policy["inventory_sha256"] = changed.sha256
    with pytest.raises(ValueError, match="resolved target"):
        preview((changed, policy, raw))


def test_does_not_mask_declared_target_that_exists(evidence):
    manifest, policy, raw = evidence
    original = next(e for e in manifest.entries if e.relative_path == "relocated/item.bin")
    changed = replace(manifest, entries=manifest.entries + (replace(original, relative_path="publisher/item.bin"),))
    policy["inventory_sha256"] = changed.sha256
    with pytest.raises(ValueError, match="declared target"):
        preview((changed, policy, raw))


def test_nul_candidate_requires_all_prefix_assertions_matched(evidence):
    manifest, policy, raw = evidence
    changed = replace(manifest, checksums=tuple(
        replace(c, matched=False) if c.ledger == "SHA256SUMS" else c for c in manifest.checksums))
    policy["inventory_sha256"] = changed.sha256
    with pytest.raises(ValueError, match="prefix"):
        preview((changed, policy, raw))


def test_nul_candidate_rejects_impossible_count_without_allocating_padding(evidence):
    evidence[1]["rules"][0]["trailing_nul_bytes"] = 2**64
    with pytest.raises(ValueError, match="NUL"):
        preview(evidence)


@pytest.mark.parametrize("change", ["frozen", "duplicate", "unknown", "absolute"])
def test_candidate_model_refuses_activation_and_ambiguous_configuration(evidence, change):
    policy = evidence[1]
    if change == "frozen":
        policy["status"] = "frozen"
    elif change == "duplicate":
        policy["rules"].append(dict(policy["rules"][0]))
    elif change == "unknown":
        policy["rules"][0]["ignore_errors"] = True
    else:
        policy["rules"][0]["ledger"] = "/tmp/SHA256SUMS"
    with pytest.raises(ValueError):
        api().ChecksumCandidates.model_validate(policy)

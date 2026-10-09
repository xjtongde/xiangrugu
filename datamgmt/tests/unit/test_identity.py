import json
from pathlib import Path

import pytest

from xiangrugu_datamgmt.identity import member_id, source_object_id
from xiangrugu_datamgmt.model import SourceMember, Disposition, ImportRun, Artifact, ValidationResult


def test_fixed_identity_golden_vectors():
    vectors = json.loads((Path(__file__).parents[1] / "fixtures" / "identity.json").read_text(encoding="utf-8"))
    for vector in vectors:
        assert member_id(**vector["input"]) == vector["expected"]


def test_identity_preserves_unicode_case_and_archive_boundaries():
    def identity(path="a.zip", chain=("é.csv",), **kwargs):
        return member_id(release_id=kwargs.get("release_id", "v1"), relative_path=path, archive_chain=chain, sha256=kwargs.get("sha256", "a" * 64))
    values = {identity(), identity(chain=("e\u0301.csv",)), identity(chain=("É.csv",)), identity(chain=("x.zip", "é.csv")), identity(path="A.zip"), identity(release_id="v2"), identity(sha256="b" * 64)}
    assert len(values) == 7
    assert identity(chain=("a/b",)) != identity(chain=("a", "b"))


@pytest.mark.parametrize("path", ["../x", "/x", "a//b", "a/./b", "a\\b", "", "x\x00"])
def test_noncanonical_or_escaping_paths_are_rejected(path):
    with pytest.raises(ValueError):
        member_id(release_id="v1", relative_path=path, archive_chain=(), sha256="a" * 64)


def test_object_id_separates_carriers_and_original_names():
    def identity(name, carrier):
        return source_object_id(relative_path="a.zip", archive_chain=("data.mdb",), object_name=name, carrier=carrier)
    assert len({identity("People", "mdb"), identity("people", "mdb"), identity("People", "sqlite")}) == 3


def test_member_model_is_frozen_and_derives_identity():
    member = SourceMember(release_id="v1", relative_path="a.bin", archive_chain=(), sha256="a" * 64, size=0, carrier="binary", disposition=Disposition.BLOCKED)
    assert member.source_member_id == member_id(release_id="v1", relative_path="a.bin", archive_chain=(), sha256="a" * 64)
    with pytest.raises(ValueError):
        member.size = 1


@pytest.mark.parametrize("model", [SourceMember, ImportRun, Artifact, ValidationResult])
def test_domain_records_have_required_fields(model):
    with pytest.raises(ValueError):
        model()


def test_disposition_has_only_the_four_approved_cases():
    assert {value.value for value in Disposition} == {"IMPORT", "MIRROR", "NON_TABULAR", "BLOCKED"}


def test_negative_size_and_bad_digest_are_rejected():
    with pytest.raises(ValueError):
        SourceMember(release_id="v1", relative_path="a.bin", sha256="not-a-digest", size=-1, carrier="binary", disposition="IMPORT")


def test_validation_cannot_claim_conformance_with_mismatches():
    with pytest.raises(ValueError):
        ValidationResult(run_id="r1", gate="G3", status="CONFORMS", evidence_sha256="a" * 64, checked=2, mismatches=1)


@pytest.mark.parametrize("record", [
    ImportRun(run_id="r1", release_id="v1", vcs_ref="a" * 40, config_sha256="b" * 64, state="pending"),
    Artifact(artifact_id="a1", run_id="r1", kind="manifest", relative_path="manifest.json", sha256="a" * 64, size=0),
    ValidationResult(run_id="r1", gate="G0", status="CONFORMS", evidence_sha256="a" * 64, checked=1, mismatches=0),
])
def test_all_provenance_records_are_frozen(record):
    with pytest.raises(ValueError):
        record.run_id = "other"

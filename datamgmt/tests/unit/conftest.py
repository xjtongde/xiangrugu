"""Synthetic Task 5 contracts; no real source layout or approved release."""
import pytest

from xiangrugu_datamgmt.inventory import InventoryEntry, InventoryManifest


@pytest.fixture
def inventory():
    return InventoryManifest((
        InventoryEntry("data.csv", size=3, sha256="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),
        InventoryEntry("README", size=0, sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    ), (), (), ())


@pytest.fixture
def contract_doc(inventory):
    return {
        "version": 1, "release_id": "2026-10-07-synthetic", "source_version": "synthetic-v1",
        "inventory_sha256": inventory.sha256, "status": "draft", "review": None, "exceptions": [],
        "rules": [
            {"rule_id": "data", "selector": {"relative_path": "data.csv", "archive_chain": [], "archive_ordinals": []},
             "expected": {"kind": "file", "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "size": 3, "signature": "unknown"},
             "disposition": "IMPORT", "reason": "Synthetic business rows", "format_family": "csv",
             "encodings": [{"object_name": "data", "column": "name", "codec": "utf-8", "errors": "strict"}],
             "targets": [{"object_name": "data", "schema": "harv", "table": "synthetic__data", "expected_count": 1, "expected_sha256": "a" * 64}],
             "validator": "independent-csv-v1", "mirror_of": None, "mirror_evidence_sha256": None},
            {"rule_id": "readme", "selector": {"relative_path": "README", "archive_chain": [], "archive_ordinals": []},
             "expected": {"kind": "file", "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "size": 0, "signature": "unknown"},
             "disposition": "NON_TABULAR", "reason": "Source documentation, preserved without loading rows", "format_family": "documentation",
             "encodings": [], "targets": [], "validator": "raw-byte-sha256-v1", "mirror_of": None, "mirror_evidence_sha256": None},
        ],
    }

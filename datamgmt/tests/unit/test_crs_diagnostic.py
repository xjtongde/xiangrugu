"""Synthetic WKT expectations; no source layouts, coordinates or databases."""
import importlib
import hashlib
import base64

import pytest


LAT_LON = b'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]'
LON_LAT = b'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AXIS["Longitude",EAST],AXIS["Latitude",NORTH]]'
SPHERE = b'GEOGCS["Synthetic sphere",DATUM["Synthetic datum",SPHEROID["Synthetic sphere",6371000,0]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'


def api():
    spec = importlib.util.find_spec("xiangrugu_datamgmt.crs_diagnostic")
    assert spec is not None, "Offline CRS diagnostic API is not implemented"
    return importlib.import_module(spec.name)


def test_diagnostic_retains_original_bytes_and_does_not_assign_srid():
    raw = b'  ' + LAT_LON + b'\r\n'
    result = api().diagnose_wkt(raw)
    assert base64.b64decode(result["raw_base64"]) == raw
    assert result["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["original_wkt"] == raw.decode()
    assert result["srid_assigned"] is None
    assert result["network_enabled"] is False
    assert result["is_geographic"] is True
    assert [a["direction"] for a in result["axes"]] == ["north", "east"]
    assert any(c["authority"] == "EPSG" and c["code"] == "4326"
               for c in result["authority_candidates"])


def test_axis_difference_is_not_silently_treated_as_strict_equivalence():
    result = api().compare_wkt(LAT_LON, LON_LAT)
    assert result["strict_equivalent"] is False
    assert result["equivalent_ignoring_axis_order"] is True
    assert result["classification"] == "axis_order_difference"
    assert result["srid_assigned"] is None


def test_conflicting_declarations_remain_separate():
    result = api().compare_wkt(LAT_LON, SPHERE)
    assert result["classification"] == "conflicting"
    assert result["strict_equivalent"] is False
    assert result["equivalent_ignoring_axis_order"] is False
    assert result["primary"]["original_wkt"] != result["supplemental"]["original_wkt"]


def test_no_authority_match_does_not_invent_an_epsg_or_zero():
    result = api().diagnose_wkt(SPHERE)
    assert result["authority_candidates"] == []
    assert result["srid_assigned"] is None


def test_multiple_best_authorities_are_reported_without_selection():
    result = api().diagnose_wkt(LON_LAT)
    assert result["authority_match_status"] == "multiple_best_candidates"
    assert result["authority_candidates"] == [
        {"authority": "OGC", "code": "CRS84", "confidence": 70},
        {"authority": "IGNF", "code": "WGS84GDD", "confidence": 70},
        {"authority": "IGNF", "code": "WGS84G", "confidence": 70},
        {"authority": "EPSG", "code": "4326", "confidence": 25},
        {"authority": "EPSG", "code": "4978", "confidence": 25},
        {"authority": "EPSG", "code": "4979", "confidence": 25},
    ]
    assert result["srid_assigned"] is None


def test_candidate_budget_rejects_more_than_the_limit():
    with pytest.raises(api().CRSDiagnosticError) as caught:
        api().diagnose_wkt(LON_LAT, limits=api().CRSLimits(max_candidates=5))
    assert caught.value.code == "candidate_limit"


def test_exact_candidate_budget_keeps_every_candidate():
    result = api().diagnose_wkt(LON_LAT, limits=api().CRSLimits(max_candidates=6))
    assert len(result["authority_candidates"]) == 6
    assert result["srid_assigned"] is None


def test_identical_crs_is_reported_without_assigning_srid():
    result = api().compare_wkt(LAT_LON, LAT_LON)
    assert result["classification"] == "equivalent"
    assert result["strict_equivalent"] is True
    assert result["srid_assigned"] is None


@pytest.mark.parametrize("raw,code", [
    (b'', 'empty_wkt'), (b' \n', 'empty_wkt'), (b'\xff', 'invalid_utf8'),
    (b'GEOGCS["x"\x00]', 'nul_byte'), (b'https://example.invalid/crs', 'invalid_wkt'),
    (b'EPSG:4326', 'invalid_wkt'), (b'GEOGCS["x"', 'unbalanced_wkt'),
    (LAT_LON + b' garbage', 'trailing_wkt'),
    (LAT_LON + LAT_LON, 'trailing_wkt'),
    (b'GEOGCS["x")', 'unbalanced_wkt'),
    (b'GEOGCS["unterminated]', 'unbalanced_wkt'),
    (b'GEOGCS["x"]', 'invalid_wkt'),
])
def test_invalid_input_is_rejected_without_echoing_source(raw, code):
    with pytest.raises(api().CRSDiagnosticError) as caught:
        api().diagnose_wkt(raw)
    assert caught.value.code == code
    assert str(caught.value) == code


def test_byte_budget_is_enforced_before_parsing():
    with pytest.raises(api().CRSDiagnosticError) as caught:
        api().diagnose_wkt(LAT_LON, limits=api().CRSLimits(max_bytes=16))
    assert caught.value.code == 'byte_limit'


def test_nesting_budget_is_enforced_before_parsing():
    with pytest.raises(api().CRSDiagnosticError) as caught:
        api().diagnose_wkt(LAT_LON, limits=api().CRSLimits(max_depth=2))
    assert caught.value.code == 'depth_limit'


@pytest.mark.parametrize("name,value", [('max_bytes', 0), ('max_depth', True),
                                       ('max_candidates', -1), ('max_bytes', 1.5)])
def test_invalid_budgets_are_rejected(name, value):
    with pytest.raises(ValueError):
        api().CRSLimits(**{name: value})


def test_exact_budget_boundaries_are_accepted():
    assert api().diagnose_wkt(LAT_LON, limits=api().CRSLimits(
        max_bytes=len(LAT_LON), max_depth=3))["srid_assigned"] is None


def test_network_enabled_context_is_rejected_not_silently_mutated():
    from pyproj import network
    was_enabled = network.is_network_enabled()
    try:
        network.set_network_enabled(True)
        with pytest.raises(api().CRSDiagnosticError) as caught:
            api().diagnose_wkt(LAT_LON)
        assert caught.value.code == 'network_enabled'
        assert network.is_network_enabled() is True
    finally:
        network.set_network_enabled(was_enabled)


def test_runtime_provenance_includes_bundled_database_hash():
    info = api().runtime_provenance()
    assert info["pyproj_version"]
    assert info["proj_version"]
    assert info["epsg_version"]
    assert len(info["proj_db_sha256"]) == 64
    assert info["proj_db_size"] > 0

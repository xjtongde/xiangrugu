"""Bounded offline WKT diagnostics, not SRID decisions or geometry transforms."""
from dataclasses import dataclass
import base64
import hashlib
from pathlib import Path
import re

from pyproj import CRS, database, datadir, network, __version__, proj_version_str
from pyproj.exceptions import CRSError


class CRSDiagnosticError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class CRSLimits:
    max_bytes: int = 65536
    max_depth: int = 64
    max_candidates: int = 32

    def __post_init__(self):
        for value in (self.max_bytes, self.max_depth, self.max_candidates):
            if type(value) is not int or value <= 0:
                raise ValueError("CRS budgets must be positive integers")


def _parse(raw: bytes, limits: CRSLimits) -> tuple[str, CRS]:
    if not isinstance(raw, bytes):
        raise TypeError("WKT input must be original bytes")
    if len(raw) > limits.max_bytes:
        raise CRSDiagnosticError("byte_limit")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError:
        raise CRSDiagnosticError("invalid_utf8") from None
    if not text.strip():
        raise CRSDiagnosticError("empty_wkt")
    if "\x00" in text:
        raise CRSDiagnosticError("nul_byte")
    if not re.match(r"\s*[A-Za-z][A-Za-z0-9_]*\s*[\[(]", text):
        raise CRSDiagnosticError("invalid_wkt")
    # Guard one complete WKT expression and bounded nesting before PROJ's parser.
    stack = []
    quoted = False
    index = 0
    while index < len(text):
        char = text[index]
        if char == '"':
            if quoted and index + 1 < len(text) and text[index + 1] == '"':
                index += 2
                continue
            quoted = not quoted
        elif not quoted:
            if char in "[(":
                stack.append(char)
                if len(stack) > limits.max_depth:
                    raise CRSDiagnosticError("depth_limit")
            elif char in "])":
                if not stack or stack.pop() != ("[" if char == "]" else "("):
                    raise CRSDiagnosticError("unbalanced_wkt")
                if not stack:
                    if text[index + 1:].strip():
                        raise CRSDiagnosticError("trailing_wkt")
                    break
        index += 1
    if quoted or stack:
        raise CRSDiagnosticError("unbalanced_wkt")
    if network.is_network_enabled():
        raise CRSDiagnosticError("network_enabled")
    try:
        return text, CRS.from_wkt(text)
    except CRSError:
        raise CRSDiagnosticError("invalid_wkt") from None


def _describe(raw: bytes, text: str, crs: CRS, limits: CRSLimits) -> dict:
    candidates = crs.list_authority(min_confidence=0)
    if len(candidates) > limits.max_candidates:
        raise CRSDiagnosticError("candidate_limit")
    best_count = sum(c.confidence == max(x.confidence for x in candidates)
                     for c in candidates) if candidates else 0
    return {
        "raw_base64": base64.b64encode(raw).decode("ascii"),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "original_wkt": text,
        "normalized_wkt": crs.to_wkt(),
        "is_geographic": crs.is_geographic,
        "is_projected": crs.is_projected,
        "axes": [{"name": a.name, "abbreviation": a.abbrev,
                  "direction": a.direction, "unit_name": a.unit_name,
                  "unit_conversion_factor": a.unit_conversion_factor}
                 for a in crs.axis_info],
        "authority_candidates": [{"authority": c.auth_name, "code": c.code,
                                  "confidence": c.confidence} for c in candidates],
        "authority_match_status": "none" if not best_count else (
            "single_best_candidate" if best_count == 1 else "multiple_best_candidates"),
        "authority_candidates_are_decisions": False,
        "srid_assigned": None,
        "network_enabled": False,
    }


def diagnose_wkt(raw: bytes, *, limits: CRSLimits = CRSLimits()) -> dict:
    text, crs = _parse(raw, limits)
    return _describe(raw, text, crs, limits)


def compare_wkt(primary: bytes, supplemental: bytes, *, limits: CRSLimits = CRSLimits()) -> dict:
    ptext, pcrs = _parse(primary, limits)
    stext, scrs = _parse(supplemental, limits)
    strict = pcrs.equals(scrs, ignore_axis_order=False)
    ignoring_axes = pcrs.equals(scrs, ignore_axis_order=True)
    return {
        "primary": _describe(primary, ptext, pcrs, limits),
        "supplemental": _describe(supplemental, stext, scrs, limits),
        "strict_equivalent": strict,
        "equivalent_ignoring_axis_order": ignoring_axes,
        "classification": "equivalent" if strict else (
            "axis_order_difference" if ignoring_axes else "conflicting"),
        "srid_assigned": None,
    }


def runtime_provenance() -> dict:
    catalog = Path(datadir.get_data_dir()) / "proj.db"
    digest = hashlib.sha256()
    with catalog.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"pyproj_version": __version__, "proj_version": proj_version_str,
            "epsg_version": database.get_database_metadata("EPSG.VERSION"),
            "epsg_date": database.get_database_metadata("EPSG.DATE"),
            "proj_db_sha256": digest.hexdigest(), "proj_db_size": catalog.stat().st_size,
            "network_enabled": network.is_network_enabled()}

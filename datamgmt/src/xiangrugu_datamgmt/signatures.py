"""Byte signatures are observations, not adapter/disposition decisions."""


def detect_signature(prefix: bytes) -> str:
    if prefix.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "zip"
    if prefix.startswith(b"SQLite format 3\x00"):
        return "sqlite"
    if prefix.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "ole"
    if prefix.startswith((b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")):
        return "tiff"
    if prefix.startswith(b"%PDF-"):
        return "pdf"
    return "unknown"

"""Bound ZIP metadata before ZipFile allocates the whole central directory."""
import struct
import zipfile


class ArchiveLimit(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def preflight_zip(stream, *, remaining_members, max_central_bytes):
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(max(0, size - 65557))
    tail = stream.read(65557)
    offset = tail.rfind(b"PK\x05\x06")
    if offset < 0 or len(tail) - offset < 22:
        raise zipfile.BadZipFile("missing end record")
    _, disk, directory_disk, disk_count, count, central_size, central_offset, comment_size = struct.unpack_from("<4s4H2LH", tail, offset)
    if offset + 22 + comment_size != len(tail):
        raise zipfile.BadZipFile("end record length")
    if disk or directory_disk or disk_count != count:
        raise ArchiveLimit("unsupported_multidisk")
    if count == 65535 or central_size == 0xffffffff or central_offset == 0xffffffff:
        raise ArchiveLimit("unsupported_zip64")
    if count > remaining_members:
        raise ArchiveLimit("count_limit")
    if central_size > max_central_bytes:
        raise ArchiveLimit("central_limit")
    end_position = size - len(tail) + offset
    if central_offset + central_size != end_position:
        raise zipfile.BadZipFile("central directory bounds")
    stream.seek(central_offset)
    end = central_offset + central_size
    actual_count = 0
    while stream.tell() < end:
        header = stream.read(46)
        if len(header) != 46 or header[:4] != b"PK\x01\x02":
            raise zipfile.BadZipFile("central header")
        name_size, extra_size, member_comment_size = struct.unpack_from("<3H", header, 28)
        stream.seek(name_size + extra_size + member_comment_size, 1)
        actual_count += 1
        if actual_count > remaining_members:
            raise ArchiveLimit("count_limit")
    if stream.tell() != end or actual_count != count:
        raise zipfile.BadZipFile("central directory count")
    stream.seek(0)

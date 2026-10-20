import struct

import pytest

from media_tidy.config import Library


def mkv_bytes(width: int, height: int) -> bytes:
    """Smallest header our probe understands: PixelWidth then PixelHeight elements."""
    return b"\x1a\x45\xdf\xa3" + b"\x00" * 16 + b"\xb0\x82" + width.to_bytes(2, "big") + b"\xba\x82" + height.to_bytes(2, "big")


def mp4_bytes(width: int, height: int) -> bytes:
    return b"tkhd" + b"\x00" * 4 + b"\x00" * 20 + b"\x00" * 16 + b"\x00" * 36 + struct.pack(">II", width << 16, height << 16)


def avi_bytes(width: int, height: int) -> bytes:
    return b"RIFF" + b"\x00" * 8 + b"avih" + b"\x00" * 4 + b"\x00" * 32 + struct.pack("<II", width, height)


@pytest.fixture
def lib(tmp_path):
    for d in ("TV", "Movies", "_incoming"):
        (tmp_path / d).mkdir()
    return Library(tmp_path)


def put(path, data=b"x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path

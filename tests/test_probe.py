from conftest import avi_bytes, mkv_bytes, mp4_bytes, put

from media_tidy.probe import height


def test_reads_height_from_each_container(tmp_path):
    assert height(put(tmp_path / "a.mkv", mkv_bytes(1920, 1080))) == 1080
    assert height(put(tmp_path / "b.mp4", mp4_bytes(1280, 720))) == 720
    assert height(put(tmp_path / "c.avi", avi_bytes(640, 480))) == 480


def test_unreadable_is_none(tmp_path):
    assert height(put(tmp_path / "d.mkv", b"not a video")) is None
    assert height(put(tmp_path / "e.wmv", b"x")) is None

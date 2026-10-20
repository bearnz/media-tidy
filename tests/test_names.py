import pytest

from media_tidy.names import clean_title, parse_code, parse_movie, show_key, show_name_from_release


@pytest.mark.parametrize("name, folder, expected", [
    ("Show.S01E02.720p.mkv", None, (1, 2, None)),
    ("friends_s01e01_720p_bluray.mkv", None, (1, 1, None)),
    ("friends.s10e17e18.720p.mkv", None, (10, 17, 18)),
    ("Taskmaster S12E7.mp4", None, (12, 7, None)),
    ("BILLIONS - S03 E01 - Tie Goes To The Runner.mp4", None, (3, 1, None)),
    ("Guy Montgomery's Guy Mont Spelling Bee AU - Series 2 Episode 11.mp4", None, (2, 11, None)),
    ("Bro Town - 101 The Weakest Link [Jackson Clag].avi", 1, (1, 1, None)),
    ("Bro Town - 101 The Weakest Link [Jackson Clag].avi", None, None),
    ("Top Gear S00E153 - East Coast Road Trip.mkv", None, (0, 153, None)),
    ("Dune.Part.Two.2024.1080p.WEBRip.mkv", None, None),
])
def test_parse_code(name, folder, expected):
    got = parse_code(name, folder)
    assert (got[:3] if got else None) == expected


@pytest.mark.parametrize("raw, expected", [
    (".Risk.Management.1080p.10bit.BluRay.AAC5.1.HEVC-Vyndros", "Risk Management"),
    (" - I Love To Squander Promise (1080p ALL4 WEB-DL AAC2.0 H.264)-ASTRD", "I Love To Squander Promise"),
    (".2016.Multi.1080p.Blu-ray", ""),
    (" - Episode 1 (576p DVD x265 Ghost)", ""),
    (" [2008.12.28] (Vietnam Special)", "Vietnam Special"),
    (" - Dave Gorman, Ken Livingstone (Angus Scandal 2002-05-24)", "Dave Gorman, Ken Livingstone (Angus Scandal 2002-05-24)"),
    (" - Flotsam & Jetsam (XL)", "Flotsam & Jetsam (XL)"),       # an already tidy title stays as it is
    (".Traffic.Stops. 1080P. WEBDl", "Traffic Stops"),
    (" - An Evening With Top Gear", "An Evening With Top Gear"),   # a show name inside the title is kept
])
def test_clean_title(raw, expected):
    assert clean_title(raw, show="Top Gear") == expected


def test_clean_title_that_is_only_the_show_name_is_dropped():
    assert clean_title(", Episode 5 _ Full Episode _ Taskmaster-(1080p)", show="Taskmaster") == ""


def test_clean_title_lowercase_release_gets_title_case():
    assert clean_title(".the.system.of.endless.plates.1080p", all_lower=True) == "The System Of Endless Plates"


@pytest.mark.parametrize("name, expected", [
    ("Dune.Part.Two.2024.1080p.WEBRip.1600MB.DD5.1.x264-GalaxyRG[TGx]", ("Dune Part Two", 2024, None)),
    ("The.Martian.2015.EXTENDED.1080p.BluRay.H264.AAC-RARBG", ("The Martian", 2015, "Extended")),
    ("Tenet.2020.IMAX.1080p.BluRay.H264.AAC-RARBG", ("Tenet", 2020, "IMAX")),
    ("Avengers Endgame (2019) [BluRay] [1080p] [YTS.LT]", ("Avengers Endgame", 2019, None)),
    ("2001.A.Space.Odyssey.1968.1080p.BluRay", ("2001 A Space Odyssey", 1968, None)),
    ("Blade.Runner.2049.2017.1080p.mkv", ("Blade Runner 2049", 2017, None)),
    ("Some.Home.Video.mkv", None),
])
def test_parse_movie(name, expected):
    assert parse_movie(name) == expected


def test_show_matching_ignores_case_years_and_leading_the():
    assert show_key("The Flash (TV)") == show_key("the.flash.2014".replace(".", " ")) == "flash"
    assert show_name_from_release("The.Last.Leg.") == "The Last Leg"
    assert show_name_from_release("Lanterns 2026 ") == "Lanterns"

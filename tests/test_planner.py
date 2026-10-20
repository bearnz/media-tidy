from conftest import avi_bytes, mkv_bytes, put

from media_tidy.apply import apply_plan, latest_log, undo
from media_tidy.planner import build_plan, read_plan, write_plan


def moves(plan, root):
    return {(r.action, str(r.src.relative_to(root)), str(r.dst.relative_to(root)) if r.dst else None)
            for r in plan.rows}


def test_movie_release_folder_is_renamed_and_cleaned(lib):
    rel = lib.movies / "Dune.Part.Two.2024.1080p.WEBRip.1600MB.DD5.1.x264-GalaxyRG[TGx]"
    put(rel / "Dune.Part.Two.2024.1080p.WEBRip.1600MB.DD5.1.x264-GalaxyRG.mkv", mkv_bytes(1920, 1080))
    put(rel / "RARBG.txt")
    put(rel / "Subs" / "2_English.srt", b"1\n00:00:01,000 --> 00:00:02,000\nHello\n")
    m = moves(build_plan(lib), lib.root)
    assert ("move", str(rel.relative_to(lib.root) / "Dune.Part.Two.2024.1080p.WEBRip.1600MB.DD5.1.x264-GalaxyRG.mkv"),
            r"Movies\Dune Part Two (2024)\Dune Part Two (2024).mkv") in m
    assert ("move", str((rel / "Subs" / "2_English.srt").relative_to(lib.root)),
            r"Movies\Dune Part Two (2024)\Dune Part Two (2024).en.srt") in m
    assert any(a == "quarantine" and s.endswith("RARBG.txt") for a, s, _ in m)


def test_tidy_library_plans_nothing(lib):
    put(lib.movies / "Chef (2014)" / "Chef (2014).mp4")
    put(lib.tv / "QI" / "Series 6" / "QI S06E03 - Flotsam & Jetsam (XL).mkv")
    put(lib.tv / "Top Gear" / "Specials" / "Top Gear S00E153 - East Coast Road Trip.mkv")
    put(lib.tv / "Top Gear" / "Trailers" / "Series 1 - Series 1 Trailer.mkv")
    assert build_plan(lib).actions == []


def test_incoming_episode_joins_existing_show_with_its_season_word(lib):
    put(lib.tv / "Taskmaster" / "Series 21" / "Taskmaster S21E01 - Cube Is Good.mkv")
    put(lib.incoming / "Taskmaster.S21E02.Leg.Up.Johnny.1080p.ALL4.WEB-DL.AAC2.0.H.264.mkv")
    m = moves(build_plan(lib), lib.root)
    assert ("move", r"_incoming\Taskmaster.S21E02.Leg.Up.Johnny.1080p.ALL4.WEB-DL.AAC2.0.H.264.mkv",
            r"TV\Taskmaster\Series 21\Taskmaster S21E02 - Leg Up Johnny.mkv") in m


def test_incoming_new_show_is_flagged(lib):
    put(lib.incoming / "Pluribus.S01E01.1080p.x265-ELiTE.mkv")
    plan = build_plan(lib)
    row = next(r for r in plan.actions)
    assert str(row.dst.relative_to(lib.root)) == r"TV\Pluribus\Season 1\Pluribus S01E01.mkv"
    assert "new show" in row.note


def test_duplicate_episode_keeps_higher_resolution(lib):
    put(lib.tv / "Show" / "Season 1" / "Show S01E01.avi", avi_bytes(640, 480))
    put(lib.incoming / "Show.S01E01.1080p.WEB.mkv", mkv_bytes(1920, 1080))
    m = moves(build_plan(lib), lib.root)
    assert ("quarantine", r"TV\Show\Season 1\Show S01E01.avi", r"_quarantine\_duplicates\TV\Show\Season 1\Show S01E01.avi") in m
    assert ("move", r"_incoming\Show.S01E01.1080p.WEB.mkv", r"TV\Show\Season 1\Show S01E01.mkv") in m


def test_duplicate_movie_worse_copy_is_quarantined(lib):
    put(lib.movies / "Chef (2014)" / "Chef (2014).mkv", mkv_bytes(1920, 1080))
    put(lib.incoming / "Chef.2014.720p.WEB" / "Chef.2014.720p.WEB.mkv", mkv_bytes(1280, 720))
    plan = build_plan(lib)
    assert [r.action for r in plan.actions] == ["quarantine"]
    assert "_duplicates" in str(plan.actions[0].dst)


def test_no_year_is_left_for_the_user(lib):
    put(lib.incoming / "Some.Home.Video.mkv")
    plan = build_plan(lib)
    assert plan.actions == [] and plan.rows[0].action == "leave"


def test_apply_then_undo_round_trip(lib):
    src = put(lib.movies / "Venom.2018.1080p.BluRay.H264.AAC-RARBG" / "Venom.2018.1080p.BluRay.H264.AAC-RARBG.mp4")
    put(src.parent / "RARBG.txt")
    before = sorted(p.relative_to(lib.root) for p in lib.root.rglob("*"))
    write_plan(build_plan(lib), lib.plan_file)
    log, done, problems = apply_plan(lib, read_plan(lib.plan_file))
    assert problems == [] and done == 2
    assert (lib.movies / "Venom (2018)" / "Venom (2018).mp4").exists()
    assert not src.parent.exists()                        # emptied release folder removed
    undo(lib, latest_log(lib))
    ours = {"_media-tidy", "_quarantine"}      # the tool's own folders may stay behind, empty
    after = sorted(p.relative_to(lib.root) for p in lib.root.rglob("*") if not ours & set(p.parts))
    assert after == [p for p in before if not ours & set(p.parts)]


def test_apply_skips_rather_than_overwrites(lib):
    put(lib.movies / "Venom.2018.1080p" / "Venom.2018.1080p.mp4")
    write_plan(build_plan(lib), lib.plan_file)
    put(lib.movies / "Venom (2018)" / "Venom (2018).mp4", b"already here")
    _, done, problems = apply_plan(lib, read_plan(lib.plan_file))
    assert done == 0 and problems and "target exists" in problems[0]
    assert (lib.movies / "Venom (2018)" / "Venom (2018).mp4").read_bytes() == b"already here"

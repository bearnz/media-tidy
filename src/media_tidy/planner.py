"""Build a dry-run plan: every move needed to bring TV, Movies and the drop folder into shape.

Nothing here touches the disk except reading it. The plan is a CSV the user can check (and edit)
before `apply` runs it.
"""

import csv
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from media_tidy import probe
from media_tidy.config import Library
from media_tidy.names import (EXTRA_DIRS, JUNK_DIRS, JUNK_FILE, MOVIE_NAME, SUBS, VIDEO, clean_title, folder_season,
                              is_ad_sub, movie_target_name, parse_code, parse_movie, show_key, show_name_from_release,
                              sub_lang)


@dataclass
class Row:
    action: str   # "move" | "quarantine" | "leave"
    src: Path
    dst: Path | None
    note: str = ""


@dataclass
class Plan:
    rows: list = field(default_factory=list)

    def move(self, src, dst, note=""):
        self.rows.append(Row("move", Path(src), Path(dst), note))

    def quarantine(self, lib, src, base, note, sub="junk"):
        rel = os.path.relpath(src, base)
        self.rows.append(Row("quarantine", Path(src), lib.quarantine / sub / rel, note))

    def leave(self, src, why):
        self.rows.append(Row("leave", Path(src), None, why))

    @property
    def actions(self):
        return [r for r in self.rows if r.action != "leave"]

    def summary(self) -> Counter:
        return Counter(r.action for r in self.rows)


def _same(a, b) -> bool:
    return os.path.normcase(str(a)) == os.path.normcase(str(b))


def _videos(files):
    return [p for p in files if p.suffix.lower() in VIDEO and not JUNK_FILE.search(p.name)]


# ---------------------------------------------------------------- TV

def _season_word(show_dir: Path) -> str:
    words = Counter()
    if show_dir.is_dir():
        for d in show_dir.iterdir():
            m = re.match(r"(Season|Series) \d", d.name, re.I)
            if d.is_dir() and m:
                words[m[1].title()] += 1
    return words.most_common(1)[0][0] if words else "Season"


def _season_dir(word: str, n: int) -> str:
    return "Specials" if n == 0 else f"{word} {n}"


def _episode_name(show: str, f: Path, fs):
    """-> (season, episode, new file name) or None."""
    code = parse_code(f.name, fs)
    if not code:
        return None
    s, e, e2, end = code
    stem = f.stem
    title = clean_title(stem[end:], show, stem == stem.lower())
    prefix = stem[:end]
    if re.search(r"\bXL\b", prefix) and "XL" not in title:
        title = f"{title} (XL)" if title else "XL"
    elif re.search(r"bit more news", prefix, re.I) and not re.search("bit more", title, re.I):
        title = f"{title} (A Bit More)" if title else "A Bit More"
    epcode = f"S{s:02d}E{e:02d}" + (f"-E{e2:02d}" if e2 else "")
    return s, e, f"{show} {epcode}" + (f" - {title}" if title else "") + f.suffix.lower()


class _TV:
    def __init__(self, lib: Library, plan: Plan):
        self.lib, self.plan = lib, plan
        self.shows = {show_key(d.name): d for d in lib.tv.iterdir() if d.is_dir()} if lib.tv.is_dir() else {}
        self.episodes = defaultdict(list)    # (show dir, season, ep) -> [(src, dst, note)]
        self.subs = []                       # (subtitle, show dir it belongs to)
        self._words = {}

    def season_word(self, show_dir: Path) -> str:
        if show_dir not in self._words:
            self._words[show_dir] = _season_word(show_dir)
        return self._words[show_dir]

    def show_dir_for(self, release_show: str) -> tuple[Path, bool]:
        key = show_key(release_show)
        if key in self.shows:
            return self.shows[key], False
        d = self.lib.tv / release_show
        self.shows[key] = d
        return d, True

    def add_episode(self, src: Path, show_dir: Path, fs=None, new_show=False):
        parsed = _episode_name(show_dir.name, src, fs)
        if not parsed:
            return False
        s, e, name = parsed
        dst = show_dir / _season_dir(self.season_word(show_dir), s) / name
        self.episodes[(str(show_dir).lower(), s, e)].append((src, dst, "new show - check the name" if new_show else ""))
        return True

    def scan_library(self):
        for show_dir in list(self.shows.values()):
            for dp, dns, fns in os.walk(show_dir):
                rel = Path(dp).relative_to(show_dir)
                parts = [p.lower() for p in rel.parts]
                if any(p in EXTRA_DIRS for p in parts) or ("specials" in parts and parts.index("specials") < len(parts) - 1):
                    dns[:] = []        # extras and nested specials stay exactly as they are
                    continue
                fs = folder_season(rel.parts)
                for f in map(lambda n: Path(dp) / n, fns):
                    if JUNK_FILE.search(f.name) or any(p in JUNK_DIRS for p in parts):
                        self.plan.quarantine(self.lib, f, self.lib.root, "junk")
                    elif f.suffix.lower() in VIDEO:
                        if not self.add_episode(f, show_dir, fs) and fs is None:
                            self.plan.leave(f, "no episode code")
                    elif f.suffix.lower() in SUBS:
                        self.subs.append((f, show_dir))

    def add_incoming(self, f: Path) -> Path:
        """Episode from the drop folder: find (or start) its show folder. Returns the show folder."""
        cut = re.search(r"(?<![A-Za-z0-9])S\d{1,2} ?E\d|Series \d", f.stem, re.I)
        show_dir, new = self.show_dir_for(show_name_from_release(f.stem[:cut.start()]))
        self.add_episode(f, show_dir, new_show=new)
        return show_dir

    def resolve(self):
        """Duplicates (same show/season/episode): keep the highest resolution, newest on a tie."""
        stems = {}
        for key, items in self.episodes.items():
            if len(items) > 1:
                ranked = sorted(items, key=lambda it: (probe.height(it[0]) or 0, it[0].stat().st_mtime), reverse=True)
                best_h = probe.height(ranked[0][0]) or 0
                for src, dst, _ in ranked[1:]:
                    h = probe.height(src) or 0
                    why = f"duplicate: {h or 'unreadable'}p vs kept {best_h}p" if h != best_h else f"duplicate: same {h}p, older"
                    self.plan.quarantine(self.lib, src, self.lib.root, why, sub="_duplicates")
                items = ranked[:1]
            src, dst, note = items[0]
            stems[key] = dst.with_suffix("")
            if not _same(src, dst) or src.name != dst.name:
                self.plan.move(src, dst, note)
        # Subtitles follow the episode they belong to.
        counts = Counter()
        for f, show_dir in self.subs:
            # Scene-style "Subs/<release name>/2_English.srt" carries the code in a parent folder name.
            code = parse_code(f.name) or next((parse_code(p.name) for p in f.parents if parse_code(p.name)), None)
            base = stems.get((str(show_dir).lower(), code[0], code[1])) if code and show_dir else None
            if base is None or f.suffix == "" or is_ad_sub(f):
                self.plan.leave(f, "subtitle with no matching episode")
                continue
            if f.suffix.lower() == ".srt":
                if f.name.startswith(base.name + "."):
                    continue          # already named for its episode
                lang = sub_lang(f, f.name)
                counts[(base, lang)] += 1
                n = counts[(base, lang)]
                dst = Path(f"{base}.{lang}.srt" if n == 1 else f"{base}.{lang}.{n}.srt")
            else:
                dst = base.with_suffix(f.suffix.lower())
            if not _same(f, dst):
                self.plan.move(f, dst, "subtitle")


# ---------------------------------------------------------------- Movies

def _movie_folder_ok(d: Path) -> bool:
    if not MOVIE_NAME.match(d.name):
        return False
    return all(p.is_file() and p.name.startswith(d.name + ".") for p in d.iterdir())


def plan_movie(lib: Library, plan: Plan, item: Path, base: Path):
    """Sort one movie (a folder or a loose file) into Movies/Title (Year)/Title (Year).ext."""
    files = [Path(dp) / n for dp, _, fns in os.walk(item) for n in fns] if item.is_dir() else [item]
    vids = _videos(files)
    if not vids:
        for f in files:
            plan.leave(f, "no video found")
        return
    main = max(vids, key=lambda p: p.stat().st_size)
    if item.is_dir() and MOVIE_NAME.match(item.name):
        name = item.name
    else:
        parsed = parse_movie(item.name) or parse_movie(main.name)
        if not parsed:
            plan.leave(item, "can't find a title and year - rename it, or edit the plan")
            return
        name = movie_target_name(*parsed)
    dst_dir = lib.movies / name
    existing = _videos(list(dst_dir.iterdir())) if dst_dir.is_dir() and not _same(dst_dir, item) else []
    if existing:   # already in the library: keep the better copy (resolution, then newest)
        old = existing[0]
        rank = lambda p: (probe.height(p) or 0, p.stat().st_mtime)
        if rank(main) <= rank(old):
            for f in files:
                plan.quarantine(lib, f, base, f"duplicate of {name} (library copy is as good or better)", sub="_duplicates")
            return
        plan.quarantine(lib, old, base, f"duplicate of {name} (replaced by a better copy)", sub="_duplicates")
    counts = Counter()
    for f in sorted(files, key=lambda p: int((re.match(r"(\d+)_", p.name) or [0, "0"])[1])):
        ext = f.suffix.lower()
        if f == main:
            dst = dst_dir / f"{name}{ext}"
        elif f in vids:
            plan.quarantine(lib, f, base, "extra video (sample?) - check")
            continue
        elif JUNK_FILE.search(f.name) or ext in {".txt", ".nfo", ".jpg", ".png"} or (ext == ".srt" and is_ad_sub(f)):
            plan.quarantine(lib, f, base, "junk")
            continue
        elif ext == ".srt":
            lang = sub_lang(f, f.name)
            counts[lang] += 1
            dst = dst_dir / (f"{name}.{lang}.srt" if counts[lang] == 1 else f"{name}.{lang}.{counts[lang]}.srt")
        elif ext in (".idx", ".sub"):
            dst = dst_dir / f"{name}{ext}"
        else:
            plan.leave(f, "unrecognised file")
            continue
        if not (_same(f, dst) and f.name == dst.name):
            plan.move(f, dst, "movie" if f == main else "subtitle")


# ---------------------------------------------------------------- whole plan

def build_plan(lib: Library) -> Plan:
    plan = Plan()
    tv = _TV(lib, plan)
    tv.scan_library()
    if lib.movies.is_dir():
        for item in sorted(lib.movies.iterdir()):
            if not (item.is_dir() and _movie_folder_ok(item)):
                plan_movie(lib, plan, item, lib.root)
    if lib.incoming.is_dir():
        for item in sorted(lib.incoming.iterdir()):
            files = [Path(dp) / n for dp, _, fns in os.walk(item) for n in fns] if item.is_dir() else [item]
            episodes = [f for f in _videos(files) if parse_code(f.name)]
            if episodes:
                show_dirs = {tv.add_incoming(f) for f in episodes}
                for f in files:
                    if f not in episodes:
                        if f.suffix.lower() in SUBS and len(show_dirs) == 1 and not is_ad_sub(f):
                            tv.subs.append((f, next(iter(show_dirs))))
                        elif f.suffix.lower() in VIDEO:
                            plan.leave(f, "video with no episode code")
                        else:
                            plan.quarantine(lib, f, lib.root, "junk")
            else:
                plan_movie(lib, plan, item, lib.root)
    tv.resolve()
    _check_collisions(plan)
    return plan


def _check_collisions(plan: Plan):
    seen = defaultdict(list)
    for r in plan.actions:
        seen[str(r.dst).lower()].append(r)
    moving_out = {str(r.src).lower() for r in plan.actions}
    for r in list(plan.actions):
        clash = len(seen[str(r.dst).lower()]) > 1
        occupied = r.dst.exists() and not _same(r.src, r.dst) and str(r.dst).lower() not in moving_out
        if clash or occupied:
            r.action, r.note = "leave", f"would overwrite {r.dst}" if occupied else f"two files want {r.dst}"
            r.dst = None


# ---------------------------------------------------------------- plan file

def write_plan(plan: Plan, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["action", "from", "to", "note"])
        for r in plan.rows:
            w.writerow([r.action, str(r.src), str(r.dst) if r.dst else "", r.note])


def read_plan(path: Path) -> list[Row]:
    with open(path, encoding="utf-8-sig") as fh:
        return [Row(r["action"], Path(r["from"]), Path(r["to"]) if r["to"] else None, r["note"])
                for r in csv.DictReader(fh)]

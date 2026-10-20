"""Parsing release-style file names and building tidy ones."""

import os
import re

VIDEO = {".mkv", ".mp4", ".avi", ".wmv", ".m4v"}
SUBS = {".srt", ".idx", ".sub"}
# Plex's extras folder names (show level, or inside a season), plus our own catch-alls.
EXTRA_DIRS = {"behind the scenes", "deleted scenes", "featurettes", "interviews", "scenes",
              "shorts", "trailers", "other", "extras"}
JUNK_DIRS = {"screens", "sample"}
JUNK_FILE = re.compile(r"(^rarbg(\.com)?\.(txt|mp4)$|downloaded from|torrent downloaded|upcoming releases"
                       r"|^screen(shot)?-?\d+|\.screen\d+\.png$|\.nfo$|^\.ds_store$|^sample\.|^www\.|ahashare"
                       r"|^sujaidr\.txt$|psarips|hon3yhd|yify-torrents)", re.I)

CODE = re.compile(r"(?<![A-Za-z0-9])S(\d{1,2}) ?E(\d{1,3})(?:-?E(\d{1,3}))?(?![0-9])", re.I)
SERIES_EP = re.compile(r"Series (\d{1,2}),? Episode (\d{1,3})", re.I)
TECH = re.compile(r"^(\d{3,4}[pi]|web|webrip|web-?dl|webdl|hdtv|sdtv|pdtv|bluray|blu-ray|brrip|bdrip|dvdrip|dvd"
                  r"|hdrip|uhd|hdr|hdr10|dv|x26[45]|h26[45]|hevc|avc|xvid|divx|amzn|dsnp|hmax|hulu|all4|10bit"
                  r"|aac[\d.]*|ddp?[\d.+]*|eac3|ac3|dts|truehd|atmos|6ch|reencode|youtube|multi|\d+mb)$", re.I)
TECH_CAPS = {"MAX", "NF", "HD", "SD", "MULTI", "PROPER", "REPACK", "INTERNAL", "iNTERNAL", "LIMITED", "REMASTERED"}
EDITIONS = {"extended": "Extended", "theatrical": "Theatrical", "imax": "IMAX", "unrated": "Unrated",
            "directors": "Director's Cut", "director's": "Director's Cut", "final cut": "Final Cut"}
RELEASE_WORDS = {"extended", "theatrical", "imax", "unrated", "directors", "remastered", "proper", "repack",
                 "limited", "hc", "multi", "complete"}
BAD_CHARS = re.compile(r'[<>"/\\|?*]')
YEAR = re.compile(r"^(19[2-9]\d|20[0-4]\d)$")


def safe(name: str) -> str:
    """Make a string legal as a Windows file name."""
    name = name.replace(":", " -")
    name = BAD_CHARS.sub("", name)
    return re.sub(r"\s+", " ", name).strip(" .")


def parse_code(name: str, folder_season: int | None = None):
    """-> (season, episode, last_episode_or_None, end_index) or None."""
    m = CODE.search(name)
    if m:
        return int(m[1]), int(m[2]), int(m[3]) if m[3] else None, m.end()
    m = SERIES_EP.search(name)
    if m:
        return int(m[1]), int(m[2]), None, m.end()
    m = re.search(r"- ([1-9])(\d{2}) ", name)          # "- 101 Title", only when it agrees with the folder
    if m and folder_season == int(m[1]):
        return int(m[1]), int(m[2]), None, m.end()
    return None


def folder_season(parts) -> int | None:
    for p in reversed(list(parts)):
        m = re.fullmatch(r"(?:Season|Series|S)\s?(\d{1,4})(?: \(.*\))?", p, re.I)
        if m:
            return int(m[1])
        if p.lower() == "specials":
            return 0
    return None


def is_tech(tok: str, first: bool = False) -> bool:
    t = tok.strip("()[]-_,.")
    if t in TECH_CAPS or (first and YEAR.match(t)):
        return True
    return any(TECH.match(p.strip("()[]_,.")) for p in t.split("-") if p.strip("()[]_,."))


def clean_title(raw: str, show: str = "", all_lower: bool = False) -> str:
    """Episode title from whatever follows the episode code; drops release junk."""
    s = re.sub(r"\[[^\]]*\]", " ", raw)
    s = re.sub(r"(?<=[A-Za-z])_(?=(s|t|ve|ll|re|d|m)\b)", "'", s)   # There_s -> There's
    s = s.replace("_", " ")
    if " " not in s.strip(" .-"):
        s = s.replace(".", " ")
    s = re.sub(r"(?<=[A-Za-z0-9]{2})\.(?=[A-Za-z0-9]{2})", " ", s)   # 'Traffic.Stops' but not 'F.I.P'
    out = []
    for tok in s.split():
        if is_tech(tok, first=not out):
            break
        out.append(tok)
    t = " ".join(out).strip(" -.,")
    t = re.sub(r"\bFull Episode\b", "", t, flags=re.I).strip(" -.,")
    if show and t.lower() == show.lower():     # 'Series 12, Episode 5 _ Taskmaster' has no real title
        t = ""
    if re.fullmatch(r"\(([^()]*)\)", t):
        t = t[1:-1]
    if re.fullmatch(r"(episode|ep)\s*\d+", t, re.I):
        t = ""
    if t and all_lower:
        t = re.sub(r"\b([a-z])", lambda m: m[1].upper(), t)
        t = re.sub(r"'S\b", "'s", t)
    return safe(t)


def show_key(name: str) -> str:
    """Loose key for matching a release's show name to an existing show folder."""
    n = re.sub(r"\([^)]*\)", " ", name.lower())
    n = re.sub(r"\b(19|20)\d\d\b", " ", n)
    n = re.sub(r"[^a-z0-9]+", " ", n).strip()
    return re.sub(r"^the ", "", n)


def show_name_from_release(prefix: str) -> str:
    """'The.Last.Leg.' -> 'The Last Leg'; drops a trailing year and separators."""
    s = prefix.replace("_", " ")
    if " " not in s.strip(" .-"):
        s = s.replace(".", " ")
    s = re.sub(r"\[[^\]]*\]", " ", s)
    s = re.sub(r"[\s\-.]+$", "", s)
    s = re.sub(r"\s+(19|20)\d\d$", "", s.strip())
    s = re.sub(r"\s+-\s*$", "", s)
    if s == s.lower():
        s = s.title()
    return safe(s)


def parse_movie(name: str):
    """Release-style movie name -> (title, year, edition or None), or None if there is no year.

    The year is the last year-like token that is followed by release junk or the end, so
    '2001.A.Space.Odyssey.1968.1080p' gives ('2001 A Space Odyssey', 1968).
    """
    s = re.sub(r"\.(mkv|mp4|avi|m4v|wmv)$", "", name, flags=re.I)
    s = re.sub(r"[\[\]()]", " ", s)
    toks = [t for t in re.split(r"[\s._]+", s) if t]
    years = [i for i, t in enumerate(toks) if i > 0 and YEAR.match(t)]
    if not years:
        return None
    marker = lambda i: i == len(toks) - 1 or is_tech(toks[i + 1]) or toks[i + 1].lower() in RELEASE_WORDS
    year_i = next((i for i in years if marker(i)), years[-1])
    title = " ".join(toks[:year_i]).strip(" -")
    rest = " ".join(toks[year_i + 1:]).lower()
    edition = None
    for key, label in EDITIONS.items():
        if re.search(r"\b" + re.escape(key) + r"\b", rest):
            edition = label
            break
    if title == title.lower() or title == title.upper():
        title = title.title()
    return safe(title), int(toks[year_i]), edition


MOVIE_NAME = re.compile(r"^.+ \((19|20)\d\d\)( \{[a-z]+-[^}]+\})*$")


def movie_target_name(title: str, year: int, edition: str | None = None) -> str:
    return f"{title} ({year})" + (f" {{edition-{edition}}}" if edition else "")


LANG = {"english": "en", "eng": "en", "spanish": "es", "spa": "es", "french": "fr", "fre": "fr", "fra": "fr",
        "german": "de", "ger": "de", "deu": "de", "italian": "it", "ita": "it", "portuguese": "pt", "dutch": "nl",
        "danish": "da", "swedish": "sv", "norwegian": "nb", "nor": "nb", "bokmal": "nb", "finnish": "fi",
        "polish": "pl", "chinese": "zh", "japanese": "ja", "korean": "ko", "arabic": "ar", "hebrew": "he",
        "greek": "el", "turkish": "tr", "russian": "ru", "czech": "cs", "hungarian": "hu", "romanian": "ro",
        "thai": "th", "vietnamese": "vi", "indonesian": "id", "malay": "ms", "ukrainian": "uk",
        "bulgarian": "bg", "croatian": "hr", "icelandic": "is", "ice": "is"}


def _read_text(path, limit=None) -> str:
    with open(path, "rb") as f:
        return f.read(limit if limit else -1).decode("utf-8", "ignore")


def is_ad_sub(path) -> bool:
    return os.path.getsize(path) < 1024 and bool(re.search(r"torrent|proxy|yts|yify", _read_text(path), re.I))


def sub_lang(path, name: str) -> str:
    """Language code for a subtitle, plus '.forced' for a short track that starts late (foreign-dialogue subs)."""
    text = _read_text(path)
    m = re.match(r"(?:\d+_)?([A-Za-z]+)\.srt$", name)
    if m and m[1].lower() in LANG:
        lang = LANG[m[1].lower()]
    else:
        m = re.search(r"\.([a-z]{2,3})(?:\.forced)?\.srt$", name, re.I)
        if m and m[1].lower() in set(LANG.values()):
            lang = m[1].lower()
        else:
            lang = "en" if len(re.findall(r"\b(the|you|and|what)\b", text.lower())) > 40 else "und"
    starts = [int(h) * 60 + int(mi) for h, mi in re.findall(r"(\d\d):(\d\d):\d\d,\d+ -->", text)]
    if starts and len(starts) < 100 and min(starts) >= 10:
        lang += ".forced"
    return lang

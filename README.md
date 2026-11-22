# media-tidy

Tidies Plex media under N:\.plex into TV/Movies naming conventions, with dry-run plans, quarantine and undo.

## What it does

`media-tidy plan` looks at three places under the library root (default `N:\.plex`):

- **`_incoming\`**: a drop folder for new downloads. Anything with an episode code (`S01E02`, `Series 2 Episode 3`) goes to TV; anything else with a year goes to Movies.
- **`TV\`**: existing shows. Episodes are renamed to `Show\Season N\Show S01E02 - Title.ext` (keeping the show's own "Season"/"Series" word; season 0 lives in `Specials`). Extras folders (`Trailers`, `Deleted Scenes`, `Behind The Scenes`, `Featurettes`, `Interviews`, `Scenes`, `Shorts`, `Other`, `Extras`) and anything nested under `Specials` are left alone.
- **`Movies\`**: any folder that isn't already `Title (Year)` with matching file names becomes `Title (Year)\Title (Year).ext`. `EXTENDED`/`THEATRICAL`/`IMAX`/`UNRATED`/`Director's Cut` in the release name becomes a Plex `{edition-...}` tag.

Along the way:

- Subtitles move next to their video as `.en.srt` (`.en.2.srt` for extra tracks, `.en.forced.srt` for short partial tracks).
- Release junk (`RARBG.txt`, screenshots, `.nfo`, samples, advert subtitles) goes to `_quarantine\junk\`.
- Duplicates keep the higher resolution (read from the file header), or the newer file on a tie; the loser goes to `_quarantine\_duplicates\`.
- Nothing is ever deleted, and nothing overwrites an existing file.

Names come from the file names alone: there is no online lookup. Check the plan before applying, especially rows marked `new show`, and edit the `to` column of the CSV to fix any name (e.g. `Dune - Part Two (2024)` to match TMDB's punctuation).

## Running

```
uv run media-tidy plan            # dry run: writes N:\.plex\_media-tidy\plan.csv, changes nothing
uv run media-tidy apply           # carries out plan.csv, logging every move
uv run media-tidy undo            # reverses the latest apply
uv run media-tidy --root D:\media plan   # a different library root
```

Undo logs are `N:\.plex\_media-tidy\moves-<timestamp>.jsonl`.

Before moving or re-pathing a lot of media, turn off Plex's "Empty trash automatically after every scan", scan, check nothing is unavailable, then empty trash and turn it back on, so watch history follows the files.

## Testing

```
uv run pytest
```

## Copyright

Copyright (c) 2026 Josh (github.com/bearnz). All rights reserved.

No licence is granted. You are welcome to read this code and to fork it on
GitHub; you may not use, copy, modify or redistribute it without permission.
See [NOTICE](NOTICE) for the terms, and open an issue if you would like to use
any of it.

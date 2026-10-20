# media-tidy

Tidies Plex media under N:\.plex into TV/Movies naming conventions, with dry-run plans, quarantine and undo.

## Running

`uv run media-tidy plan` (dry run, writes N:\.plex\_media-tidy\plan.csv), then `uv run media-tidy apply`;
`uv run media-tidy undo` reverses the latest apply. Never run `apply` on Josh's library without his yes
for that plan.

## Testing

`uv run pytest`. A dry run against the real library is also a regression check: a tidy library should
plan zero moves, so any unexpected row means a parsing change broke an existing name.

## Layout

`src/media_tidy/`: `names.py` (parsing and naming rules), `planner.py` (builds the plan), `apply.py`
(moves, undo log, undo), `probe.py` (resolution from mkv/mp4/avi headers), `cli.py`.
Stdlib only at runtime; pytest is the only dev dependency.

## Notes

Conventions are in ~/.claude/CLAUDE.md (feature branches -> PR -> main,
push only on approval, provenance labels).

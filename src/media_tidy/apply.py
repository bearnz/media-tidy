"""Carry out a plan (renames only, never deletes) and undo it."""

import json
import os
import time
from pathlib import Path

from media_tidy.config import Library
from media_tidy.planner import Row


def _same(a, b) -> bool:
    return os.path.normcase(str(a)) == os.path.normcase(str(b))


def _prune(dirs, stop):
    """Remove folders a run emptied, walking up until something is still in use."""
    stop = {os.path.normcase(str(s)) for s in stop}
    for d in sorted({Path(x) for x in dirs}, key=lambda p: len(p.parts), reverse=True):
        while d.is_dir() and os.path.normcase(str(d)) not in stop and not any(d.iterdir()):
            d.rmdir()
            d = d.parent


def apply_plan(lib: Library, rows: list[Row]) -> tuple[Path, int, list[str]]:
    """-> (log file, moves done, problems). Every move is logged before the next one starts."""
    lib.state.mkdir(parents=True, exist_ok=True)
    log_path = lib.state / f"moves-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
    done, problems, emptied = 0, [], []
    with open(log_path, "w", encoding="utf-8") as log:
        for r in rows:
            if r.action not in ("move", "quarantine") or r.dst is None:
                continue
            if not r.src.exists():
                problems.append(f"missing, skipped: {r.src}")
                continue
            if r.dst.exists() and not _same(r.src, r.dst):
                problems.append(f"target exists, skipped: {r.dst}")
                continue
            r.dst.parent.mkdir(parents=True, exist_ok=True)
            os.rename(r.src, r.dst)
            log.write(json.dumps([str(r.src), str(r.dst)]) + "\n")
            log.flush()
            emptied.append(r.src.parent)
            done += 1
    _prune(emptied, [lib.root, lib.tv, lib.movies, lib.incoming])
    return log_path, done, problems


def latest_log(lib: Library) -> Path | None:
    logs = sorted(lib.state.glob("moves-*.jsonl")) if lib.state.is_dir() else []
    return logs[-1] if logs else None


def undo(lib: Library, log_path: Path) -> tuple[int, list[str]]:
    with open(log_path, encoding="utf-8") as fh:
        moves = [json.loads(line) for line in fh if line.strip()]
    done, problems, emptied = 0, [], []
    for src, dst in reversed(moves):
        src, dst = Path(src), Path(dst)
        if not dst.exists() or (src.exists() and not _same(src, dst)):
            problems.append(f"can't put back: {dst} -> {src}")
            continue
        src.parent.mkdir(parents=True, exist_ok=True)
        os.rename(dst, src)
        emptied.append(dst.parent)
        done += 1
    _prune(emptied, [lib.root, lib.tv, lib.movies, lib.incoming, lib.quarantine])
    log_path.rename(log_path.with_name(log_path.name + ".undone"))
    return done, problems

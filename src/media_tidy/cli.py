"""media-tidy plan | apply | undo"""

import argparse
import sys
from pathlib import Path

from media_tidy.apply import apply_plan, latest_log, undo
from media_tidy.config import DEFAULT_ROOT, Library
from media_tidy.planner import build_plan, read_plan, write_plan


def _show(rows, root: Path, limit: int):
    rel = lambda p: str(p.relative_to(root)) if p and root in p.parents else str(p)
    for r in rows[:limit]:
        print(f"  [{r.action}] {rel(r.src)}" + (f"\n      -> {rel(r.dst)}" if r.dst else "") + (f"   ({r.note})" if r.note else ""))
    if len(rows) > limit:
        print(f"  ... and {len(rows) - limit} more (see the plan file)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="media-tidy", description=__doc__)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT, help=f"library root (default {DEFAULT_ROOT})")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="dry run: write the plan file, change nothing")
    p.add_argument("--show", type=int, default=40, help="how many rows to print")
    sub.add_parser("apply", help="carry out the plan file").add_argument("--plan", type=Path)
    sub.add_parser("undo", help="reverse the latest apply").add_argument("--log", type=Path)
    a = ap.parse_args(argv)
    lib = Library(a.root)

    if a.cmd == "plan":
        plan = build_plan(lib)
        write_plan(plan, lib.plan_file)
        c = plan.summary()
        print(f"moves: {c['move']}  quarantine: {c['quarantine']}  left for you: {c['leave']}")
        _show(plan.rows, lib.root, a.show)
        print(f"plan written to {lib.plan_file} - check it (you can edit the 'to' column), then run `media-tidy apply`")
        return 0

    if a.cmd == "apply":
        path = a.plan or lib.plan_file
        if not path.exists():
            print(f"no plan at {path}; run `media-tidy plan` first", file=sys.stderr)
            return 1
        log, done, problems = apply_plan(lib, read_plan(path))
        for msg in problems:
            print("  " + msg)
        print(f"moved {done} files; undo log {log}")
        return 1 if problems else 0

    if a.cmd == "undo":
        log = a.log or latest_log(lib)
        if not log:
            print("nothing to undo", file=sys.stderr)
            return 1
        done, problems = undo(lib, log)
        for msg in problems:
            print("  " + msg)
        print(f"put back {done} files from {log.name}")
        return 1 if problems else 0
    return 2

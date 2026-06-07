#!/usr/bin/env python3
"""Opt-in, read-only memory-health nudge — for a Claude Code SessionStart hook.

It NEVER edits anything. It runs the curator's read-only analysis over a memory dir
and, only when health is below a threshold, prints a one-line nudge so the agent (and
you) notice rot early and can choose to run `memory-doctor lint --fix` / a v0.2 curate.

Why a hook at all: a probabilistic reader won't keep memory tidy on its own; a machine
should watch it. Why read-only: auto-editing memory is the #1 trust risk (see SPEC D2).

Wire it up (opt-in) in ~/.claude/settings.json:

    {
      "hooks": {
        "SessionStart": [
          { "hooks": [ { "type": "command",
              "command": "python3 /path/to/memory-doctor/hooks/health_nudge.py --dir ~/.claude/.../memory" } ] }
        ]
      }
    }

Exit code is always 0 (a nudge must never block a session).
"""

from __future__ import annotations

import argparse
import os
import sys

# Make the bundled/sibling package importable whether run from repo or installed skill.
_HERE = os.path.dirname(os.path.abspath(__file__))
for cand in (os.path.join(_HERE, "..", "src"), os.path.join(_HERE, "..", "skill", "scripts")):
    if os.path.isdir(os.path.join(cand, "memory_doctor")):
        sys.path.insert(0, os.path.abspath(cand))
        break

try:
    from memory_doctor.adapters import detect_format, get_adapter
    from memory_doctor.report import analyze
except Exception:
    sys.exit(0)  # never break a session because the nudge couldn't load

FRESH_FLOOR = 70  # nudge when freshness drops below this


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", required=True)
    p.add_argument("--floor", type=int, default=FRESH_FLOOR)
    args = p.parse_args()

    root = os.path.abspath(os.path.expanduser(args.dir))
    if not os.path.isdir(root):
        sys.exit(0)
    try:
        store = get_adapter(detect_format(root)).load(root)
        rep = analyze(store)
    except Exception:
        sys.exit(0)

    issues = []
    if rep.freshness < args.floor:
        issues.append(f"freshness {rep.freshness}/100")
    if rep.fixable_index_issues:
        issues.append(f"{rep.fixable_index_issues} index issue(s) (auto-fixable)")
    if rep.dead_links:
        issues.append(f"{len(rep.dead_links)} dead link(s)")
    if rep.asymmetric_links:
        issues.append(f"{len(rep.asymmetric_links)} asymmetric supersede link(s)")
    if len(rep.dup_candidates) >= 2:
        issues.append(f"{len(rep.dup_candidates)} duplicate candidate(s)")

    if issues:
        print(f"🧠 memory-doctor: {store.fmt} store health — " + "; ".join(issues)
              + ". Run `memory-doctor report --dir <dir>` for details.", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()

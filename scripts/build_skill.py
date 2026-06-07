#!/usr/bin/env python3
"""Sync the package into the publishable skill so the skill is self-contained.

Single source of truth is src/memory_curator/. The skill bundle (skill/scripts/) is
generated — do not edit it by hand. Run this after changing src/, then commit.
"""

import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "memory_curator")
DEST = os.path.join(ROOT, "skill", "scripts", "memory_curator")
ENTRY = os.path.join(ROOT, "skill", "scripts", "curate.py")

ENTRY_SRC = '''#!/usr/bin/env python3
"""Self-contained entrypoint for the bundled memory-curator skill.

    python scripts/curate.py report --dir <memory-dir>
    python scripts/curate.py lint   --dir <memory-dir> [--fix]
    python scripts/curate.py undo   --dir <memory-dir>
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memory_curator.cli import main

if __name__ == "__main__":
    main()
'''


def main():
    if os.path.isdir(DEST):
        shutil.rmtree(DEST)
    shutil.copytree(SRC, DEST, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    os.makedirs(os.path.dirname(ENTRY), exist_ok=True)
    with open(ENTRY, "w", encoding="utf-8") as f:
        f.write(ENTRY_SRC)
    print(f"bundled {SRC} -> {DEST}")
    print(f"wrote   {ENTRY}")


if __name__ == "__main__":
    main()

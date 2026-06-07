# memory-doctor

**A maintenance layer for LLM-agent long-term memory — the cure for context rot.**

Memory skills *write* memory. Almost none *keep it healthy*. Over time an agent's memory
store grows long, contradicts itself, sprouts dead links, and the index drifts out of sync —
the agent then burns tokens parsing stale history instead of acting. That's context rot.

`memory-doctor` doesn't produce memory. It keeps an existing store healthy: a read-only
**health report**, plus deterministic, reversible **repairs**.

> Positioning: *producers write, memory-doctor keeps it alive.* It complements memory skills,
> it doesn't compete with them.

## Status — v0.1

Zero dependencies, zero LLM, fully reversible. Two formats, auto-detected:

- **Claude Code auto-memory** — frontmatter + `[[wiki-links]]` + `MEMORY.md` index.
- **[mneme](https://github.com/casperkwok/mneme)** — `.mneme` cells with lifecycle
  (`state`/`conf`/`seen`) and typed `link`s; the spine is derived, so freshness uses `seen`,
  history cells (superseded/retired) are excluded from active health, and supersede back-link
  symmetry is checked.

Commands:

- `report` — read-only health card: dead links, stale notes, oversized files, lexical
  **duplicate candidates**, freshness score, plus per-format checks (auto-memory: index drift,
  orphans; mneme: history, supersede link symmetry).
- `lint --fix` — deterministic, safe repair: reconciles the `MEMORY.md` index (adds missing
  entries, drops dangling ones) while preserving your hand-written hooks. Snapshots first.
  (mneme's spine is derived, so there is no index to reconcile — use `report`.)
- `undo` — restore the last snapshot.

Semantic operations that need a model — true duplicate **merge**, contradiction **reconcile**,
oversized **compaction** — are *detected and flagged* in v0.1 and *resolved* in v0.2 (LLM-based,
no embeddings; manual-apply, snapshot-backed).

## Usage

```bash
# read-only — safe to run anytime
python -m memory_doctor report --dir ~/.claude/.../memory

# preview the index fix, then apply (a snapshot is taken first)
python -m memory_doctor lint --dir ~/.claude/.../memory
python -m memory_doctor lint --dir ~/.claude/.../memory --fix

# revert
python -m memory_doctor undo --dir ~/.claude/.../memory
```

Requires Python ≥ 3.9. No third-party packages.

## Safety

Every write snapshots the whole directory to `.memory-doctor/snapshots/<ts>/` first and logs to
`.memory-doctor/changelog.md`; `undo` restores it. v0.1 only ever performs deterministic index
reconciliation — no content is rewritten.

## License

Apache-2.0 © 2026 Casper Kwok

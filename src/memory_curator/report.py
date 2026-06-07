"""Read-only health detection over a MemoryStore.

Everything here is deterministic and LLM-free (v0.1). Semantic problems that genuinely
need a model (true dedup merge, contradiction reconcile) are *flagged* as candidates,
never resolved — resolution is v0.2.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from .model import MemoryStore, MemUnit

OVERSIZE_CHARS = 1800
DUP_JACCARD = 0.50
# freshness half-life (days) by type: references/prefs age slowly, projects fast
HALFLIFE_DAYS = {"reference": 180, "user": 180, "feedback": 90, "project": 30, "unknown": 60}
STALE_DAYS = 30

_ASCII_WORD = re.compile(r"[a-z0-9_]{3,}")
_CJK = re.compile(r"[一-鿿]")


def _tokens(text: str) -> set:
    """Stdlib-only tokens that work for mixed CN/EN: ascii words (len>=3) plus CJK
    character bigrams. Good enough to surface lexical near-duplicates without jieba."""
    t = text.lower()
    toks = set(_ASCII_WORD.findall(t))
    cjk = _CJK.findall(t)
    toks.update(cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1))
    return toks


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class HealthReport:
    store: MemoryStore
    total_units: int = 0
    total_bytes: int = 0
    missing_from_index: list = field(default_factory=list)   # unit ids absent from index
    dangling_index: list = field(default_factory=list)       # index entries -> no file
    dead_links: list = field(default_factory=list)           # (unit_id, broken_target)
    orphans: list = field(default_factory=list)              # unit ids, no inbound + unindexed
    stale: list = field(default_factory=list)                # (unit_id, age_days)
    oversized: list = field(default_factory=list)            # (unit_id, chars)
    dup_candidates: list = field(default_factory=list)       # (id_a, id_b, score)
    freshness: int = 0

    @property
    def fixable_index_issues(self) -> int:
        return len(self.missing_from_index) + len(self.dangling_index)


def analyze(store: MemoryStore) -> HealthReport:
    rep = HealthReport(store=store)
    units = store.units
    rep.total_units = len(units)
    rep.total_bytes = sum(len(u.body.encode("utf-8")) for u in units)

    ids = {u.id for u in units}
    files = {__import__("os").path.basename(u.path) for u in units}
    indexed_ids = {e.id for e in store.index}

    # index drift
    rep.missing_from_index = sorted(ids - indexed_ids)
    rep.dangling_index = [e.id for e in store.index if e.target not in files and e.id not in ids]

    # inbound link map (for orphan detection)
    inbound = {u.id: 0 for u in units}
    for u in units:
        for target in u.links:
            if target in inbound and target != u.id:
                inbound[target] += 1
            if target not in ids:
                rep.dead_links.append((u.id, target))

    now = time.time()
    for u in units:
        if inbound.get(u.id, 0) == 0 and u.id not in indexed_ids:
            rep.orphans.append(u.id)
        age_days = (now - u.mtime) / 86400 if u.mtime else 0
        if age_days > STALE_DAYS:
            rep.stale.append((u.id, round(age_days)))
        if u.size_chars > OVERSIZE_CHARS:
            rep.oversized.append((u.id, u.size_chars))

    # lexical duplicate candidates (flag only)
    toksets = {u.id: _tokens(u.gist + " " + u.body) for u in units}
    for i in range(len(units)):
        for j in range(i + 1, len(units)):
            a, b = units[i], units[j]
            s = _jaccard(toksets[a.id], toksets[b.id])
            if s >= DUP_JACCARD:
                rep.dup_candidates.append((a.id, b.id, round(s, 2)))

    # freshness score = mean per-unit exponential decay, by type half-life
    if units:
        total = 0.0
        for u in units:
            age_days = (now - u.mtime) / 86400 if u.mtime else 0
            hl = HALFLIFE_DAYS.get(u.type, HALFLIFE_DAYS["unknown"])
            total += 0.5 ** (age_days / hl)
        rep.freshness = round(total / len(units) * 100)
    return rep


def render_card(rep: HealthReport) -> str:
    kb = rep.total_bytes / 1024
    lines = [
        f"🧠 Memory Health   ({rep.total_units} units, {kb:.1f} KB · format: {rep.store.fmt})",
    ]

    def row(label, count, detail="", flag=""):
        bar = f"{label+':':<18}{count}"
        if detail:
            bar = f"{bar:<28}{detail}"
        if flag:
            bar = f"{bar}  {flag}"
        return "├─ " + bar

    idx_issues = rep.fixable_index_issues
    lines.append(row("Index drift", idx_issues,
                     f"{len(rep.missing_from_index)} missing / {len(rep.dangling_index)} dangling",
                     "▲ fixable" if idx_issues else "✓"))
    lines.append(row("Duplicate cand.", len(rep.dup_candidates),
                     "lexical", "▲ review (v0.2 merge)" if rep.dup_candidates else "✓"))
    lines.append(row("Conflicts", "—", "needs LLM", "→ v0.2"))
    lines.append(row("Dead links", len(rep.dead_links),
                     "", "⚠" if rep.dead_links else "✓"))
    lines.append(row("Orphans", len(rep.orphans),
                     "no inbound + unindexed", "▲" if rep.orphans else "✓"))
    lines.append(row("Stale (>30d)", len(rep.stale),
                     "", "" if not rep.stale else "▲"))
    lines.append(row("Oversized", len(rep.oversized),
                     f">{OVERSIZE_CHARS} chars", "▲ compact (v0.2)" if rep.oversized else "✓"))
    # last row uses └─
    lines.append(f"└─ {'Freshness:':<18}{rep.freshness} / 100")

    # detail appendix
    def detail_block(title, items):
        if not items:
            return []
        return [f"\n{title}:"] + [f"  • {x}" for x in items]

    out = ["\n".join(lines)]
    out += detail_block("Index — missing entries", rep.missing_from_index)
    out += detail_block("Index — dangling entries", rep.dangling_index)
    out += detail_block("Dead links", [f"{a} → [[{b}]]" for a, b in rep.dead_links])
    out += detail_block("Orphans", rep.orphans)
    out += detail_block("Duplicate candidates",
                        [f"{a} ~ {b}  ({s})" for a, b, s in rep.dup_candidates])
    out += detail_block("Oversized", [f"{i}  ({c} chars)" for i, c in rep.oversized])
    out += detail_block("Stale", [f"{i}  ({d}d)" for i, d in rep.stale])
    return "\n".join(p for p in out if p)

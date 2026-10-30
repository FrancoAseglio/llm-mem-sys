"""Scoring for the session sets (consistency across turns, set K). Pure: no database, no model.

The design is frozen in docs/predictions/set_K.md, section 1:
  correct           every `expect` group has a word in the answer
  forbid_raw        a `forbid` word (outdated or wrong value) is in the answer, before hand review
  forbid_in_prompt  a `forbid` word is in the memory lines
  stable fact       every probe of one fact (in one story, at least two probes) is correct and has
                    no contradiction
"""

from evaluation.metrics import contains_any, normalise


def score_probe(answer: str, lines: list[str], probe: dict) -> dict:
    """The keyword scores of one probe in one mode (hand review comes later)."""
    a = normalise(answer)
    expect = probe.get("expect", [])
    forbid = probe.get("forbid", [])
    return {
        "correct": all(any(w in a for w in group) for group in expect),
        "forbid_raw": contains_any(answer, forbid) if forbid else None,
        "forbid_in_prompt": contains_any(" ".join(lines), forbid) if forbid else None,
    }


def stability_groups(probes: list[dict]) -> dict[tuple[str, str], list[dict]]:
    """Probes grouped by (story, fact), keeping only facts with at least two probes."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for p in probes:
        groups.setdefault((p["scenario"], p["fact"]), []).append(p)
    return {k: v for k, v in groups.items() if len(v) >= 2}


def is_stable(group: list[dict], mode: str) -> bool:
    """Every probe of the group correct, and none with a forbidden word in the answer."""
    return all(p[mode]["correct"] and not p[mode]["forbid_raw"] for p in group)


def totals(probes: list[dict], mode: str) -> dict:
    """The numbers of the summary table for one mode (keyword scores, before hand review)."""
    groups = stability_groups(probes)
    indirect = [p for p in probes if p["type"] == "indirect"]
    with_forbid = [p for p in probes if p[mode]["forbid_raw"] is not None]
    return {
        "correct": sum(p[mode]["correct"] for p in probes),
        "probes": len(probes),
        "contradictions_raw": sum(bool(p[mode]["forbid_raw"]) for p in with_forbid),
        "forbid_probes": len(with_forbid),
        "forbid_in_prompt": sum(bool(p[mode]["forbid_in_prompt"]) for p in with_forbid),
        "stable": sum(is_stable(g, mode) for g in groups.values()),
        "groups": len(groups),
        "indirect_correct": sum(p[mode]["correct"] for p in indirect),
        "indirect": len(indirect),
    }

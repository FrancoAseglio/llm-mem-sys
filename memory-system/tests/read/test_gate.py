"""Pure tests for the relevance gate (no database, no model): retrieve.gate_failure and
retrieve.select_memories with hand-made Memory objects."""

from datetime import datetime

import pytest

from memory_system.read import retrieve
from memory_system.read.retrieve import Memory, best_raw, gate_failure, select_memories


@pytest.fixture(autouse=True)
def gate_settings(monkeypatch):
    monkeypatch.setattr(retrieve, "MIN_RELEVANCE", 0.42)
    monkeypatch.setattr(retrieve, "RELATIVE_WINDOW", 0.08)
    monkeypatch.setattr(retrieve, "ROUTING_TOP_N", 2)
    monkeypatch.setattr(retrieve, "SAFETY_BYPASS", True)
    monkeypatch.setattr(retrieve, "SAFETY_RELATIONS", {"allergic_to"})
    monkeypatch.setattr(retrieve, "PIN_IMPORTANCE", 1.01)


def mem(id, relation, raw, rank=1, pinned=False):
    return Memory(
        id, relation, "v", datetime(2026, 1, 1), 0.0, pinned, {},
        raw_similarity=raw, relation_rank=rank,
    )


def ids(memories):
    return [m.id for m in memories]


def test_floor_drops_weak_matches():
    weak = mem(1, "lives_in", 0.30)
    assert gate_failure(weak, best=0.30)[0] == "floor"
    assert gate_failure(weak, best=0.30)[1] == pytest.approx(0.12)


def test_window_drops_facts_far_below_the_best():
    top, neighbour = mem(1, "lives_in", 0.70), mem(2, "works_at", 0.55)
    assert gate_failure(top, best_raw([top, neighbour])) is None
    stage, gap = gate_failure(neighbour, best_raw([top, neighbour]))
    assert stage == "window" and gap == pytest.approx(0.15)


def test_routing_drops_facts_of_unrelated_relations():
    far = mem(1, "hobby", 0.60, rank=5)
    assert gate_failure(far, best=0.60) == ("routing", 5.0)


def test_routing_off_lets_every_relation_through(monkeypatch):
    monkeypatch.setattr(retrieve, "ROUTING_TOP_N", 0)
    assert gate_failure(mem(1, "hobby", 0.60, rank=9), best=0.60) is None


def test_allergy_bypasses_floor_and_window_when_routed():
    allergy = mem(1, "allergic_to", 0.30, rank=2)
    assert gate_failure(allergy, best=0.70) is None
    assert gate_failure(mem(2, "allergic_to", 0.30, rank=3), best=0.70)[0] == "floor"


def test_safety_bypass_can_be_switched_off(monkeypatch):
    monkeypatch.setattr(retrieve, "SAFETY_BYPASS", False)
    assert gate_failure(mem(1, "allergic_to", 0.30, rank=1), best=0.70)[0] == "floor"


def test_best_raw_ignores_facts_below_the_floor_and_pinned_ones():
    scored = [mem(1, "a", 0.30), mem(2, "b", 0.50), mem(3, "c", 0.90, pinned=True)]
    assert best_raw(scored) == 0.50
    assert best_raw([mem(1, "a", 0.10)]) == 0.0


def test_select_memories_keeps_score_order_and_caps_at_k():
    scored = [mem(i, "lives_in", 0.60) for i in range(1, 7)]
    pinned, relevant = select_memories(scored, k=4)
    assert pinned == [] and ids(relevant) == [1, 2, 3, 4]


def test_select_memories_returns_pinned_separately(monkeypatch):
    monkeypatch.setattr(retrieve, "PIN_IMPORTANCE", 0.9)
    scored = [mem(1, "name", 0.10, pinned=True), mem(2, "lives_in", 0.60)]
    pinned, relevant = select_memories(scored, k=4)
    assert ids(pinned) == [1] and ids(relevant) == [2]

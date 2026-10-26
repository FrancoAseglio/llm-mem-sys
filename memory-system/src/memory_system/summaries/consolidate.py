"""Consolidation: merge old notes of one user into shorter digests.

consolidate(user_id) runs after summarize_pending. When the user has at least CONSOLIDATE_MIN live
notes older than CONSOLIDATE_AGE_DAYS (by their newest source message), the model groups them by
topic and writes one or two sentences per group, citing the notes it merges. Each digest must pass
three pure checks (summaries/rules.py):

  faithful   is_faithful against the source messages of the notes it cites (the notes' own rule)
  retention  it keeps every number and capitalised name of those notes (month and weekday excepted)
  shorter    it is shorter than those notes together

A digest that passes is stored as a `summaries` row with kind = 'digest'; its notes get digest_id
and stop being retrieved, but are kept. A digest that fails is dropped and its notes stay live.
One `consolidate` event per run lists what was kept and what was dropped, with reasons. A failed
model call stores nothing and logs a `reject` event. Messages are never touched.

The design was frozen before any code (docs/predictions/set_J.md, section 1).
"""

from pydantic import BaseModel

from memory_system.core.config import (
    CONSOLIDATE,
    CONSOLIDATE_AGE_DAYS,
    CONSOLIDATE_BATCH,
    CONSOLIDATE_MIN,
    SUMMARIES,
    SUMMARY_FAITHFUL_MIN,
)
from memory_system.core.db import get_pool
from memory_system.core.events import log_event
from memory_system.core.llm import chat_structured, embed
from memory_system.summaries.rules import is_faithful, missing_details

SYSTEM_PROMPT = """You merge short memory notes about the USER into fewer, shorter digests.

You get numbered notes. Group the notes that are about the same topic, trip, project or story, and write one digest per group.
Rules:
- One or two sentences per digest, shorter than the notes it merges put together.
- Keep every name, place, number, price and time exactly as written in the notes. Add nothing.
- Start with "The user" or "The user's" and write in the third person.
- If the notes show that something changed, write the final state; keep both values when the notes give both (for example a quote and a final price).
- What another person did stays theirs: never make the user the one who did it.
- A digest merges at least two notes. Leave out a note that fits no group.
- For every digest give the numbers of the notes it merges.
- If nothing can be merged, return {"digests": []}.

Example:
Notes:
1. "The user signed up for a Tuesday pottery class."
2. "The user made a blue bowl in the pottery class."
3. "The user's colleague Dorota is moving to Riga next week."
4. "The user's pottery teacher Wanda praised the user's blue bowl."
Output:
{"digests": [{"text": "The user takes a Tuesday pottery class and made a blue bowl there, which their teacher Wanda praised.", "notes": [1, 2, 4]}]}
"""


class Digest(BaseModel):
    text: str
    notes: list[int]


class DigestList(BaseModel):
    digests: list[Digest]


def _old_notes(conn, user_id: str) -> list[tuple]:
    """(id, content, period_start, period_end) of live notes older than the age limit, oldest first."""
    return conn.execute(
        """SELECT id, content, period_start, COALESCE(period_end, created_at) AS ended
           FROM summaries
           WHERE user_id = %s AND kind = 'note' AND digest_id IS NULL
             AND COALESCE(period_end, created_at) < now() - make_interval(days => %s)
           ORDER BY ended, id
           LIMIT %s""",
        (user_id, CONSOLIDATE_AGE_DAYS, CONSOLIDATE_BATCH),
    ).fetchall()


def _sources(conn, note_ids: list[int]) -> dict[int, list[str]]:
    """The source messages of each note (messages.summary_id), by note id."""
    by_note: dict[int, list[str]] = {n: [] for n in note_ids}
    for summary_id, content in conn.execute(
        "SELECT summary_id, content FROM messages WHERE summary_id = ANY(%s) ORDER BY id",
        (note_ids,),
    ):
        by_note[summary_id].append(content)
    return by_note


def _already_tried(conn, user_id: str, notes: list[tuple]) -> bool:
    """True if the last run looked at exactly these notes, so asking again would change nothing."""
    last = conn.execute(
        "SELECT details->'considered' FROM memory_events "
        "WHERE user_id = %s AND event_type = 'consolidate' ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    return bool(last) and last[0] == [n[0] for n in notes]


def consolidate(user_id: str) -> list[str]:
    """Merge the user's old notes into digests. Returns the digests kept (empty if none)."""
    if not (SUMMARIES and CONSOLIDATE):
        return []
    with get_pool().connection() as conn:
        notes = _old_notes(conn, user_id)
        if len(notes) < CONSOLIDATE_MIN or _already_tried(conn, user_id, notes):
            return []
        sources = _sources(conn, [n[0] for n in notes])

    numbered = "\n".join(f'{i}. "{n[1]}"' for i, n in enumerate(notes, 1))
    try:
        result = chat_structured(
            SYSTEM_PROMPT, f"Notes:\n{numbered}\nOutput:", DigestList
        )
    except Exception as error:  # model down, timeout or malformed JSON
        with get_pool().connection() as conn:
            log_event(
                conn,
                user_id,
                "reject",
                None,
                {"reason": "consolidation failed", "error": repr(error)[:200]},
            )
        return []

    by_number = dict(enumerate(notes, 1))
    kept, kept_ids, digested, dropped = [], [], [], []
    taken: set[int] = set()  # notes already merged into a digest kept in this run
    with get_pool().connection() as conn:
        for digest in result.digests:
            text = digest.text.strip()
            numbers = [n for n in dict.fromkeys(digest.notes) if n in by_number]
            cited = [by_number[n] for n in numbers]
            entry = {"text": text, "notes": [c[0] for c in cited]}
            if not text or len(cited) < 2:
                dropped.append({**entry, "reason": "fewer than 2 notes"})
                continue
            if any(c[0] in taken for c in cited):
                dropped.append({**entry, "reason": "note already merged"})
                continue
            messages = [m for c in cited for m in sources[c[0]]]
            if not is_faithful(text, messages, SUMMARY_FAITHFUL_MIN):
                dropped.append({**entry, "reason": "not faithful"})
                continue
            missing = missing_details(text, [c[1] for c in cited])
            if missing:
                dropped.append(
                    {**entry, "reason": "dropped details", "missing": missing}
                )
                continue
            if len(text) >= sum(len(c[1]) for c in cited):
                dropped.append({**entry, "reason": "not shorter"})
                continue
            digest_id = conn.execute(
                "INSERT INTO summaries "
                "(user_id, kind, content, period_start, period_end, embedding) "
                "VALUES (%s, 'digest', %s, %s, %s, %s) RETURNING id",
                (
                    user_id,
                    text,
                    min(c[2] or c[3] for c in cited),
                    max(c[3] for c in cited),
                    embed(text),
                ),
            ).fetchone()[0]
            ids = [c[0] for c in cited]
            conn.execute(
                "UPDATE summaries SET digest_id = %s WHERE id = ANY(%s)",
                (digest_id, ids),
            )
            taken.update(ids)
            kept.append(text)
            kept_ids.append(digest_id)
            digested += ids
        log_event(
            conn,
            user_id,
            "consolidate",
            None,
            {
                "notes": len(notes),
                "considered": [n[0] for n in notes],
                "kept": kept_ids,
                "digested": digested,
                "dropped": dropped,
            },
        )
    return kept

"""Write side of the summaries layer: turn new user messages into short episode notes.

summarize_pending(user_id) reads the messages that came after the last run, asks the model for
one sentence per episode (with the numbers of the messages it used), keeps only the sentences
that pass the faithfulness check, stores them in `summaries` and links their source messages
(messages.summary_id). Each run logs one `summarize` event; its `up_to` is the last message
id seen, which is where the next run starts. A failed model call changes nothing and logs a
`reject` event, so the same messages are tried again next time.
"""

from pydantic import BaseModel

from memory_system.core.config import SUMMARY_BATCH, SUMMARY_FAITHFUL_MIN
from memory_system.core.db import get_pool
from memory_system.core.events import log_event
from memory_system.core.llm import chat_structured, embed
from memory_system.summaries.rules import is_chatter, is_faithful

SYSTEM_PROMPT = """You write short memory notes about the USER from their numbered messages.

Write one sentence per distinct thing the user did, experienced, bought, planned or went through.
Rules:
- Only what the messages say. Keep names, places, numbers and times exactly as written. Add nothing.
- Start every sentence with "The user" or "The user's" and write in the third person.
- Combine related messages into one sentence when they tell one story. If a later message changes or cancels an earlier one, write the final state.
- If a message is about another person, the note is about that person, not about the user.
- Skip questions, thanks and chit-chat. Skip plain personal facts that are stored elsewhere: name, home city, job, employer, allergies, languages, likes and dislikes.
- For every sentence give the numbers of the messages it uses.
- If nothing qualifies, return {"episodes": []}.

Examples:
Messages:
1. "Yesterday I fixed the kitchen tap myself, it took two hours."
2. "Thanks, that was helpful!"
3. "My colleague Dana is moving to Oslo next week."
Output:
{"episodes": [{"text": "The user fixed the kitchen tap themselves yesterday and it took two hours.", "messages": [1]}, {"text": "The user's colleague Dana is moving to Oslo next week.", "messages": [3]}]}

Messages:
1. "I'm thinking about taking a pottery class."
2. "I signed up for the Tuesday pottery class!"
Output:
{"episodes": [{"text": "The user signed up for the Tuesday pottery class after thinking about it.", "messages": [1, 2]}]}
"""


class Episode(BaseModel):
    text: str
    messages: list[int]


class EpisodeList(BaseModel):
    episodes: list[Episode]


def _pending(conn, user_id: str) -> list[tuple]:
    """(id, content, created_at) of the user's messages after the last summarize run."""
    done = conn.execute(
        "SELECT COALESCE(MAX((details->>'up_to')::bigint), 0) FROM memory_events "
        "WHERE user_id = %s AND event_type = 'summarize'",
        (user_id,),
    ).fetchone()[0]
    return conn.execute(
        "SELECT id, content, created_at FROM messages "
        "WHERE user_id = %s AND role = 'user' AND id > %s ORDER BY id",
        (user_id, done),
    ).fetchall()


def pending_count(user_id: str) -> int:
    """How many user messages have not been through a summarize run yet."""
    with get_pool().connection() as conn:
        return len(_pending(conn, user_id))


def _summarize_batch(user_id: str, batch: list[tuple]) -> list[str] | None:
    """Summarise one batch. Returns the kept sentences, or None if the model failed.

    Questions, requests and thanks are never sent to the model (the prompt asks it to skip
    them, but it did not always). They still count as seen, so the next run starts after them.
    """
    usable = [m for m in batch if not is_chatter(m[1])]
    numbered = "\n".join(f'{i}. "{text}"' for i, (_, text, _) in enumerate(usable, 1))
    try:
        result = (
            chat_structured(
                SYSTEM_PROMPT, f"Messages:\n{numbered}\nOutput:", EpisodeList
            )
            if usable
            else EpisodeList(episodes=[])
        )
    except Exception as error:  # model down, timeout or malformed JSON
        with get_pool().connection() as conn:
            log_event(
                conn,
                user_id,
                "reject",
                None,
                {"reason": "summarization failed", "error": repr(error)[:200]},
            )
        return None

    by_number = dict(enumerate(usable, 1))
    kept, kept_ids, dropped, linked = [], [], [], set()
    with get_pool().connection() as conn:
        existing = {
            row[0].lower()
            for row in conn.execute(
                "SELECT content FROM summaries WHERE user_id = %s", (user_id,)
            )
        }
        for episode in result.episodes:
            text = episode.text.strip()
            numbers = [n for n in dict.fromkeys(episode.messages) if n in by_number]
            if not text or not numbers:
                dropped.append({"text": text, "reason": "no source"})
                continue
            sources = [by_number[n] for n in numbers]
            if not is_faithful(text, [s[1] for s in sources], SUMMARY_FAITHFUL_MIN):
                dropped.append({"text": text, "reason": "not faithful"})
                continue
            if text.lower() in existing:
                continue
            existing.add(text.lower())
            # each message is linked to one summary only (messages.summary_id)
            ids = [s[0] for s in sources if s[0] not in linked]
            linked.update(ids)
            summary_id = conn.execute(
                "INSERT INTO summaries (user_id, content, period_start, period_end, embedding) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (
                    user_id,
                    text,
                    min(s[2] for s in sources),
                    max(s[2] for s in sources),
                    embed(text),
                ),
            ).fetchone()[0]
            if ids:
                conn.execute(
                    "UPDATE messages SET summary_id = %s WHERE id = ANY(%s) AND summary_id IS NULL",
                    (summary_id, ids),
                )
            kept.append(text)
            kept_ids.append(summary_id)
        log_event(
            conn,
            user_id,
            "summarize",
            None,
            {
                "up_to": batch[-1][0],
                "messages": len(batch),
                "skipped": len(batch) - len(usable),
                "kept": kept_ids,
                "dropped": dropped,
            },
        )
    return kept


def summarize_pending(user_id: str) -> list[str]:
    """Summarise the user's new messages, SUMMARY_BATCH at a time. Returns the sentences kept."""
    kept: list[str] = []
    while True:
        with get_pool().connection() as conn:
            batch = _pending(conn, user_id)[:SUMMARY_BATCH]
        if not batch:
            return kept
        result = _summarize_batch(user_id, batch)
        if result is None:  # model failed: leave these messages for the next run
            return kept
        kept += result

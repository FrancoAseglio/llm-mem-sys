from typing import Literal

from pydantic import BaseModel

from memory_system.llm import chat_structured


class ExtractedFact(BaseModel):
    relation: str
    value: str
    action: Literal["assert", "retract"] = "assert"


class ExtractionResult(BaseModel):
    facts: list[ExtractedFact]


def load_relation_types(conn) -> dict[str, tuple[str, str]]:
    """Return {name: (cardinality, description)} for every relation type."""
    rows = conn.execute(
        "SELECT name, cardinality, description FROM relation_types"
    ).fetchall()
    return {name: (card, desc) for name, card, desc in rows}


def build_prompt(relations: dict[str, tuple[str, str]]) -> str:
    """System prompt for the extractor, listing the allowed relations."""
    allowed = "\n".join(f"- {name}: {desc}" for name, (_, desc) in relations.items())
    return f"""You extract long-term facts about the USER from one message.

Allowed relations (use these exact names only):
{allowed}

Rules:
- Only facts the user states about themselves. Ignore questions, greetings, thanks and chit-chat.
- Ignore temporary things (what they ate today, the weather).
- Keep values short and normalized: 'Milan', 'cycling', 'penicillin'.
- "I moved to X" or "I now live in X" means lives_in = X.
- Plans, hopes and things the user is saving for or working towards are durable: goal = X.
- If the user says something is NOT (or no longer) true, give that fact with action "retract"; "not X, but Y" is a retract for X and a fact for Y. Disliking or hating X is not a retract: dislikes = X.
- One item per fact. If there is nothing durable, return {{"facts": []}}.

Examples:
Message: "I live in Rome and I'm a nurse."
{{"facts": [{{"relation": "lives_in", "value": "Rome"}}, {{"relation": "job_title", "value": "nurse"}}]}}
Message: "I don't speak French, I speak Spanish."
{{"facts": [{{"relation": "speaks", "value": "French", "action": "retract"}}, {{"relation": "speaks", "value": "Spanish"}}]}}
Message: "Thanks, that was helpful!"
{{"facts": []}}
Message: "What's the weather like in Paris?"
{{"facts": []}}
"""


def extract_facts(
    text: str, relations: dict[str, tuple[str, str]]
) -> list[ExtractedFact]:
    """Extract durable facts about the user from one message, deduplicated.

    Each fact has an action: 'assert' (default) or 'retract' (the user says it is not true).
    """
    result = chat_structured(
        build_prompt(relations), f'Message: "{text}"', ExtractionResult
    )
    clean, seen = [], set()
    for fact in result.facts:
        relation, value = fact.relation.strip(), fact.value.strip()
        key = (relation, value.lower(), fact.action)
        # drop invented relations, empty values and repeats
        if relation in relations and value and key not in seen:
            seen.add(key)
            clean.append(
                ExtractedFact(relation=relation, value=value, action=fact.action)
            )
    return clean

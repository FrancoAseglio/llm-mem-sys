from pydantic import BaseModel

from memory_system.llm import chat_structured


class ExtractedFact(BaseModel):
    relation: str
    value: str


class ExtractionResult(BaseModel):
    facts: list[ExtractedFact]


def load_relation_types(conn) -> dict[str, tuple[str, str]]:
    rows = conn.execute("SELECT name, cardinality, description FROM relation_types").fetchall()
    return {name: (card, desc) for name, card, desc in rows}


def build_prompt(relations: dict[str, tuple[str, str]]) -> str:
    allowed = "\n".join(f"- {name}: {desc}" for name, (_, desc) in relations.items())
    return f"""You extract long-term facts about the USER from one message.

Allowed relations (use these exact names only):
{allowed}

Rules:
- Only facts the user states about themselves. Ignore questions, greetings, thanks and chit-chat.
- Ignore temporary things (what they ate today, the weather).
- Keep values short and normalized: 'Milan', 'cycling', 'penicillin'.
- "I moved to X" or "I now live in X" means lives_in = X.
- One item per fact. If there is nothing durable, return {{"facts": []}}.

Examples:
Message: "I live in Rome and I'm a nurse."
{{"facts": [{{"relation": "lives_in", "value": "Rome"}}, {{"relation": "job_title", "value": "nurse"}}]}}
Message: "Thanks, that was helpful!"
{{"facts": []}}
Message: "What's the weather like in Paris?"
{{"facts": []}}
"""


def extract_facts(text: str, relations: dict[str, tuple[str, str]]) -> list[ExtractedFact]:
    result = chat_structured(build_prompt(relations), f'Message: "{text}"', ExtractionResult)
    clean, seen = [], set()
    for fact in result.facts:
        relation, value = fact.relation.strip(), fact.value.strip()
        key = (relation, value.lower())
        if relation in relations and value and key not in seen:  # drop invented relations
            seen.add(key)
            clean.append(ExtractedFact(relation=relation, value=value))
    return clean

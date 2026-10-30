"""Prompt labels for relation types: 'lives_in' -> 'Lives in'. Unknown names fall back as is."""

LABELS = {
    "name": "Name",
    "lives_in": "Lives in",
    "works_at": "Works at",
    "job_title": "Job title",
    "partner": "Partner",
    "birthday": "Birthday",
    "hobby": "Hobby",
    "likes": "Likes",
    "dislikes": "Dislikes",
    "allergic_to": "Allergic to",
    "family_member": "Family member",
    "speaks": "Speaks",
    "goal": "Goal",
}


def label(relation: str) -> str:
    return LABELS.get(relation, relation)

"""SET B: 8 scenarios.

Status: SPENT. It was held out when written, but the floor and window were chosen after
looking at it. Covers: indirect dislikes, allergies (safety and noise), paraphrases, flooded
history, precision, a correction, name recall.
"""

from .common import FOOD, NAMEY, NEUTRAL, TURIN_CHATTER, spread

SCENARIOS = [
    {
        "id": "b_indirect_dislike",
        "kind": "indirect",
        "messages": [(200, "I can't stand olives, the taste is awful.")]
        + spread(FOOD + NEUTRAL[:2], 10, 190),
        "questions": [
            {
                "q": "I'm making a pizza for friends tonight. What toppings should I skip for myself?",
                "expect": [["olive"]],
                "needs": ["olive"],
            },
        ],
    },
    {
        "id": "b_food_allergy",
        "kind": "safety",
        "messages": [(220, "I'm allergic to peanuts.")] + spread(NEUTRAL[:8], 10, 200),
        "questions": [
            # no "expect": a good answer may simply suggest an apple, so only retrieval is checked
            {"q": "Can you suggest a quick snack for me?", "needs": ["peanut"]},
        ],
    },
    {
        "id": "b_drug_allergy_noise",
        "kind": "noise",
        "messages": [(150, "I'm allergic to penicillin.")]
        + spread(FOOD + NEUTRAL[:2], 10, 140),
        "questions": [
            {"q": "Can you suggest a dinner recipe for me?", "avoid": ["penicillin"]},
        ],
    },
    {
        "id": "b_paraphrase_job",
        "kind": "paraphrase",
        "messages": [(180, "I work as a pediatric nurse at the city hospital.")]
        + spread(NEUTRAL[:8], 10, 170),
        "questions": [
            {
                "q": "What do I do for a living?",
                "expect": [["nurse"]],
                "needs": ["nurse"],
            },
        ],
    },
    {
        "id": "b_stale_flood",
        "kind": "flood",
        "messages": [(300, "I live in Turin.")]
        + spread(TURIN_CHATTER, 200, 290)
        + [(60, "I moved to Rome last month!")],
        "questions": [
            {
                "q": "Which city do I live in?",
                "expect": [["rome"]],
                "needs": ["rome"],
                "stale": ["turin"],
            },
        ],
    },
    {
        "id": "b_precision",
        "kind": "noise",
        "messages": [
            (200, "I live in Rome, I'm a teacher and I love painting."),
            (150, "I also speak Spanish."),
        ]
        + spread(NEUTRAL[:7], 10, 140),
        "questions": [
            {
                "q": "Which languages do I speak?",
                "expect": [["spanish"]],
                "needs": ["spanish"],
                "avoid": ["rome", "teacher", "painting"],
            },
        ],
    },
    {
        "id": "b_correction",
        "kind": "correction",
        "messages": [(200, "I'm allergic to peanuts.")]
        + spread(NEUTRAL[:6], 40, 190)
        + [
            (
                30,
                "Actually I was wrong earlier, I'm not allergic to peanuts, "
                "I'm allergic to walnuts.",
            )
        ],
        "questions": [
            {
                "q": "Which nuts am I allergic to?",
                "expect": [["walnut"]],
                "needs": ["walnut"],
                "stale": ["peanut"],
            },
        ],
    },
    {
        "id": "b_name_recall",
        "kind": "noise",
        "messages": [(250, "My name is Franco.")]
        + spread(NAMEY + NEUTRAL[:3], 10, 240),
        "questions": [
            {"q": "What's my name?", "expect": [["franco"]], "needs": ["franco"]},
        ],
    },
]

"""SET D: a second rich profile (Tomas), a small safety scenario and a job switch. 19 questions.

Status: SPENT. Blind, written before relation routing existed in the pipeline; run once.
"""

from .common import ABSTAIN, NEUTRAL, spread

D_RICH = [
    (340, "Hi, I'm Tomas and I live in Lisbon."),
    (330, "I'm a pharmacist at a small clinic."),
    (310, "My wife is called Ines."),
    (290, "I speak Portuguese, English and a little German."),
    (270, "I play the guitar in the evenings."),
    (250, "I'm allergic to eggs."),
    (230, "I really hate anchovies, the smell is awful."),
    (210, "My favourite kind of music is fado."),
    (190, "I'm saving up to buy a small boat."),
    (170, "My sister is named Marta."),
    (150, "I was born on the 3rd of March."),
    (130, "I also enjoy cooking, especially bread."),
] + spread(NEUTRAL[:6], 15, 120)

D_WORDS = [
    "tomas",
    "lisbon",
    "pharmacist",
    "clinic",
    "ines",
    "portuguese",
    "english",
    "german",
    "guitar",
    "egg",
    "anchovies",
    "fado",
    "boat",
    "marta",
    "march",
    "cooking",
]


def _d_others(*keep):
    return [w for w in D_WORDS if w not in keep]


SCENARIOS = [
    {
        "id": "d_rich_profile",
        "kind": "rich",
        "messages": D_RICH,
        "questions": [
            {
                "q": "What's my name?",
                "expect": [["tomas"]],
                "needs": ["tomas"],
                "avoid": _d_others("tomas", "lisbon"),
            },
            {
                "q": "Where do I live?",
                "expect": [["lisbon"]],
                "needs": ["lisbon"],
                "avoid": _d_others("lisbon", "tomas"),
            },
            {
                "q": "What do I do for a living?",
                "expect": [["pharmacist"]],
                "needs": ["pharmacist"],
                "avoid": _d_others("pharmacist", "clinic"),
            },
            {
                "q": "What's my wife's name?",
                "expect": [["ines"]],
                "needs": ["ines"],
                "avoid": _d_others("ines"),
            },
            {
                "q": "Which languages do I speak?",
                "expect": [["portuguese"], ["english"], ["german"]],
                "needs": ["portuguese", "english", "german"],
                "avoid": _d_others("portuguese", "english", "german"),
            },
            {
                "q": "I'm picking a cafe for breakfast tomorrow. What should I watch out for on the menu?",
                "expect": [["egg"]],
                "needs": ["egg"],
                "avoid": _d_others("egg"),
            },
            {
                "q": "I'm making a pizza tonight. Which topping should I skip for myself?",
                "expect": [["anchovies", "anchovy"]],
                "needs": ["anchovies"],
                "avoid": _d_others("anchovies", "egg"),
            },
            {
                "q": "What music would you put on for me?",
                "expect": [["fado"]],
                "needs": ["fado"],
                "avoid": _d_others("fado"),
            },
            {
                "q": "What am I saving up for?",
                "expect": [["boat"]],
                "needs": ["boat"],
                "avoid": _d_others("boat"),
            },
            {
                "q": "When is my birthday?",
                "expect": [["march"]],
                "needs": ["march"],
                "avoid": _d_others("march"),
            },
            {
                "q": "What's my sister called?",
                "expect": [["marta"]],
                "needs": ["marta"],
                "avoid": _d_others("marta"),
            },
            {
                "q": "What do I like doing in my free time?",
                "expect": [["guitar"], ["cooking"]],
                "needs": ["guitar", "cooking"],
                "avoid": _d_others("guitar", "cooking"),
            },
            {"q": "What car do I drive?", "expect": [ABSTAIN], "avoid": D_WORDS},
            {"q": "What's my dog's name?", "expect": [ABSTAIN], "avoid": D_WORDS},
            {"q": "What's my mother's job?", "expect": [ABSTAIN], "avoid": D_WORDS},
        ],
    },
    {
        "id": "d_small_safety",
        "kind": "safety",
        "messages": [
            (220, "I have a serious gluten intolerance, I can't eat it at all."),
            (200, "I live in Naples."),
        ]
        + spread(NEUTRAL[:6], 10, 190),
        "questions": [
            {
                "q": "Can you suggest a quick lunch for me?",
                "needs": ["gluten"],
                "avoid": ["naples"],
            },
            {
                "q": "Which city am I based in?",
                "expect": [["naples"]],
                "needs": ["naples"],
                "avoid": ["gluten"],
            },
        ],
    },
    {
        "id": "d_job_switch",
        "kind": "stale",
        "messages": [
            (300, "I work at Bluefin Labs as a data analyst."),
            (90, "I've left Bluefin and joined Harbor Bank as an accountant."),
        ],
        "questions": [
            {
                "q": "Where do I work now?",
                "expect": [["harbor"]],
                "needs": ["harbor"],
                "stale": ["bluefin"],
            },
            {
                "q": "What's my job title?",
                "expect": [["accountant"]],
                "needs": ["accountant"],
                "stale": ["analyst"],
            },
        ],
    },
]

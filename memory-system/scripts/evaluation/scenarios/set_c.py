"""SET C: one user with a rich profile (11 facts) plus two small scenarios.

Status: SPENT. Blind when written, before the relative window was run on it. Many facts compete
for the same question, and abstain questions test the floor.
"""

from .common import ABSTAIN, NEUTRAL, spread

RICH = [
    (330, "My name is Giulia and I live in Bologna."),
    (320, "I work as an architect at Studio Verdi."),
    (300, "My partner is Marco."),
    (280, "I speak Italian and English."),
    (260, "I love running, I usually go out before sunrise."),
    (240, "I also enjoy photography."),
    (220, "I'm allergic to shellfish."),
    (200, "I really dislike coriander, it tastes like soap."),
    (180, "I like jazz music a lot."),
    (160, "I'd love to learn how to sail one day."),
    (140, "My brother's name is Luca."),
] + spread(NEUTRAL[:6], 20, 130)

RICH_WORDS = [
    "giulia",
    "bologna",
    "architect",
    "marco",
    "italian",
    "running",
    "photography",
    "shellfish",
    "coriander",
    "jazz",
    "sail",
    "luca",
]


def _others(*keep):
    return [w for w in RICH_WORDS if w not in keep]


SCENARIOS = [
    {
        "id": "c_rich_profile",
        "kind": "rich",
        "messages": RICH,
        "questions": [
            {
                "q": "What's my name?",
                "expect": [["giulia"]],
                "needs": ["giulia"],
                "avoid": _others("giulia", "bologna"),
            },
            {
                "q": "Which city do I live in?",
                "expect": [["bologna"]],
                "needs": ["bologna"],
                "avoid": _others("bologna", "giulia"),
            },
            {
                "q": "What do I do for work?",
                "expect": [["architect"]],
                "needs": ["architect"],
                "avoid": _others("architect"),
            },
            {
                "q": "Who is my partner?",
                "expect": [["marco"]],
                "needs": ["marco"],
                "avoid": _others("marco"),
            },
            {
                "q": "Which languages do I speak?",
                "expect": [["italian"], ["english"]],
                "needs": ["italian", "english"],
                "avoid": _others("italian"),
            },
            {
                "q": "I'm booking a restaurant for tonight. What should I avoid eating?",
                "expect": [["shellfish"], ["coriander"]],
                "needs": ["shellfish", "coriander"],
                "avoid": _others("shellfish", "coriander"),
            },
            {
                "q": "What's my brother called?",
                "expect": [["luca"]],
                "needs": ["luca"],
                "avoid": _others("luca"),
            },
            {
                "q": "What kind of music do I like?",
                "expect": [["jazz"]],
                "needs": ["jazz"],
                "avoid": _others("jazz"),
            },
            {
                "q": "What is my favourite colour?",
                "expect": [ABSTAIN],
                "avoid": RICH_WORDS,
            },
            {"q": "What's my pet's name?", "expect": [ABSTAIN], "avoid": RICH_WORDS},
        ],
    },
    {
        "id": "c_double_move",
        "kind": "stale",
        "messages": [
            (300, "I live in Genoa."),
            (180, "I've just moved to Bologna."),
            (60, "Big news, I'm now living in Verona!"),
        ]
        + spread(NEUTRAL[4:9], 20, 170),
        "questions": [
            {
                "q": "Which city do I live in?",
                "expect": [["verona"]],
                "needs": ["verona"],
                "stale": ["genoa", "bologna"],
            },
        ],
    },
    {
        "id": "c_new_job",
        "kind": "write-bug",
        "messages": [
            (200, "I work at Fabbrica Rossi as a designer."),
            (30, "Exciting news, I just started a new position at Delta Labs!"),
        ],
        "questions": [
            {
                "q": "Where do I work?",
                "expect": [["delta"]],
                "needs": ["delta"],
                "stale": ["rossi"],
                "avoid": ["new position", "new job"],
            },
        ],
    },
]

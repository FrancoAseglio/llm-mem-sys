"""SET I: questions about the past. 12 questions.

Status: BLIND. Written BEFORE the past-question mechanism exists. To be run once, after it is
built. Predictions: docs/predictions/set_I.md.

Past questions (value that was replaced), present-tense controls on the same users (an old value
must not come back), 'before' questions that are NOT about the user's past (the trigger must not
pull old values in), and a user who never changed anything. All people and places are new.
"""

from .common import ABSTAIN, NEUTRAL, assert_no_leaks, spread

SCENARIOS = [
    {
        "id": "i_move",
        "kind": "past",
        "messages": [
            (200, "I live in Bergen."),
            (60, "I moved to Tallinn last month."),
        ]
        + spread(NEUTRAL[:4], 10, 190),
        "questions": [
            {
                "q": "Which city did I live in before Tallinn?",
                "expect": [["bergen"]],
                "needs": ["bergen"],
            },
            {
                "q": "Which city do I live in now?",
                "expect": [["tallinn"]],
                "needs": ["tallinn"],
                "stale": ["bergen"],
            },
        ],
    },
    {
        "id": "i_job",
        "kind": "past",
        "messages": [
            (220, "I work at Halvorsen Marine."),
            (70, "I left Halvorsen Marine, I now work at Pelican Software."),
        ]
        + spread(NEUTRAL[2:6], 10, 210),
        "questions": [
            {
                "q": "Where did I work previously?",
                "expect": [["halvorsen"]],
                "needs": ["halvorsen"],
            },
            {
                "q": "Where do I work now?",
                "expect": [["pelican"]],
                "needs": ["pelican"],
                "stale": ["halvorsen"],
            },
        ],
    },
    {
        "id": "i_two_moves",
        "kind": "past",
        "messages": [
            (300, "I live in Ghent."),
            (180, "I moved to Valencia."),
            (50, "I've moved again, I live in Gdansk now."),
        ]
        + spread(NEUTRAL[4:8], 10, 290),
        "questions": [
            {
                "q": "Where did I live originally?",
                "expect": [["ghent"]],
                "needs": ["ghent"],
            },
            {
                "q": "Where did I live before Gdansk?",
                "expect": [["valencia"]],
                "needs": ["valencia"],
            },
        ],
    },
    {
        "id": "i_flip",
        "kind": "past",
        "messages": [
            (200, "I can't stand olives."),
            (60, "Funny thing, I've started to love olives."),
        ]
        + spread(NEUTRAL[6:10], 10, 190),
        "questions": [
            {
                "q": "What food did I use to dislike?",
                # 'olive' alone would also match the current like, so the answer and the
                # memory lines must carry the dislike itself
                "expect": [
                    ["olive"],
                    ["dislike", "hate", "can't stand", "didn't like"],
                ],
                "needs": ["dislike"],
            },
        ],
    },
    {
        "id": "i_partner",
        "kind": "past",
        "messages": [
            (250, "My partner is Dario."),
            (90, "Dario and I split up. I'm with Elena now."),
        ]
        + spread(NEUTRAL[:4], 10, 240),
        "questions": [
            {
                "q": "Who was my partner before Elena?",
                "expect": [["dario"]],
                "needs": ["dario"],
            },
            {
                "q": "Who is my partner?",
                "expect": [["elena"]],
                "needs": ["elena"],
                "stale": ["dario"],
            },
        ],
    },
    {
        # trap: 'before' appears, but the question is not about the user's past
        "id": "i_trap_before",
        "kind": "trap",
        "messages": [
            (180, "I live in Aarhus."),
            (50, "I moved to Cork."),
        ]
        + spread(NEUTRAL[4:8], 10, 170),
        "questions": [
            {
                "q": "Any tips for stretching before a run?",
                "avoid": ["aarhus", "cork"],
            },
            {
                "q": "What should I cook before my guests arrive?",
                "avoid": ["aarhus", "cork"],
            },
        ],
    },
    {
        # nothing was ever replaced: there is no past to report
        "id": "i_never_moved",
        "kind": "abstain",
        "messages": [
            (150, "I live in Leiden."),
        ]
        + spread(NEUTRAL[6:10], 10, 140),
        "questions": [
            {
                "q": "Where did I live before?",
                "expect": [ABSTAIN],
            },
        ],
    },
]

assert_no_leaks("I", NEUTRAL, SCENARIOS)

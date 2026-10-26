"""SET F: the write path only. 10 questions.

Status: SPENT. Written after the write-path fixes and before running it; run once.
Covers: corrections, a hallucination-prone message, likes/dislikes flips, employer changes.
The stored facts (evaluate.py --verbose) are the main check; predictions in docs/predictions/write_path_and_set_F.md.
"""

from .common import assert_no_leaks, spread

# The first four filler messages of set E, copied so that this set does not depend on set E.
F_FILLER = [
    "How do tides work?",
    "Can you explain what a black hole is?",
    "How do I fold a fitted sheet?",
    "What's the plot of Hamlet?",
]

SCENARIOS = [
    {
        # correction without the word "not"; expected: latex archived, pollen active
        "id": "f_correction_allergy",
        "kind": "correction",
        "messages": [
            (210, "I'm allergic to latex."),
            (
                35,
                "Sorry, I mixed things up before: latex is fine for me, "
                "it's pollen that I'm allergic to.",
            ),
        ]
        + spread(F_FILLER, 10, 200),
        "questions": [
            {
                "q": "What am I allergic to?",
                "expect": [["pollen"]],
                "needs": ["pollen"],
                "stale": ["latex"],
            },
        ],
    },
    {
        # "no longer" correction on a multi-valued relation; expected: chess archived, pottery active
        "id": "f_no_longer_hobby",
        "kind": "correction",
        "messages": [
            (190, "I play chess most evenings."),
            (25, "I don't play chess anymore; these days my hobby is pottery."),
        ]
        + spread(F_FILLER, 10, 180),
        "questions": [
            {
                "q": "What are my hobbies?",
                "expect": [["pottery"]],
                "needs": ["pottery"],
                "stale": ["chess"],
            },
        ],
    },
    {
        # hallucination-prone: no new title is stated; expected: teacher stays, nothing invented
        "id": "f_vague_promotion",
        "kind": "hallucination",
        "messages": [
            (200, "I work at Hillside School as a teacher."),
            (20, "Big day today, I finally got the promotion I'd been chasing!"),
        ],
        "questions": [
            {
                "q": "Where do I work?",
                "expect": [["hillside"]],
                "needs": ["hillside"],
                "avoid": ["promot", "manager", "senior"],
            },
            {"q": "What's my job title?", "avoid": ["promot", "manager", "senior"]},
        ],
    },
    {
        # likes -> dislikes; expected: likes superseded by dislikes (contradiction)
        "id": "f_like_to_dislike",
        "kind": "contradiction",
        "messages": [
            (180, "I love spicy food."),
            (30, "I've gone right off spicy food, I can't stand it these days."),
        ],
        "questions": [
            {"q": "What kind of food do I enjoy?", "avoid": ["spicy"]},
        ],
    },
    {
        # dislikes -> likes; expected: dislikes superseded by likes (contradiction)
        "id": "f_dislike_to_like",
        "kind": "contradiction",
        "messages": [
            (200, "I can't stand opera."),
            (40, "Funny thing, I've grown to really love opera lately."),
        ],
        "questions": [
            {"q": "What music do I like?", "expect": [["opera"]], "needs": ["opera"]},
        ],
    },
    {
        # employer change, no title; expected: nurse conflicted, so the title question gets nothing
        "id": "f_employer_no_title",
        "kind": "conflicted",
        "messages": [
            (240, "I'm a nurse at Saint Mary's Hospital."),
            (30, "I switched employers, I'm at Riverside Clinic now."),
        ],
        "questions": [
            {
                "q": "Where do I work?",
                "expect": [["riverside"]],
                "needs": ["riverside"],
                "stale": ["mary"],
            },
            {"q": "What's my job title?", "avoid": ["nurse"]},  # by design: conflicted
        ],
    },
    {
        # employer change with a title; expected: both superseded, nothing conflicted
        "id": "f_employer_with_title",
        "kind": "stale",
        "messages": [
            (260, "I work at Northwind as a sales rep."),
            (45, "I left Northwind and I'm now a product manager at Contoso."),
        ],
        "questions": [
            {
                "q": "Where do I work?",
                "expect": [["contoso"]],
                "needs": ["contoso"],
                "stale": ["northwind"],
            },
            {
                "q": "What's my job title?",
                "expect": [["product manager"]],
                "needs": ["product manager"],
                "stale": ["sales"],
            },
        ],
    },
]

assert_no_leaks("F", F_FILLER, SCENARIOS)

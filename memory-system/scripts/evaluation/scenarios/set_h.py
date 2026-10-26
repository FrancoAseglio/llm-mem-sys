"""SET H: validation of the summaries layer. 15 questions.

Status: BLIND. Written after the summaries design was approved and BEFORE any summaries code
exists. To be run once, after the layer is built. Predictions: docs/predictions/set_H.md.

Mostly episodes that no typed fact holds (the layer's job), plus guards for what it could
break: third-person statements turned into the user's, a cancelled plan kept as live, and
typed-fact questions that summaries could pollute. All people, places and topics are new.
"""

from .common import ABSTAIN, assert_no_leaks, spread

H_FILLER = [
    "What's the boiling point of water at altitude?",
    "How do bees make honey?",
    "Can you explain what a mortgage is?",
    "What's the longest river in Africa?",
    "How does a rainbow form?",
    "What's a good way to memorise a poem?",
    "How many bones are in the human body?",
    "What does a thermostat do?",
]

SCENARIOS = [
    {
        # episode: a single event with an object
        "id": "h_bake",
        "kind": "episode",
        "messages": [
            (
                70,
                "Last weekend I baked my first sourdough loaf and it came out completely flat.",
            ),
        ]
        + spread(H_FILLER[:4], 10, 65),
        "questions": [
            {
                "q": "What did I bake last weekend?",
                "expect": [["sourdough"]],
                "needs": ["sourdough"],
            },
        ],
    },
    {
        # episode: cause and duration in one message
        "id": "h_injury",
        "kind": "episode",
        "messages": [
            (
                130,
                "I broke my wrist skiing in February and had a cast on for six weeks.",
            ),
        ]
        + spread(H_FILLER[2:6], 10, 120),
        "questions": [
            {
                "q": "How did I hurt my wrist?",
                "expect": [["ski"]],
                "needs": ["ski"],
            },
            {
                "q": "How long did I wear the cast?",
                "expect": [["six"]],
                "needs": ["six"],
            },
        ],
    },
    {
        # episode: a purchase with a price
        "id": "h_purchase",
        "kind": "episode",
        "messages": [
            (
                95,
                "I finally bought a second-hand Vespa from my neighbour for 900 euros.",
            ),
        ]
        + spread(H_FILLER[4:8], 10, 85),
        "questions": [
            {
                "q": "What did I buy from my neighbour?",
                "expect": [["vespa"]],
                "needs": ["vespa"],
            },
            {
                "q": "How much did it cost?",
                "expect": [["900"]],
                "needs": ["900"],
            },
        ],
    },
    {
        # a story over several messages: what a summary should hold
        "id": "h_adoption",
        "kind": "story",
        "messages": [
            (180, "I'm thinking about adopting a rescue greyhound."),
            (150, "I visited the shelter today and met a greyhound called Biscuit."),
            (120, "The adoption paperwork got approved!"),
            (100, "Biscuit comes home on Saturday, I can't wait."),
            (90, "Biscuit already chewed one of my slippers."),
        ],
        "questions": [
            {
                "q": "What kind of animal did I adopt?",
                "expect": [["greyhound"]],
                "needs": ["greyhound"],
            },
            {
                "q": "What is my dog called?",
                "expect": [["biscuit"]],
                "needs": ["biscuit"],
            },
            {
                "q": "What did my dog chew?",
                "expect": [["slipper"]],
                "needs": ["slipper"],
            },
        ],
    },
    {
        # control: typed facts; summaries must not add noise or stale values
        "id": "h_control_facts",
        "kind": "control",
        "messages": [
            (200, "My name is Elena and I live in Gdansk."),
            (190, "I work at a shipyard as a welder."),
            (60, "I'm allergic to shellfish."),
        ]
        + spread(H_FILLER[:4], 10, 180),
        "questions": [
            {"q": "What's my name?", "expect": [["elena"]], "needs": ["elena"]},
            {
                "q": "Which city do I live in?",
                "expect": [["gdansk"]],
                "needs": ["gdansk"],
            },
            {
                "q": "What do I do for a living?",
                "expect": [["welder"]],
                "needs": ["welder"],
            },
            {
                "q": "Can you suggest a dish for dinner at a restaurant?",
                "needs": ["shellfish"],
                "avoid": ["gdansk", "welder"],
            },
        ],
    },
    {
        # trap: third person. A summary must not turn a friend's trip into the user's
        "id": "h_third_person",
        "kind": "trap",
        "messages": [
            (60, "My friend Raul is travelling through Peru next month."),
            (55, "Raul sent me a photo of his hotel in Cusco."),
        ]
        + spread(H_FILLER[4:8], 10, 50),
        "questions": [
            {
                "q": "Where am I travelling next month?",
                "expect": [ABSTAIN],
                "avoid": ["peru", "cusco"],
            },
            {
                "q": "What's my brother's name?",
                "expect": [ABSTAIN],
                "avoid": ["raul"],
            },
        ],
    },
    {
        # trap: a plan that was cancelled. A summary must not keep it as live
        "id": "h_cancelled",
        "kind": "stale",
        "messages": [
            (100, "I'm going to the Lyon conference in May."),
            (60, "The Lyon conference got cancelled, so I'm not going after all."),
        ]
        + spread(H_FILLER[2:5], 10, 90),
        "questions": [
            {
                "q": "Am I going to the Lyon conference?",
                "expect": [["cancel", "not going"]],
                "needs": ["cancel"],
            },
        ],
    },
]

assert_no_leaks("H", H_FILLER, SCENARIOS)

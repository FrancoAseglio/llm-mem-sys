"""SET G: beyond the 13 fact types. 19 questions.

Status: BLIND. Written before any summaries code exists; run once on the current system
(step "baseline for G"), and once more after the summaries layer. Predictions are in
docs/predictions/set_G.md and were written before the first run.

Unlike sets A-F, many questions here are NOT answerable from the 13 typed facts:
episodes (a trip, a wedding), details of a project, a job-search story, questions about
the past, information that fits no type (a diet). The baseline (raw messages) may win on
those; that is what this set is for. Control questions check that nothing else breaks.
All people, places and topics are new; none appear in sets A-F.
"""

from .common import ABSTAIN, assert_no_leaks, spread

G_FILLER = [
    "How do volcanoes form?",
    "What's a good stretching routine for the morning?",
    "Why is the sky blue?",
    "How many moons does Jupiter have?",
    "What's a palindrome?",
    "How do I remove a coffee stain?",
    "Can you explain what inflation is?",
    "What's the tallest mountain in the world?",
]

SCENARIOS = [
    {
        # episode: a trip with a companion; no fact type fits
        "id": "g_trip",
        "kind": "episode",
        "messages": [
            (
                150,
                "Last spring I went hiking in Norway with my cousin Ingrid, "
                "and we saw the northern lights.",
            ),
        ]
        + spread(G_FILLER[:4], 20, 140),
        "questions": [
            {
                "q": "What trip did I tell you about?",
                "expect": [["norway"]],
                "needs": ["norway"],
            },
            {
                "q": "Who did I go hiking with?",
                "expect": [["ingrid"]],
                "needs": ["ingrid"],
            },
        ],
    },
    {
        # upcoming event with place and a task
        "id": "g_wedding",
        "kind": "episode",
        "messages": [
            (
                60,
                "My sister Marta is getting married in Lisbon this September, "
                "and I'm giving a speech.",
            ),
        ]
        + spread(G_FILLER[2:6], 5, 55),
        "questions": [
            {
                "q": "Where is my sister's wedding?",
                "expect": [["lisbon"]],
                "needs": ["lisbon"],
            },
            {
                "q": "What am I doing at the wedding?",
                "expect": [["speech"]],
                "needs": ["speech"],
            },
        ],
    },
    {
        # a diet fits no type: "I'm vegan" was filed as a hobby in a manual test
        "id": "g_diet_misfile",
        "kind": "misfile",
        "messages": [
            (120, "I'm vegan, so no dairy or eggs for me."),
            (90, "I play the cello in a small amateur orchestra."),
        ]
        + spread(G_FILLER[4:8], 10, 110),
        "questions": [
            {
                "q": "What are my hobbies?",
                "expect": [["cello"]],
                "needs": ["cello"],
                "avoid": ["vegan"],  # a diet must not appear as a hobby
            },
            {
                "q": "Can you suggest something for dinner?",
                "expect": [["vegan", "plant", "dairy"]],
                "needs": ["vegan"],
            },
        ],
    },
    {
        # the past: the old home is superseded; one control (now), one about the past
        "id": "g_past_home",
        "kind": "past",
        "messages": [
            (400, "I live in Porto."),
            (45, "I've just moved to Leeds for a new start."),
        ]
        + spread(G_FILLER[:3], 20, 300),
        "questions": [
            {
                "q": "Where do I live now?",
                "expect": [["leeds"]],
                "needs": ["leeds"],
                "stale": ["porto"],
            },
            {
                "q": "Where did I live before Leeds?",
                "expect": [["porto"]],
                "needs": ["porto"],
            },
        ],
    },
    {
        # a plan with a time frame; may or may not become a goal
        "id": "g_training",
        "kind": "plan",
        "messages": [
            (
                80,
                "I'm training for a half marathon in November, "
                "running three mornings a week.",
            ),
        ]
        + spread(G_FILLER[3:7], 10, 70),
        "questions": [
            {
                "q": "What am I training for?",
                "expect": [["marathon"]],
                "needs": ["marathon"],
            },
        ],
    },
    {
        # details of a work project: not a fact type
        "id": "g_project",
        "kind": "episode",
        "messages": [
            (110, "I work at Brightline Logistics."),
            (
                100,
                "At work I'm leading the move of our billing system to a new "
                "cloud provider, and the deadline is the end of March.",
            ),
        ]
        + spread(G_FILLER[1:5], 10, 90),
        "questions": [
            {
                "q": "What project am I leading at work?",
                "expect": [["billing"]],
                "needs": ["billing"],
            },
            {
                "q": "When is the deadline for it?",
                "expect": [["march"]],
                "needs": ["march"],
            },
        ],
    },
    {
        # a story over time: what a summary should capture
        "id": "g_jobsearch",
        "kind": "story",
        "messages": [
            (
                200,
                "I've started looking for a new job and sent applications to three firms.",
            ),
            (170, "I had an interview at Kestrel Analytics and it went okay."),
            (150, "Kestrel said no, they picked someone with more experience."),
            (120, "Second interview, this time at Orbital Freight."),
            (100, "Orbital Freight offered me the job and I accepted!"),
            (90, "I start at Orbital Freight next month."),
        ],
        "questions": [
            {
                "q": "How did my job search go?",
                "expect": [["orbital"]],
                "needs": ["orbital"],
            },
            {
                "q": "Which company turned me down?",
                "expect": [["kestrel"]],
                "needs": ["kestrel"],
            },
            {
                "q": "Where do I work?",
                "expect": [["orbital"]],
                "needs": ["orbital"],
            },
        ],
    },
    {
        # control: ordinary typed facts, as in sets A-F
        "id": "g_control_facts",
        "kind": "control",
        "messages": [
            (180, "My name is Tomas and I'm a baker."),
            (170, "I speak Czech and English."),
            (60, "I'm allergic to hazelnuts."),
        ]
        + spread(G_FILLER[2:6], 10, 160),
        "questions": [
            {"q": "What's my name?", "expect": [["tomas"]], "needs": ["tomas"]},
            {
                "q": "Which languages do I speak?",
                "expect": [["czech"]],
                "needs": ["czech"],
            },
            {
                "q": "Can you suggest a quick snack?",
                "needs": ["hazelnut"],
                "avoid": ["czech", "baker"],
            },
        ],
    },
    {
        # abstain: nothing here answers the questions; "dog" belongs to a neighbour
        "id": "g_abstain",
        "kind": "abstain",
        "messages": [
            (90, "My neighbour's dog barks every morning, it drives me crazy."),
            (80, "I bought a new desk lamp yesterday."),
        ]
        + spread(G_FILLER[4:8], 10, 70),
        "questions": [
            {"q": "Do I have any pets?", "expect": [ABSTAIN], "avoid": ["dog", "barks"]},
            {
                "q": "What's my favourite colour?",
                "expect": [ABSTAIN],
                "avoid": ["lamp", "dog"],
            },
        ],
    },
]

assert_no_leaks("G", G_FILLER, SCENARIOS)

"""SET A: the first 9 scenarios (10 questions).

Status: TUNING SET. The retrieval gate was tuned on these, so they can NOT validate it.
Covers: stale values, recency, multi-valued facts, noise, third-person and past-tense traps, abstain.
"""
from .common import ABSTAIN


SCENARIOS = [
    {
        "id": "move_city", "kind": "stale",
        "messages": [
            (200, "I live in Turin and I work at Acme as a software engineer."),
            (190, "Can you recommend a good book about building habits?"),
            (120, "Big news: I just moved to Milan!"),
            (60, "Thanks, that was really helpful."),
        ],
        "questions": [
            {"q": "Which city do I live in?", "expect": [["milan"]],
             "needs": ["milan"], "stale": ["turin"]},
        ],
    },
    {
        "id": "job_change", "kind": "stale",
        "messages": [
            (300, "I work at Acme as a software engineer."),
            (150, "The commute to the office is quite short, which is nice."),
            (40, "Exciting news, I just started a new job at Globex!"),
        ],
        "questions": [
            {"q": "Where do I work?", "expect": [["globex"]],
             "needs": ["globex"], "stale": ["acme"]},
        ],
    },
    {
        "id": "old_relevant", "kind": "recency",
        "messages": [
            (260, "I live in Milan and I work as a nurse."),
            (240, "What's a good way to learn Spanish?"),
            (200, "Can you explain how compound interest works?"),
            (160, "Thanks, that was helpful!"),
            (120, "I love hiking in the mountains."),
            (80, "What's the difference between a virus and a bacterium?"),
            (30, "Give me a tip for sleeping better."),
        ],
        "questions": [
            {"q": "Which city do I live in?", "expect": [["milan"]], "needs": ["milan"]},
            {"q": "What is my profession?", "expect": [["nurse"]], "needs": ["nurse"]},
        ],
    },
    {
        "id": "many_hobbies", "kind": "multi",
        "messages": [
            (150, "I love cycling, I go out every weekend."),
            (100, "I started climbing recently and it's great."),
            (50, "I've also taken up chess."),
        ],
        "questions": [
            {"q": "What are my hobbies?", "expect": [["cycling"], ["climbing"], ["chess"]],
             "needs": ["cycling", "climbing", "chess"]},
        ],
    },
    {
        "id": "dislike_noise", "kind": "noise",
        "messages": [
            (120, "I really dislike mushrooms, I can't stand the texture."),
            (100, "What's a good recipe for carbonara?"),
            (90, "Can you suggest a pasta sauce for tonight?"),
            (70, "How long should I boil spaghetti?"),
            (50, "Thanks, dinner was great!"),
        ],
        "questions": [
            {"q": "I'm cooking for myself tonight. Which ingredient should I leave out?",
             "expect": [["mushroom"]], "needs": ["mushroom"]},
        ],
    },
    {
        "id": "family", "kind": "basic",
        "messages": [
            (180, "My sister's name is Anna."),
            (90, "What's a nice gift for a birthday?"),
        ],
        "questions": [
            {"q": "What is my sister's name?", "expect": [["anna"]], "needs": ["anna"]},
        ],
    },
    {
        "id": "third_person_trap", "kind": "trap",
        "messages": [
            (200, "I live in Milan."),
            (100, "My sister Anna lives in Berlin and she's a doctor."),
        ],
        "questions": [
            {"q": "Which city do I live in?", "expect": [["milan"]],
             "needs": ["milan"], "stale": ["berlin"]},
        ],
    },
    {
        "id": "past_tense_trap", "kind": "trap",
        "messages": [
            (200, "I live in Milan."),
            (60, "I used to live in Turin when I was a student."),
        ],
        "questions": [
            {"q": "Which city do I live in?", "expect": [["milan"]],
             "needs": ["milan"], "stale": ["turin"]},
        ],
    },
    {
        "id": "unknown", "kind": "abstain",
        "messages": [
            (100, "I live in Milan."),
            (60, "What's a good recipe for carbonara?"),
        ],
        "questions": [
            {"q": "What is my favourite colour?", "expect": [ABSTAIN]},
        ],
    },
]

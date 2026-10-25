"""SET E: food/drug allergies, goals phrased differently, abstain questions. 12 questions.

Status: SPENT. Blind, written before the safety bypass and the goal-extraction change; run once.
Measures the safety gain and noise cost of letting allergies skip the floor, and goal extraction.
"""
from .common import ABSTAIN, assert_no_leaks, spread

# Filler written for E only.
E_FILLER = [
    "How do tides work?",
    "Can you explain what a black hole is?",
    "How do I fold a fitted sheet?",
    "What's the plot of Hamlet?",
    "How many players are on a rugby team?",
    "Why is the sky blue?",
    "How do I remove a coffee stain?",
    "Can you recommend a board game for four people?",
    "What's the difference between weather and climate?",
    "Thanks, that's exactly what I needed.",
]

E_FOOD_WORDS = ["sesame", "mushroom", "ghent", "carpenter"]
E_DRUG_WORDS = ["ibuprofen", "tallinn", "librarian"]
E_GOAL_WORDS = ["marathon", "japanese", "house"]

SCENARIOS = [
    {
        # food allergy + food dislike: vague food questions need the allergy, others must not get it
        "id": "e_food_profile", "kind": "safety",
        "messages": [(240, "I'm allergic to sesame seeds."),
                     (210, "I can't stand mushrooms."),
                     (180, "I live in Ghent."),
                     (150, "I work as a carpenter.")] + spread(E_FILLER[:8], 10, 140),
        "questions": [
            {"q": "What should I cook for dinner tonight?", "needs": ["sesame"],
             "avoid": ["ghent", "carpenter"]},
            {"q": "Any snack ideas for this afternoon?", "needs": ["sesame"],
             "avoid": ["ghent", "carpenter"]},
            {"q": "Where do I live?", "expect": [["ghent"]], "needs": ["ghent"],
             "avoid": ["sesame", "mushroom", "carpenter"]},
            {"q": "What do I do for work?", "expect": [["carpenter"]], "needs": ["carpenter"],
             "avoid": ["sesame", "mushroom", "ghent"]},
        ],
    },
    {
        # drug allergy: needed for a medical question, noise for a food question
        "id": "e_drug_profile", "kind": "safety",
        "messages": [(230, "I'm allergic to ibuprofen."),
                     (190, "I live in Tallinn."),
                     (160, "I'm a librarian.")] + spread(E_FILLER[2:10], 10, 150),
        "questions": [
            {"q": "I have a headache, what can I take?", "needs": ["ibuprofen"],
             "avoid": ["tallinn", "librarian"]},
            {"q": "What should I cook for dinner tonight?",
             "avoid": ["ibuprofen", "tallinn", "librarian"]},
            {"q": "Where do I live?", "expect": [["tallinn"]], "needs": ["tallinn"],
             "avoid": ["ibuprofen", "librarian"]},
            {"q": "What's my blood type?", "expect": [ABSTAIN], "avoid": E_DRUG_WORDS},
        ],
    },
    {
        # goals phrased differently from "I'm saving up to buy a small boat."
        "id": "e_goals", "kind": "goal",
        "messages": [(220, "I'm planning to run a marathon next spring."),
                     (170, "I want to learn Japanese."),
                     (120, "I'm putting money aside for a house.")] + spread(E_FILLER[:8], 10, 110),
        "questions": [
            {"q": "What am I training for?", "expect": [["marathon"]], "needs": ["marathon"],
             "avoid": ["japanese", "house"]},
            {"q": "Which language am I trying to learn?", "expect": [["japanese"]],
             "needs": ["japanese"], "avoid": ["marathon", "house"]},
            {"q": "What big purchase am I working towards?", "expect": [["house"]],
             "needs": ["house"], "avoid": ["marathon", "japanese"]},
            {"q": "What's my cat's name?", "expect": [ABSTAIN], "avoid": E_GOAL_WORDS},
        ],
    },
]

assert_no_leaks("E", E_FILLER, SCENARIOS, E_FOOD_WORDS + E_DRUG_WORDS + E_GOAL_WORDS)

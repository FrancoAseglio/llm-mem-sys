"""Test scenarios for the evaluation.

Each scenario replays a short life history, with messages dated N days ago,
then asks questions that can be answered from memory alone.

SET A  the first 10 questions. The retrieval gate was tuned on these, so they can NOT validate it.
SET B  held-out when written, but SPENT: the floor and window were chosen after looking at it.
SET D  BLIND, written before relation routing existed in the pipeline. RUN IT ONCE.
SET C  blind when written, now SPENT: written BEFORE the relative window was run on it. One user with a rich profile
       (12 facts) so many facts compete, plus abstain questions that test the floor.
SET E  BLIND, written before the safety bypass and the goal-extraction change. Measures the safety gain
       and noise cost of letting allergies skip the floor, and goal extraction. RUN IT ONCE.
SET F  BLIND, write path only: corrections, a hallucination-prone message, likes/dislikes flips and
       employer changes. Written after the write-path fixes, before running it. RUN IT ONCE.
       The stored facts (--verbose) are the main check; predictions in docs/predictions_write.md.

messages : (days_ago, text)  -- order does not matter, the runner sorts them
expect   : list of groups; every group needs at least one of its words in the ANSWER
           (leave out to skip answer scoring and only check retrieval)
needs    : words that must appear in the memory lines sent to the model
avoid    : words that must NOT appear in the memory lines (irrelevant noise)
stale    : outdated words, reported separately (they never fail an answer)
kind     : what the scenario is designed to test
"""

ABSTAIN = [
    "don't know", "do not know", "don't have", "do not have", "haven't told", "have not told",
    "haven't mentioned", "have not mentioned", "not mentioned", "didn't mention", "did not mention",
    "haven't shared", "have not shared", "not sure", "no information", "not aware", "don't recall",
    "no record", "can't say", "cannot say", "i'm not able", "unable to",
]

# Neutral filler: no word here is used in any "needs", "avoid" or "stale" list.
NEUTRAL = [
    "Can you explain how compound interest works?",
    "Thanks, that was helpful!",
    "What's the difference between a virus and a bacterium?",
    "Give me a tip for sleeping better.",
    "How do I convert Celsius to Fahrenheit?",
    "What's the capital of Australia?",
    "How does a refrigerator work?",
    "Any tips for staying focused while studying?",
    "Can you recommend a good podcast about history?",
    "What's a good way to learn the guitar?",
]
FOOD = [
    "What's a good way to cook rice?",
    "Can you suggest a vegetarian lasagna?",
    "How many calories are in a banana?",
    "How long should I bake bread?",
    "What's a quick breakfast idea?",
    "How do I make a good tomato sauce?",
]
NAMEY = [
    "What's a good name for a cat?",
    "How do I pronounce quinoa?",
    "Can you suggest names for a bakery?",
    "What does the name Sofia mean?",
    "Who painted the Mona Lisa?",
]
TURIN_CHATTER = [
    "Turin is lovely in autumn.",
    "The Turin derby was great last night.",
    "I had coffee in Turin city centre today.",
    "My favourite Turin bakery just closed down.",
    "Public transport in Turin is quite decent.",
    "I walked along the Po river in Turin.",
]


def spread(texts, newest, oldest):
    """Give each text a days_ago value, evenly spaced from `oldest` down to `newest`."""
    n = len(texts)
    if n == 1:
        return [(oldest, texts[0])]
    step = (oldest - newest) / (n - 1)
    return [(round(oldest - i * step), t) for i, t in enumerate(texts)]


SET_A = [
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

SET_B = [
    {
        "id": "b_indirect_dislike", "kind": "indirect",
        "messages": [(200, "I can't stand olives, the taste is awful.")]
                    + spread(FOOD + NEUTRAL[:2], 10, 190),
        "questions": [
            {"q": "I'm making a pizza for friends tonight. What toppings should I skip for myself?",
             "expect": [["olive"]], "needs": ["olive"]},
        ],
    },
    {
        "id": "b_food_allergy", "kind": "safety",
        "messages": [(220, "I'm allergic to peanuts.")] + spread(NEUTRAL[:8], 10, 200),
        "questions": [
            # no "expect": a good answer may simply suggest an apple, so only retrieval is checked
            {"q": "Can you suggest a quick snack for me?", "needs": ["peanut"]},
        ],
    },
    {
        "id": "b_drug_allergy_noise", "kind": "noise",
        "messages": [(150, "I'm allergic to penicillin.")] + spread(FOOD + NEUTRAL[:2], 10, 140),
        "questions": [
            {"q": "Can you suggest a dinner recipe for me?", "avoid": ["penicillin"]},
        ],
    },
    {
        "id": "b_paraphrase_job", "kind": "paraphrase",
        "messages": [(180, "I work as a pediatric nurse at the city hospital.")]
                    + spread(NEUTRAL[:8], 10, 170),
        "questions": [
            {"q": "What do I do for a living?", "expect": [["nurse"]], "needs": ["nurse"]},
        ],
    },
    {
        "id": "b_stale_flood", "kind": "flood",
        "messages": [(300, "I live in Turin.")] + spread(TURIN_CHATTER, 200, 290)
                    + [(60, "I moved to Rome last month!")],
        "questions": [
            {"q": "Which city do I live in?", "expect": [["rome"]],
             "needs": ["rome"], "stale": ["turin"]},
        ],
    },
    {
        "id": "b_precision", "kind": "noise",
        "messages": [(200, "I live in Rome, I'm a teacher and I love painting."),
                     (150, "I also speak Spanish.")] + spread(NEUTRAL[:7], 10, 140),
        "questions": [
            {"q": "Which languages do I speak?", "expect": [["spanish"]], "needs": ["spanish"],
             "avoid": ["rome", "teacher", "painting"]},
        ],
    },
    {
        "id": "b_correction", "kind": "correction",
        "messages": [(200, "I'm allergic to peanuts.")] + spread(NEUTRAL[:6], 40, 190)
                    + [(30, "Actually I was wrong earlier, I'm not allergic to peanuts, "
                            "I'm allergic to walnuts.")],
        "questions": [
            {"q": "Which nuts am I allergic to?", "expect": [["walnut"]],
             "needs": ["walnut"], "stale": ["peanut"]},
        ],
    },
    {
        "id": "b_name_recall", "kind": "noise",
        "messages": [(250, "My name is Franco.")] + spread(NAMEY + NEUTRAL[:3], 10, 240),
        "questions": [
            {"q": "What's my name?", "expect": [["franco"]], "needs": ["franco"]},
        ],
    },
]


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

RICH_WORDS = ["giulia", "bologna", "architect", "marco", "italian", "running", "photography",
              "shellfish", "coriander", "jazz", "sail", "luca"]


def _others(*keep):
    return [w for w in RICH_WORDS if w not in keep]


SET_C = [
    {
        "id": "c_rich_profile", "kind": "rich",
        "messages": RICH,
        "questions": [
            {"q": "What's my name?", "expect": [["giulia"]], "needs": ["giulia"],
             "avoid": _others("giulia", "bologna")},
            {"q": "Which city do I live in?", "expect": [["bologna"]], "needs": ["bologna"],
             "avoid": _others("bologna", "giulia")},
            {"q": "What do I do for work?", "expect": [["architect"]], "needs": ["architect"],
             "avoid": _others("architect")},
            {"q": "Who is my partner?", "expect": [["marco"]], "needs": ["marco"],
             "avoid": _others("marco")},
            {"q": "Which languages do I speak?", "expect": [["italian"], ["english"]],
             "needs": ["italian", "english"], "avoid": _others("italian")},
            {"q": "I'm booking a restaurant for tonight. What should I avoid eating?",
             "expect": [["shellfish"], ["coriander"]], "needs": ["shellfish", "coriander"],
             "avoid": _others("shellfish", "coriander")},
            {"q": "What's my brother called?", "expect": [["luca"]], "needs": ["luca"],
             "avoid": _others("luca")},
            {"q": "What kind of music do I like?", "expect": [["jazz"]], "needs": ["jazz"],
             "avoid": _others("jazz")},
            {"q": "What is my favourite colour?", "expect": [ABSTAIN], "avoid": RICH_WORDS},
            {"q": "What's my pet's name?", "expect": [ABSTAIN], "avoid": RICH_WORDS},
        ],
    },
    {
        "id": "c_double_move", "kind": "stale",
        "messages": [(300, "I live in Genoa."), (180, "I've just moved to Bologna."),
                     (60, "Big news, I'm now living in Verona!")] + spread(NEUTRAL[4:9], 20, 170),
        "questions": [
            {"q": "Which city do I live in?", "expect": [["verona"]], "needs": ["verona"],
             "stale": ["genoa", "bologna"]},
        ],
    },
    {
        "id": "c_new_job", "kind": "write-bug",
        "messages": [(200, "I work at Fabbrica Rossi as a designer."),
                     (30, "Exciting news, I just started a new position at Delta Labs!")],
        "questions": [
            {"q": "Where do I work?", "expect": [["delta"]], "needs": ["delta"],
             "stale": ["rossi"], "avoid": ["new position", "new job"]},
        ],
    },
]


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

D_WORDS = ["tomas", "lisbon", "pharmacist", "clinic", "ines", "portuguese", "english", "german",
           "guitar", "egg", "anchovies", "fado", "boat", "marta", "march", "cooking"]


def _d_others(*keep):
    return [w for w in D_WORDS if w not in keep]


SET_D = [
    {
        "id": "d_rich_profile", "kind": "rich",
        "messages": D_RICH,
        "questions": [
            {"q": "What's my name?", "expect": [["tomas"]], "needs": ["tomas"],
             "avoid": _d_others("tomas", "lisbon")},
            {"q": "Where do I live?", "expect": [["lisbon"]], "needs": ["lisbon"],
             "avoid": _d_others("lisbon", "tomas")},
            {"q": "What do I do for a living?", "expect": [["pharmacist"]], "needs": ["pharmacist"],
             "avoid": _d_others("pharmacist", "clinic")},
            {"q": "What's my wife's name?", "expect": [["ines"]], "needs": ["ines"],
             "avoid": _d_others("ines")},
            {"q": "Which languages do I speak?", "expect": [["portuguese"], ["english"], ["german"]],
             "needs": ["portuguese", "english", "german"],
             "avoid": _d_others("portuguese", "english", "german")},
            {"q": "I'm picking a cafe for breakfast tomorrow. What should I watch out for on the menu?",
             "expect": [["egg"]], "needs": ["egg"], "avoid": _d_others("egg")},
            {"q": "I'm making a pizza tonight. Which topping should I skip for myself?",
             "expect": [["anchovies", "anchovy"]], "needs": ["anchovies"],
             "avoid": _d_others("anchovies", "egg")},
            {"q": "What music would you put on for me?", "expect": [["fado"]], "needs": ["fado"],
             "avoid": _d_others("fado")},
            {"q": "What am I saving up for?", "expect": [["boat"]], "needs": ["boat"],
             "avoid": _d_others("boat")},
            {"q": "When is my birthday?", "expect": [["march"]], "needs": ["march"],
             "avoid": _d_others("march")},
            {"q": "What's my sister called?", "expect": [["marta"]], "needs": ["marta"],
             "avoid": _d_others("marta")},
            {"q": "What do I like doing in my free time?", "expect": [["guitar"], ["cooking"]],
             "needs": ["guitar", "cooking"], "avoid": _d_others("guitar", "cooking")},
            {"q": "What car do I drive?", "expect": [ABSTAIN], "avoid": D_WORDS},
            {"q": "What's my dog's name?", "expect": [ABSTAIN], "avoid": D_WORDS},
            {"q": "What's my mother's job?", "expect": [ABSTAIN], "avoid": D_WORDS},
        ],
    },
    {
        "id": "d_small_safety", "kind": "safety",
        "messages": [(220, "I have a serious gluten intolerance, I can't eat it at all."),
                     (200, "I live in Naples.")] + spread(NEUTRAL[:6], 10, 190),
        "questions": [
            {"q": "Can you suggest a quick lunch for me?", "needs": ["gluten"], "avoid": ["naples"]},
            {"q": "Which city am I based in?", "expect": [["naples"]], "needs": ["naples"],
             "avoid": ["gluten"]},
        ],
    },
    {
        "id": "d_job_switch", "kind": "stale",
        "messages": [(300, "I work at Bluefin Labs as a data analyst."),
                     (90, "I've left Bluefin and joined Harbor Bank as an accountant.")],
        "questions": [
            {"q": "Where do I work now?", "expect": [["harbor"]], "needs": ["harbor"],
             "stale": ["bluefin"]},
            {"q": "What's my job title?", "expect": [["accountant"]], "needs": ["accountant"],
             "stale": ["analyst"]},
        ],
    },
]

# ---- SET E ----
# Filler written for E only. The leak check below fails at import if any of it contains a tested word.
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

SET_E = [
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

# Leak check: filler must not contain any word that set E tests for.
_e_words = {w for sc in SET_E for q in sc["questions"]
            for w in q.get("needs", []) + q.get("avoid", []) + q.get("stale", [])
            if isinstance(w, str)} | set(E_FOOD_WORDS + E_DRUG_WORDS + E_GOAL_WORDS)
for _text in E_FILLER:
    _leaks = [w for w in _e_words if w in _text.lower()]
    assert not _leaks, f"set E filler {_text!r} contains tested words {_leaks}"

# ---- SET F ----
F_FILLER = E_FILLER[:4]

SET_F = [
    {
        # correction without the word "not"; expected: latex archived, pollen active
        "id": "f_correction_allergy", "kind": "correction",
        "messages": [(210, "I'm allergic to latex."),
                     (35, "Sorry, I mixed things up before: latex is fine for me, "
                          "it's pollen that I'm allergic to.")] + spread(F_FILLER, 10, 200),
        "questions": [
            {"q": "What am I allergic to?", "expect": [["pollen"]], "needs": ["pollen"],
             "stale": ["latex"]},
        ],
    },
    {
        # "no longer" correction on a multi-valued relation; expected: chess archived, pottery active
        "id": "f_no_longer_hobby", "kind": "correction",
        "messages": [(190, "I play chess most evenings."),
                     (25, "I don't play chess anymore; these days my hobby is pottery.")]
                    + spread(F_FILLER, 10, 180),
        "questions": [
            {"q": "What are my hobbies?", "expect": [["pottery"]], "needs": ["pottery"],
             "stale": ["chess"]},
        ],
    },
    {
        # hallucination-prone: no new title is stated; expected: teacher stays, nothing invented
        "id": "f_vague_promotion", "kind": "hallucination",
        "messages": [(200, "I work at Hillside School as a teacher."),
                     (20, "Big day today, I finally got the promotion I'd been chasing!")],
        "questions": [
            {"q": "Where do I work?", "expect": [["hillside"]], "needs": ["hillside"],
             "avoid": ["promot", "manager", "senior"]},
            {"q": "What's my job title?", "avoid": ["promot", "manager", "senior"]},
        ],
    },
    {
        # likes -> dislikes; expected: likes superseded by dislikes (contradiction)
        "id": "f_like_to_dislike", "kind": "contradiction",
        "messages": [(180, "I love spicy food."),
                     (30, "I've gone right off spicy food, I can't stand it these days.")],
        "questions": [
            {"q": "What kind of food do I enjoy?", "avoid": ["spicy"]},
        ],
    },
    {
        # dislikes -> likes; expected: dislikes superseded by likes (contradiction)
        "id": "f_dislike_to_like", "kind": "contradiction",
        "messages": [(200, "I can't stand opera."),
                     (40, "Funny thing, I've grown to really love opera lately.")],
        "questions": [
            {"q": "What music do I like?", "expect": [["opera"]], "needs": ["opera"]},
        ],
    },
    {
        # employer change, no title; expected: nurse conflicted, so the title question gets nothing
        "id": "f_employer_no_title", "kind": "conflicted",
        "messages": [(240, "I'm a nurse at Saint Mary's Hospital."),
                     (30, "I switched employers, I'm at Riverside Clinic now.")],
        "questions": [
            {"q": "Where do I work?", "expect": [["riverside"]], "needs": ["riverside"],
             "stale": ["mary"]},
            {"q": "What's my job title?", "avoid": ["nurse"]},  # by design: conflicted
        ],
    },
    {
        # employer change with a title; expected: both superseded, nothing conflicted
        "id": "f_employer_with_title", "kind": "stale",
        "messages": [(260, "I work at Northwind as a sales rep."),
                     (45, "I left Northwind and I'm now a product manager at Contoso.")],
        "questions": [
            {"q": "Where do I work?", "expect": [["contoso"]], "needs": ["contoso"],
             "stale": ["northwind"]},
            {"q": "What's my job title?", "expect": [["product manager"]],
             "needs": ["product manager"], "stale": ["sales"]},
        ],
    },
]

# Leak check: F filler must not contain any word that set F tests for.
_f_words = {w for sc in SET_F for q in sc["questions"]
            for w in q.get("needs", []) + q.get("avoid", []) + q.get("stale", [])}
for _text in F_FILLER:
    _leaks = [w for w in _f_words if w in _text.lower()]
    assert not _leaks, f"set F filler {_text!r} contains tested words {_leaks}"

for _s in SET_A:
    _s["set"] = "A"
for _s in SET_B:
    _s["set"] = "B"
for _s in SET_C:
    _s["set"] = "C"
for _s in SET_D:
    _s["set"] = "D"
for _s in SET_E:
    _s["set"] = "E"
for _s in SET_F:
    _s["set"] = "F"

SCENARIOS = SET_A + SET_B + SET_C + SET_D + SET_E + SET_F

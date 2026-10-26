"""Shared building blocks for the scenario sets: filler messages, the abstain phrases, helpers."""

ABSTAIN = [
    "don't know",
    "do not know",
    "don't have",
    "do not have",
    "haven't told",
    "have not told",
    "haven't mentioned",
    "have not mentioned",
    "not mentioned",
    "didn't mention",
    "did not mention",
    "haven't shared",
    "have not shared",
    "not sure",
    "no information",
    "not aware",
    "don't recall",
    "no record",
    "can't say",
    "cannot say",
    "i'm not able",
    "unable to",
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


def assert_no_leaks(set_name, filler, scenarios, extra_words=()):
    """Fail at import if any filler message contains a word that the set tests for.

    A leaked word would make a filler message look like the needed fact (or like noise),
    which silently corrupts the measurement.
    """
    tested = {
        w
        for sc in scenarios
        for q in sc["questions"]
        for w in q.get("needs", []) + q.get("avoid", []) + q.get("stale", [])
        if isinstance(w, str)
    } | set(extra_words)
    for text in filler:
        leaks = [w for w in tested if w in text.lower()]
        assert not leaks, (
            f"set {set_name} filler {text!r} contains tested words {leaks}"
        )

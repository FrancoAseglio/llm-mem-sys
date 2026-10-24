"""Feed a small life story into the memory and show what it stored.

Run from the memory-system folder:
    poetry run python scripts/demo_ingest.py
"""
from memory_system.db import get_pool
from memory_system.manager import ingest_user_message, list_facts

USER = "demo"

TURNS = [
    "I live in Turin and I work at Acme as a software engineer.",
    "I love cycling and I'm allergic to penicillin.",
    "Thanks, that was really helpful!",
    "What's a good recipe for carbonara?",
    "Big news: I just moved to Milan!",
    "I also enjoy climbing these days.",
    "I really love cycling, it's my main hobby.",
]

with get_pool().connection() as conn:
    conn.execute("DELETE FROM users WHERE id = %s", (USER,))  # start clean (cascades)

for text in TURNS:
    print(f"\n> {text}")
    results = ingest_user_message(USER, text)
    if not results:
        print("   (nothing durable)")
    for outcome, relation, value in results:
        print(f"   {outcome.upper():<9} {relation} = {value}")

print("\n=== Facts in memory ===")
print(f"{'relation':<14}{'value':<18}{'status':<12}{'imp':<6}{'conf':<6}valid_from")
for relation, value, status, imp, conf, valid_from in list_facts(USER):
    print(f"{relation:<14}{value:<18}{status:<12}{imp:<6.2f}{conf:<6.2f}{valid_from}")

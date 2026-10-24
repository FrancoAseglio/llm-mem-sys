"""Ask one question with no memory, baseline vector memory, and smart memory.

    poetry run python scripts/compare.py "What's the weather like where I live?" --user demo
"""
import argparse

from memory_system.assistant import build_messages, format_memory, recall
from memory_system.llm import chat
from memory_system.retrieve import retrieve

parser = argparse.ArgumentParser()
parser.add_argument("question")
parser.add_argument("--user", default="demo")
parser.add_argument("--k", type=int, default=4)
args = parser.parse_args()

smart = retrieve(args.user, args.question, args.k, touch=False)
contexts = {
    "none": [],
    "baseline": recall("baseline", args.user, args.question, args.k),
    "smart": [format_memory(m) for m in smart],
}

for mode, lines in contexts.items():
    print(f"\n{'=' * 70}\n{mode.upper()} MEMORY\n{'=' * 70}")
    for line in lines:
        print(f"  recalled: {line}")
    answer = chat(build_messages(mode, lines, [], args.question), temperature=0)
    print(f"\n{answer}")

print(f"\n{'-' * 70}\nSmart-memory score breakdown (for tuning)")
for m in smart:
    parts = " ".join(f"{k[:3]}={v:.2f}" for k, v in m.parts.items())
    print(f"  {m.score:.2f}  {m.relation}={m.value}  {'[pinned] ' if m.pinned else ''}{parts}")

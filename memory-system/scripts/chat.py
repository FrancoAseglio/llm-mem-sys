"""Interactive chat with long-term memory.

    poetry run python scripts/chat.py --user franco --mode smart

Commands: /mode smart|baseline|none   /facts   /quit
"""

import argparse

from memory_system.assistant import build_messages, recall
from memory_system.core.config import SUMMARIES, SUMMARY_EVERY
from memory_system.core.llm import chat_stream
from memory_system.summaries.consolidate import consolidate
from memory_system.summaries.summarize import pending_count, summarize_pending
from memory_system.write.manager import ingest_user_message, list_facts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="me")
    parser.add_argument(
        "--mode", choices=["smart", "baseline", "none"], default="smart"
    )
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument(
        "--quiet", action="store_true", help="hide recall/memory debug lines"
    )
    args = parser.parse_args()

    mode, history = args.mode, []
    print(f"user={args.user} mode={mode}  (/mode, /facts, /quit)")

    while True:
        try:
            text = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text == "/quit":
            break
        if text.startswith("/mode"):
            new = text.split()[-1]
            if new in ("smart", "baseline", "none"):
                mode = new
                print(f"mode -> {mode}")
            continue
        if text == "/facts":
            for relation, value, status, imp, conf, since in list_facts(args.user):
                print(
                    f"  {relation:<14}{value:<20}{status:<12}imp={imp:.2f} conf={conf:.2f}  {since}"
                )
            continue

        lines = recall(mode, args.user, text, args.k)
        if lines and not args.quiet:
            print("  [recalled]")

            for line in lines:
                print(f"    - {line}")

        print("assistant> ", end="", flush=True)
        reply = ""

        for token in chat_stream(build_messages(mode, lines, history[-6:], text)):
            print(token, end="", flush=True)
            reply += token

        print()
        history += [
            {"role": "user", "content": text},
            {"role": "assistant", "content": reply},
        ]

        for outcome, relation, value in ingest_user_message(args.user, text):
            if not args.quiet:
                print(f"  [memory] {outcome.upper()} {relation} = {value}")

        if SUMMARIES and pending_count(args.user) >= SUMMARY_EVERY:
            for note in summarize_pending(args.user):
                if not args.quiet:
                    print(f"  [summary] {note}")
            for digest in consolidate(args.user):
                if not args.quiet:
                    print(f"  [digest] {digest}")


if __name__ == "__main__":
    main()

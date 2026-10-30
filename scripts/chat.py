"""Interactive chat with long-term memory.

    poetry run python scripts/chat.py --user franco --mode smart

Commands: /mode smart|hybrid|baseline|none   /facts   /quit
(The full reference mode is for the evaluation only.)
"""

import argparse

from memory_system.assistant import build_messages, recall
from memory_system.core.config import SUMMARIES, SUMMARY_EVERY
from memory_system.core.llm import chat_stream
from memory_system.core.style import (
    OUTCOME_STYLE,
    STATUS_STYLE,
    memory_line,
    paint,
    set_enabled,
)
from memory_system.summaries.consolidate import consolidate
from memory_system.summaries.summarize import pending_count, summarize_pending
from memory_system.write.manager import ingest_user_message, list_facts

CHAT_MODES = ["smart", "hybrid", "baseline", "none"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", default="me")
    parser.add_argument("--mode", choices=CHAT_MODES, default="smart")
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument(
        "--quiet", action="store_true", help="hide recall/memory debug lines"
    )
    parser.add_argument(
        "--no-color", action="store_true", help="plain text (also: NO_COLOR=1)"
    )
    args = parser.parse_args()
    if args.no_color:
        set_enabled(False)

    mode, history = args.mode, []
    print(
        paint(f"user={args.user} mode={mode}", "bold"),
        paint(" (/mode, /facts, /quit)", "dim"),
        sep="",
    )

    while True:
        try:
            text = input("\n" + paint("you> ", "bold", "cyan")).strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text == "/quit":
            break
        if text.startswith("/mode"):
            new = text.split()[-1]
            if new in CHAT_MODES:
                mode = new
                print(paint(f"mode -> {mode}", "bold"))
            continue
        if text == "/facts":
            for relation, value, status, imp, conf, since in list_facts(args.user):
                print(
                    f"  {relation:<14}{value:<20}"
                    + paint(f"{status:<12}", STATUS_STYLE.get(status, "dim"))
                    + paint(f"imp={imp:.2f} conf={conf:.2f}  {since}", "dim")
                )
            continue

        lines = recall(mode, args.user, text, args.k)
        if lines and not args.quiet:
            print(paint("  [recalled]", "dim"))
            for line in lines:
                print(f"    - {memory_line(line)}")

        print(paint("assistant> ", "bold"), end="", flush=True)
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
                style = OUTCOME_STYLE.get(outcome, "dim")
                print(
                    paint(f"  [memory] {outcome.upper()}", style),
                    f"{relation} = {value}",
                )

        if SUMMARIES and pending_count(args.user) >= SUMMARY_EVERY:
            for note in summarize_pending(args.user):
                if not args.quiet:
                    print(paint("  [summary]", "blue"), note)
            for digest in consolidate(args.user):
                if not args.quiet:
                    print(paint("  [digest]", "blue", "bold"), digest)


if __name__ == "__main__":
    main()

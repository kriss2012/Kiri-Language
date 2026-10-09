#!/usr/bin/env python3

import argparse
import sys

from kiri import run_source


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Kiri-Language programs.")
    parser.add_argument("file", nargs="?", help="Path to a .kiri source file.")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as handle:
            source = handle.read()
        output = run_source(source)
        if output:
            print(output)
        return 0

    print("Kiri-Language REPL")
    print("Type 'exit' or Ctrl-D to quit.")
    while True:
        try:
            user_input = input("kiri> ")
        except EOFError:
            print()
            break
        if user_input.strip().lower() in {"exit", "quit"}:
            break
        if not user_input.strip():
            continue
        try:
            output = run_source(user_input)
            if output:
                print(output)
        except Exception as exc:  # pragma: no cover - CLI safety
            print(f"Error: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

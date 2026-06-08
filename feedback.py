#!/usr/bin/env python3
"""Feedback CLI — teach the rules engine from natural language.

Usage:
  python feedback.py "sun was too big in scene 5"
  python feedback.py "house draws as oval — use building instead" --type house
  python feedback.py "too many elements, scene was cluttered"
  python feedback.py --show          # show all current rules
  python feedback.py --log           # show feedback history
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(__file__))
from src.rules_engine import RulesEngine, RULES_PATH

def main():
    parser = argparse.ArgumentParser(description="Teach the rules engine from feedback")
    parser.add_argument("text", nargs="?", help="Feedback text")
    parser.add_argument("--type", "-t", help="Element type the feedback is about")
    parser.add_argument("--show", action="store_true", help="Show current rules")
    parser.add_argument("--log", action="store_true", help="Show feedback history")
    args = parser.parse_args()

    engine = RulesEngine()

    if args.show:
        print(json.dumps(engine.rules, indent=2, ensure_ascii=False))
        return

    if args.log:
        for i, entry in enumerate(engine.rules.get("feedback_log", [])):
            print(f"{i}: [{entry.get('element_type','?')}] {entry['text']} → {entry.get('action','?')}")
        return

    if not args.text:
        parser.print_help()
        return

    action = engine.process_feedback(args.text, args.type)
    print(f"[OK] {action}" if action else "[--] No action taken")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
agentlog — Persistent decision memory for any project.
Karpathy's LLM Wiki concept, shipped as a CLI.

Three commands:
  remember  — Store a decision, rationale, or context
  recall    — Retrieve relevant past decisions using natural language
  reflect   — Synthesize patterns across all stored decisions

Usage:
  python agentlog.py remember "Chose DynamoDB over Postgres for session store — need <10ms at 10K RPS"
  python agentlog.py remember "$(llm 'Summarize the database decision made here' < meeting-notes.txt)"
  python agentlog.py recall "database choices"
  python agentlog.py reflect
  python agentlog.py recall "database choices" --model gemini  # use Gemini instead
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# --- Configuration ---

__version__ = "0.1.0"

AGENTLOG_DIR = Path(os.environ.get("AGENTLOG_DIR", ".agentlog"))
DECISIONS_FILE = AGENTLOG_DIR / "decisions.jsonl"
REFLECTIONS_FILE = AGENTLOG_DIR / "reflections.md"
DEFAULT_PROVIDER = os.environ.get("AGENTLOG_PROVIDER", "anthropic")  # "anthropic" or "gemini"


def get_client(provider: str = None):
    """Get the appropriate LLM client based on provider."""
    provider = provider or DEFAULT_PROVIDER

    if provider == "gemini":
        try:
            import google.generativeai as genai
        except ImportError:
            print("Install google-generativeai: pip install google-generativeai")
            sys.exit(1)
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")
            sys.exit(1)
        genai.configure(api_key=api_key)
        return ("gemini", genai)

    else:  # anthropic
        try:
            import anthropic
        except ImportError:
            print("Install anthropic: pip install anthropic")
            sys.exit(1)
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("Set ANTHROPIC_API_KEY environment variable.")
            sys.exit(1)
        return ("anthropic", anthropic.Anthropic())


def llm_call(prompt: str, system: str = "", provider: str = None) -> str:
    """Make a single LLM call. Supports Anthropic and Gemini."""
    provider_name, client = get_client(provider)

    if provider_name == "gemini":
        model = client.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=system if system else None,
        )
        response = model.generate_content(prompt)
        return response.text

    else:  # anthropic
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


# --- Storage (JSONL — one decision per line, grep-friendly) ---


def init_storage():
    """Create the .agentlog directory if it doesn't exist."""
    AGENTLOG_DIR.mkdir(exist_ok=True)
    if not DECISIONS_FILE.exists():
        DECISIONS_FILE.touch()


def store_decision(text: str, tags: list[str] | None = None):
    """Append a decision to the log."""
    entry = {
        "id": datetime.now().strftime("%Y%m%d-%H%M%S"),
        "timestamp": datetime.now().isoformat(),
        "text": text,
        "tags": tags or [],
    }
    with open(DECISIONS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def load_decisions() -> list[dict]:
    """Load all decisions from the log."""
    if not DECISIONS_FILE.exists():
        return []
    decisions = []
    with open(DECISIONS_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                decisions.append(json.loads(line))
    return decisions


# --- Commands ---


def cmd_remember(text: str, tags: list[str] | None = None, provider: str = None):
    """Store a decision with optional auto-tagging."""
    init_storage()

    # Auto-tag using LLM if no tags provided
    if not tags:
        try:
            tag_response = llm_call(
                prompt=f'Given this decision or context, suggest 2-3 short tags (single words, lowercase). Return ONLY a comma-separated list, nothing else.\n\nDecision: "{text}"',
                system="You are a concise tagging assistant. Return only comma-separated lowercase tags.",
                provider=provider,
            )
            tags = [t.strip().lower() for t in tag_response.split(",") if t.strip()]
        except Exception:
            tags = []  # Fail silently — tags are nice-to-have

    entry = store_decision(text, tags)
    print(f"✓ Remembered [{entry['id']}]")
    if tags:
        print(f"  Tags: {', '.join(tags)}")
    print(f"  Stored in {DECISIONS_FILE}")


def cmd_recall(query: str, provider: str = None):
    """Retrieve relevant past decisions using natural language."""
    init_storage()
    decisions = load_decisions()

    if not decisions:
        print("No decisions stored yet. Use 'remember' to add some.")
        return

    # Format all decisions for context
    context = "\n".join(
        f"[{d['id']}] ({d['timestamp'][:10]}) {d['text']} [tags: {', '.join(d['tags'])}]"
        for d in decisions
    )

    response = llm_call(
        prompt=f'Here are all stored decisions:\n\n{context}\n\nQuery: "{query}"\n\nReturn the most relevant decisions and explain how they connect to the query. Be concise. If decisions contradict each other, note the evolution in thinking.',
        system="You are a decision memory retrieval system. Surface relevant past decisions and explain their relevance. Be direct and concise. Group related decisions together.",
        provider=provider,
    )

    print(f"\n— Recall: {query} —\n")
    print(response)
    print(f"\n({len(decisions)} total decisions searched)")


def cmd_reflect(provider: str = None):
    """Synthesize patterns across all stored decisions."""
    init_storage()
    decisions = load_decisions()

    if len(decisions) < 3:
        print(f"Only {len(decisions)} decisions stored. Add a few more for meaningful reflection.")
        return

    context = "\n".join(
        f"[{d['id']}] ({d['timestamp'][:10]}) {d['text']}"
        for d in decisions
    )

    response = llm_call(
        prompt=f"Here are all stored decisions:\n\n{context}\n\nAnalyze these decisions and identify:\n1. Recurring themes or principles (what values keep showing up?)\n2. Contradictions or evolving thinking (where did you change your mind?)\n3. Gaps (what important areas have no recorded decisions?)\n4. One insight that only emerges when you see all decisions together.\n\nBe specific and reference actual decisions by ID.",
        system="You are a strategic reflection assistant. Find patterns that aren't obvious from any single decision. Be insightful, not generic. Reference specific decisions.",
        provider=provider,
    )

    # Save reflection to file
    reflection_entry = f"\n## Reflection — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{response}\n"

    with open(REFLECTIONS_FILE, "a") as f:
        f.write(reflection_entry)

    print("\n— Reflection —\n")
    print(response)
    print(f"\n(Saved to {REFLECTIONS_FILE})")


def cmd_log():
    """Print the raw decision log."""
    init_storage()
    decisions = load_decisions()

    if not decisions:
        print("No decisions stored yet.")
        return

    print(f"\n— Decision Log ({len(decisions)} entries) —\n")
    for d in decisions:
        tags = f" [{', '.join(d['tags'])}]" if d.get("tags") else ""
        print(f"  {d['id']}  {d['timestamp'][:10]}  {d['text']}{tags}")


# --- CLI ---


def main():
    parser = argparse.ArgumentParser(
        description="agentlog — Persistent decision memory for any project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agentlog remember "Chose DynamoDB over Postgres — need <10ms latency at 10K RPS"
  agentlog remember "$(llm 'Summarize the database decision made here' < meeting-notes.txt)"
  agentlog remember "Shipping eval suite before GA — learned from last launch" --tags launch,evals
  agentlog recall "database choices"
  agentlog recall "what did we decide about the API?" --model gemini
  agentlog reflect
  agentlog log
        """,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # remember
    p_remember = sub.add_parser("remember", help="Store a decision or context")
    p_remember.add_argument("text", help="The decision or context to store")
    p_remember.add_argument("--tags", help="Comma-separated tags (auto-generated if omitted)")
    p_remember.add_argument("--model", choices=["anthropic", "gemini"], help="LLM provider")

    # recall
    p_recall = sub.add_parser("recall", help="Retrieve relevant past decisions")
    p_recall.add_argument("query", help="Natural language query")
    p_recall.add_argument("--model", choices=["anthropic", "gemini"], help="LLM provider")

    # reflect
    p_reflect = sub.add_parser("reflect", help="Synthesize patterns across all decisions")
    p_reflect.add_argument("--model", choices=["anthropic", "gemini"], help="LLM provider")

    # log
    sub.add_parser("log", help="Print the raw decision log")

    args = parser.parse_args()

    if args.command == "remember":
        tags = [t.strip() for t in args.tags.split(",")] if args.tags else None
        cmd_remember(args.text, tags=tags, provider=args.model)
    elif args.command == "recall":
        cmd_recall(args.query, provider=args.model)
    elif args.command == "reflect":
        cmd_reflect(provider=args.model)
    elif args.command == "log":
        cmd_log()


if __name__ == "__main__":
    main()

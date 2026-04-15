# agentlog

**Persistent decision memory for any project.** Three commands. One file. Zero frameworks.

Inspired by [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — which proved that the best knowledge system is just well-structured text that an LLM maintains for you. This is that idea, shipped as a CLI you can install in 30 seconds.

## The problem

Every team has a "why did we decide this?" problem. Decisions live in Slack threads, Google Docs, people's heads, and nowhere useful. Six months later, you're re-litigating the same trade-off because no one remembers the reasoning.

## The fix

```bash
# Store a decision directly
agentlog remember "Chose DynamoDB over Postgres for session store — need <10ms at 10K RPS"

# Or use AI to summarize a decision from a file (e.g., using Simon Willison's 'llm' CLI)
agentlog remember "$(llm 'Summarize the key architectural decision made here' < meeting-notes.txt)"

# Retrieve relevant decisions
agentlog recall "database choices"

# Synthesize patterns across all decisions
agentlog reflect
```

That's it. Decisions are stored as JSONL (one per line, grep-friendly, version-controllable). Retrieval and reflection use Claude or Gemini to find relevant context and surface patterns.

## Install

```bash
pip install anthropic  # or: pip install google-generativeai
export ANTHROPIC_API_KEY="sk-..."  # or: export GEMINI_API_KEY="..."

git clone https://github.com/RyanAlberts/agentlog.git
cd agentlog
python agentlog.py remember "First decision logged"
```

Or add it to any existing project:
```bash
cp agentlog.py your-project/
cd your-project
python agentlog.py remember "Starting the decision log for this project"
```

## How it works

`remember` stores a decision as a JSON line with auto-generated tags:
```json
{"id": "20260415-213045", "timestamp": "2026-04-15T21:30:45", "text": "Chose DynamoDB over Postgres...", "tags": ["database", "performance", "infrastructure"]}
```

`recall` sends your query + all decisions to Claude (or Gemini) and gets back the relevant context with connections explained.

`reflect` asks Claude to find patterns, contradictions, and gaps across your entire decision history. Reflections are saved to `.agentlog/reflections.md` so they accumulate over time.

## Multi-model support

Defaults to Claude (Anthropic). Switch to Gemini per-command:

```bash
agentlog recall "API design patterns" --model gemini
```

Or set a default:
```bash
export AGENTLOG_PROVIDER=gemini
```

## Design philosophy

Read [DECISIONS.md](./DECISIONS.md) for the full rationale. The short version:

- **One file, not a framework.** 200 lines of Python. Read the whole thing in 5 minutes.
- **JSONL, not a database.** Grep-friendly, git-friendly, LLM-friendly.
- **Three commands, not ten.** Remember, recall, reflect. That's the whole API surface.
- **The LLM does the heavy lifting.** No embeddings, no vector DB, no RAG pipeline. The model reads all your decisions and finds the relevant ones. This works up to ~500 decisions before you'd need to add chunking.

## Inspired by

- [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) by Andrej Karpathy — the idea that LLMs should maintain your knowledge base
- [gbrain](https://github.com/garrytan/gbrain) by Garry Tan — persistent memory for Claude Code projects
- [Simon Willison's llm](https://github.com/simonw/llm) — proof that single-purpose CLI tools for LLMs are underrated

---

Built by [Ryan](https://linkedin.com/in/YOUR_PROFILE) — Staff PM working in Agentic AI.

# Decisions

This tool is a product decision in itself. Here's the thinking behind every choice.

## Why "decisions" and not "notes" or "knowledge"?

Karpathy's LLM Wiki is general-purpose — it tracks anything. I deliberately narrowed the scope to decisions because:

1. **Decisions have the highest retrieval value.** You rarely need to recall a fact — you can Google it. You constantly need to recall *why you chose X over Y* — that reasoning is trapped in someone's head.
2. **Decisions are structured by nature.** They have a choice, alternatives, a rationale, and a context. This makes them easier for an LLM to organize and retrieve.
3. **Decisions compound.** Early decisions constrain later ones. The `reflect` command exists to surface these chains — "you chose DynamoDB in January, and that's why you're now stuck with single-table design."

A general-purpose "remember anything" tool sounds more useful but is actually less valuable. Focus is the product.

## Why three commands, not more?

I started with six: remember, recall, reflect, forget, search, export. Then I asked: which of these can I not live without? The answer was three.

- `forget` was cut because decisions shouldn't be deleted — they should be superseded. If you changed your mind, `remember` the new decision. The `reflect` command will surface the contradiction.
- `search` was cut because `recall` already does natural language search. A separate keyword search adds cognitive overhead without adding capability.
- `export` was cut because the storage format (JSONL) is already the export format. `cat .agentlog/decisions.jsonl` is your export.

## Why JSONL, not SQLite or markdown?

Three properties matter for this use case:

1. **Append-only writes** — JSONL is append-only by nature. No write conflicts, no corruption risk, no WAL to manage.
2. **Git-friendly** — each decision is one line. `git diff` shows exactly what was added. `git blame` shows when. Try that with SQLite.
3. **LLM-friendly** — the entire file can be dropped into a prompt. No serialization needed. At ~200 bytes per decision, you can fit ~500 decisions in a 100K context window with room for the response.

The trade-off: no indexing, no relational queries, linear scan for every recall. This stops working at ~1000 decisions. That's a fine problem to solve later — most projects generate 2-5 decisions per week, so you get 4+ years before this matters.

## Why Claude and Gemini, not OpenAI?

I picked two providers that represent different strengths:
- **Claude** (default): Best at nuanced reasoning and finding non-obvious connections between decisions. The `reflect` command benefits most from this.
- **Gemini**: Fastest and cheapest for simple recall queries. Good default for teams that want low latency.

OpenAI is conspicuously absent. This is a deliberate choice — I wanted to show fluency with the providers I'd actually use at Anthropic or Databricks, not hedge with the incumbent.

## Why no embeddings or vector search?

The current approach — dump all decisions into context and let the LLM find what's relevant — is "dumb" by RAG standards. It's also simpler, cheaper to build, and surprisingly effective up to ~500 decisions.

Vector search solves the *retrieval* problem but introduces three new problems:
1. Embedding model choice and maintenance
2. A vector DB dependency (Chroma, Pinecone, etc.)
3. The "semantic search misses context" problem — embeddings find similar text, not related reasoning

For this tool's scope (project-level decisions, not enterprise knowledge), brute-force context is the right call. When it stops working, the upgrade path is clear: add embeddings as a pre-filter, keep the LLM for reasoning over the filtered set.

## What I'd add next

1. **Team mode** — `agentlog remember --author ryan` to attribute decisions in shared projects
2. **Decision linking** — `agentlog remember "Switched to WebSockets" --supersedes 20260415-213045` to create explicit chains
3. **CI integration** — a GitHub Action that runs `agentlog reflect` weekly and posts the summary to a Slack channel
4. **MCP server** — expose agentlog as an MCP tool so Claude Code can recall decisions mid-conversation

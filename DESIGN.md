# DESIGN.md — Vault Agent (Team 22)

*One page. What we taught it, what it still gets wrong, what we'd want next. Update this throughout the four weeks — this is not a one-time doc.*

## What we taught it

- To only cite notes it actually used, after finding that AgentSwitch's own "Ask Vault" lists topically unrelated notes as "authorized sources" even on refused questions (filed as a bug, submitted 2026-09-21).
- To refuse rather than guess when no relevant note exists.
- To scan retrieved note content for embedded-instruction patterns and flag (never obey) them.
- To filter cited sources by actual topical relevance rather than a single fixed threshold — and, in the process of building this, we reproduced the exact bug class we'd just reported in AgentSwitch. Our first working version matched "What do we know about Bharat EV?" correctly, but "What's our marketing budget for next year?" pulled in 8 unrelated notes, all matched via generic words ("what", "know", "about", then later "year", "next") that recur across unrelated notes but carry no topical meaning. We fixed it with two layers: a fixed stopword list for grammar words and explicit generic temporal/quantity terms (year, next, month, cost...), plus a corpus-adaptive filter that excludes any word appearing in more than 12% of the vault's notes — since a fixed list can't anticipate every domain-specific filler word (e.g. "despatch", "shortage" in this vault). Verified against live Suryodaya data: correct multi-note synthesis for Bharat EV, correct refusal for the marketing-budget question, after iterating through the false-positive case.

## What it still gets wrong / is unfinished

- `VaultAgent.answer()` currently does placeholder synthesis (a join of note snippets), not real LLM-backed reasoning — needs to be wired to an actual model call for genuine multi-hop synthesis (e.g. explaining the Bharat EV → battery tray → yield/cost chain in prose, not just concatenated excerpts).
- The relevance filter is still pure keyword overlap (now with stopword + corpus-frequency filtering) — it will miss genuinely relevant notes that use different wording (paraphrase, synonyms) and has only been validated against two manual test cases so far. Needs broader testing across more of the seat's real questions before we trust it.
- Injection-detection patterns are a fixed regex list — not yet tested against a real embedded-instruction note planted in the live vault (see `tests/test_injection.py` stubs, still unwritten).
- The corpus-adaptive stopword threshold (12%) was tuned against one failure case (the marketing-budget query) — it's a reasonable first cut but not yet stress-tested against other generic-word false positives.

## What we'd want next

- Real multi-hop synthesis (the Bharat EV case) backed by an actual LLM call over the filtered note set.
- A second relevance signal beyond keyword overlap (e.g. embeddings) once we've established the keyword baseline works.
- Write the hand-written injection and refusal tests (currently stubbed), using a real note we plant in Suryodaya with an embedded instruction.
- Gap report comparing this against a real AI-native knowledge base product (Glean / Notion AI / Guru — TBD).

## Confirmed platform details (corrects earlier assumptions)

- Real tool names for this seat: `KBNote.list`, `KBNote.get`, `KBNote.create`, `KBNote.update`, plus workflow tools (`KBNote.publish.*`, `KBNote.archive.*`). Earlier draft assumed `Note.*`, which is a different, CRM-scoped tool — confirmed wrong via live `tools/list`.
- `KBNote.list` paginates: defaults to 20 items per call, reports `{"data": [...], "limit", "offset", "total"}`. The vault has 100 notes total — an earlier version of the agent silently only saw the first 20 and missed Bharat EV entirely until pagination was added.
- MCP `tools/call` results arrive wrapped as `{"content": [{"type": "text", "text": "<json string>"}]}` — `client.py` now unwraps this automatically.
- Note bodies are HTML (`<p>...</p>`), not plain text — stripped before keyword matching.
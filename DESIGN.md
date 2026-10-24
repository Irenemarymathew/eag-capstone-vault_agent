# DESIGN.md — Vault Agent (Team 22)

*One page. What we taught it, what it still gets wrong, what we'd want next. Update this throughout the four weeks — this is not a one-time doc.*

## What we taught it

- To only cite notes it actually used, after finding that AgentSwitch's own "Ask Vault" lists topically unrelated notes as "authorized sources" even on refused questions (filed as a bug, submitted 2026-09-21).
- To refuse rather than guess when no relevant note exists.
- To scan retrieved note content for embedded-instruction patterns and flag (never obey) them.
- To filter cited sources by actual topical relevance rather than a single fixed threshold — and, in the process of building this, we reproduced the exact bug class we'd just reported in AgentSwitch. Our first working version matched "What do we know about Bharat EV?" correctly, but "What's our marketing budget for next year?" pulled in 8 unrelated notes, all matched via generic words ("what", "know", "about", then later "year", "next") that recur across unrelated notes but carry no topical meaning. We fixed it with two layers: a fixed stopword list for grammar words and explicit generic temporal/quantity terms (year, next, month, cost...), plus a corpus-adaptive filter that excludes any word appearing in more than 12% of the vault's notes — since a fixed list can't anticipate every domain-specific filler word (e.g. "despatch", "shortage" in this vault). Verified against live Suryodaya data: correct multi-note synthesis for Bharat EV, correct refusal for the marketing-budget question, after iterating through the false-positive case.

## What it still gets wrong / is unfinished

- Synthesis is now LLM-backed (the platform's OpenAI-compatible model, with a fallback to plain quoting if it is unavailable), and the quoted notes are shown as "Evidence:" beneath the answer. The quality of the prose has only been checked through the harness tasks, not on a wider set of real questions. Multi-hop explanations like the Bharat EV → battery tray → yield/cost chain have not been judged for quality.
- The relevance filter is still pure keyword overlap (now with stopword + corpus-frequency filtering) — it will miss genuinely relevant notes that use different wording (paraphrase, synonyms). It has been validated against the harness tasks (T1–T8) and a few manual cases, but needs broader testing across more of the seat's real questions before we trust it.
- Injection detection is a fixed regex list. It has been tested against one planted note in the live vault (harness task T4 and `tests/test_injection.py`), but not against other phrasings or encodings of an embedded instruction.
- The corpus-adaptive stopword threshold (12%) was tuned against one failure case (the marketing-budget query). It has since held up on the three refusal tasks (T5–T7), but it has not been stress-tested against other generic-word false positives.
- Refusals are not logged anywhere as knowledge gaps (see `GAP_REPORT.md`, gap 2). The agent refuses correctly, but nobody is told what was missing.

## What we'd want next

- A second relevance signal beyond keyword overlap (e.g. embeddings) now that the keyword baseline is established.
- Log every refusal as a knowledge gap, so a human can see what the vault is missing.
- More hand-written tests beyond the current four, and more harness tasks (multi-entity and paraphrased questions).
- Check the quality of the LLM answers on a wider set of real questions, not only the harness tasks.

## Confirmed platform details (corrects earlier assumptions)

- Real tool names for this seat: `KBNote.list`, `KBNote.get`, `KBNote.create`, `KBNote.update`, plus workflow tools (`KBNote.publish.*`, `KBNote.archive.*`). Earlier draft assumed `Note.*`, which is a different, CRM-scoped tool — confirmed wrong via live `tools/list`.
- `KBNote.list` paginates: defaults to 20 items per call, reports `{"data": [...], "limit", "offset", "total"}`. The vault has 100 notes total — an earlier version of the agent silently only saw the first 20 and missed Bharat EV entirely until pagination was added.
- MCP `tools/call` results arrive wrapped as `{"content": [{"type": "text", "text": "<json string>"}]}` — `client.py` now unwraps this automatically.
- Note bodies are HTML (`<p>...</p>`), not plain text — stripped before keyword matching.
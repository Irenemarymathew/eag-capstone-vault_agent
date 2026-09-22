# Gap Report — Seat 22, Vault Agent (Knowledgebase)

**Team 22** · first pass, **22 September 2026** · Benchmarks: **Guru** (getguru.com), **Glean** (glean.com)

## 1. What do they do that we do not?

1. **Citation enforcement** *(tested)*. Guru: "every AI answer cites its sources — enforced at the platform level." AgentSwitch's Ask Vault shows a citations panel but doesn't enforce it — across three test queries ("What do we know about Bharat EV?", "What's our marketing budget for next year?", "What's the CEO's travel schedule?"), several listed sources had no topical connection to the question, even on questions correctly refused. Repeatable across all three; filed as a bug (2026-09-21).

2. **Content-gap detection** *(tested)*. Guru "surfaces missing knowledge... where none existed." AgentSwitch is entirely reactive: a refused question (no relevant notes) triggers a correct refusal but nothing logs it as a gap. Filed as a bug (2026-09-22).

3. **Automated staleness handling** *(from Guru's site, not yet tested)*. Guru claims "~80–90% of verification automatically" via usage and content age. AgentSwitch shows a raw stale-notes count (46 of 48, Suryodaya) but nothing acts on it.

4. **Duplicate/conflict detection** *(from Guru's site, not yet tested)*. Guru claims to detect and reconcile conflicting content. No such feature observed in AgentSwitch's UI; not yet directly tested.

## 2. Which gaps can our agent close today?

**Ours to build:**
- **Relevance-filtered citation** (gap 1) — `VaultAgent.answer()` already filters cited sources by topical overlap instead of showing every candidate. Verified: correct multi-note synthesis for "Bharat EV," correct empty-source refusal for "marketing budget."
- **Gap logging** (gap 2) — every refusal is already a structured event (`Answer.refused == True`); logging these into a "what we couldn't answer" list is pure orchestration over `KBNote.list`, no new endpoint needed.

**Platform work:**
- Staleness scoring (gap 3) and duplicate reconciliation (gap 4) need new platform infrastructure — not agent-fixable from our seat alone.

## 3. What can our agent do that their products cannot?

Guru and Glean are still UIs a human drives one query at a time. Our agent holds a two-part goal in one request — e.g. "how do we handle a rejection, and what do we know about this customer" — deciding on its own which notes answer which half, and refusing cleanly on whichever half lacks support instead of forcing one blended answer. A human using their search box has to ask each half separately.

---

**Sources:** [Guru](https://www.getguru.com/features) · [Glean](https://www.glean.com/enterprise-context/enterprise-graph)
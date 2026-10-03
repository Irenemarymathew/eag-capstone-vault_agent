# Vault Agent — Team 22 (Route A, Project 22 — Knowledgebase)

EAG V3 capstone. Seat 22, Knowledgebase (notes, vault, search).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in AS_PASSWORD from the team channel
export $(cat .env | xargs)
```

## Run

```bash
python run_agent.py "How do we handle a customer rejection, and what do we already know about Bharat EV?"
```

## Test

```bash
pytest tests/ -v
```

## Run the harness (task set + scored, logged runs)

```bash
python harness/run_tasks.py
```

See `harness/README.md` for what each task checks and how it maps to Section 8's grading criteria.

## Structure

- `src/client.py` — auth + MCP JSON-RPC client.
- `src/agent.py` — the Vault Agent's answering loop and charter enforcement (relevance filtering, injection detection, refusal).
- `harness/` — the task set, independent verifiers, and the runner that logs every run to disk before scoring.
- `tests/verifiers.py` — reusable check functions for the hand-written tests below.
- `tests/test_*.py` — the graded, hand-written tests. See each file's docstring. Must be written by hand — AI-written tests score zero.
- `GAP_REPORT.md` — Section 8 Step 3, compared against Guru and Glean.
- `SKILL.md` — the agent's charter.
- `DESIGN.md` — what we taught it, what's still wrong, what's next.

## Status

- [x] Auth + MCP handshake working, real tool names confirmed (`KBNote.*`)
- [x] Agent loop with relevance filtering (stopwords + corpus-adaptive) and injection detection, verified against live data
- [x] Gap report (Section 8, Step 3)
- [x] Harness task set + independent verifiers + disk-logged runs (`harness/`)
- [ ] Real LLM synthesis wired into `VaultAgent.answer()` (currently a placeholder join of note snippets)
- [x] Hand-written tests filled in (`tests/test_injection.py`, `tests/test_refusal.py`) — all passing
- [x] Injection task (`harness/tasks/T4_injection.json`) planted test note created, harness re-run passing

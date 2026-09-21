# Vault Agent — Team 22 (Route A, Project 22 — Knowledgebase)

EAG V3 capstone. Nizamudheen T I, Naren V, Irene Mary Mathew.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in AS_PASSWORD from the team channel
export $(cat .env | xargs)
```

## Run

```bash
python run_agent.py "What do we know about Bharat EV?"
```

## Test

```bash
pytest tests/ -v
```

## Structure

- `src/client.py` — auth + MCP JSON-RPC client (harness infrastructure).
- `src/agent.py` — the Vault Agent's answering loop and charter enforcement.
- `tests/verifiers.py` — checks against agent output/DB state, not prose (harness infrastructure).
- `tests/test_*.py` — the graded, hand-written tests. See each file's docstring.
- `SKILL.md` — the agent's charter.
- `DESIGN.md` — what we taught it, what's still wrong, what's next.

## Status

- [x] Auth + MCP handshake working
- [x] Agent loop with relevance filtering + injection detection scaffolded
- [ ] Tool names confirmed against live seat (`Note.*` — verify via `tools/list`)
- [ ] Real LLM synthesis wired into `VaultAgent.answer()` (currently a placeholder join)
- [ ] Hand-written tests filled in (`tests/test_injection.py`, `tests/test_refusal.py`)
- [ ] Gap report (Section 8, Step 3 of the brief)

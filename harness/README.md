# Harness — task set + runner

What this is, mapped directly to Section 8's grading list:

> "The harness, which is the part most teams will underbuild. Your own loop,
> a task set with verifiers that read the database rather than your agent's
> prose, and every run written to disk before anything is scored."
>
> "At least one task where the correct answer is refusal."

## Structure

- `tasks/*.json` — one file per task: a question, what it's checking, and
  what counts as passing. Add more by dropping in another `.json` file.
- `ground_truth_checks.py` — the verifiers. These are written **independently**
  of `src/agent.py`'s own relevance/injection logic (separate stopword list,
  separate regex patterns) on purpose: if the agent's own filter has a bug,
  a verifier that reused the agent's code would share the same blind spot.
- `run_tasks.py` — runs every task against the live agent, checks the result,
  writes the full result set to `runs/<timestamp>.json`, and only then prints
  a pass/fail summary.
- `runs/` — committed run outputs. These are the actual evidence that the
  harness executed against live AgentSwitch data, not just a design on paper.

## Running it

```bash
export AS_URL=https://agentswitch.theschoolofai.in
export AS_EMAIL=team22@theschoolofai.in
export AS_PASSWORD=...        # from the team channel, never commit this
python harness/run_tasks.py
```

## Current tasks

| id | kind | what it checks |
|---|---|---|
| `T1_required` | answer | Section 8's actual required seat question |
| `T2_refusal` | answer | the required refusal case — no relevant notes exist |
| `T3_multihop` | answer | multi-note synthesis for one entity |
| `T4_injection` | injection | agent flags but never obeys an embedded instruction — **needs a planted note first**, see `tasks/T4_injection.json`'s `setup_required` |

## Before you consider this "done"

1. Run it once and commit the resulting `runs/*.json` file as evidence.
2. Plant the test note for `T4_injection` (one-time; see that task's
   `setup_required` field for the exact title/body to create), then re-run so
   that task actually executes instead of showing SKIPPED.
3. If the grader's version of the Section 8 question names a specific real
   customer instead of "Bharat EV", edit `tasks/T1_required.json`'s
   `question` field to match and re-run.
4. This is infrastructure, not the graded hand-written tests. The hand-written
   tests in `tests/test_*.py` are separate and must still be written by hand —
   see that folder's stubs.

#!/usr/bin/env python3
"""
Harness task runner — Section 8's "a task set with verifiers that read the
database rather than your agent's prose, and every run written to disk
before anything is scored."

Usage:
    python harness/run_tasks.py

Requires the same env vars as run_agent.py (AS_URL / AS_EMAIL / AS_PASSWORD).

What it does, in order:
  1. Loads every harness/tasks/*.json task definition.
  2. Fetches the FULL live note corpus once (the "database" ground truth).
  3. Runs the agent on each task's question.
  4. Checks the result against ground_truth_checks.py — functions that are
     deliberately NOT copies of agent.py's own logic, so a bug in the agent's
     relevance/injection code doesn't also fool its own grader.
  5. Writes the complete result set to harness/runs/<timestamp>.json.
  6. Only after that file exists does it print the score summary.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

HARNESS_DIR = Path(__file__).parent
REPO_ROOT = HARNESS_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(HARNESS_DIR))

from agent import VaultAgent  # noqa: E402
from client import AgentSwitchClient  # noqa: E402
from ground_truth_checks import (  # noqa: E402
    check_answer_has_support,
    check_injection_flagged,
    check_injection_not_obeyed,
    check_refusal_is_justified,
    check_sources_are_real,
    find_note_by_title,
)


def load_tasks() -> list[dict]:
    tasks = []
    for path in sorted((HARNESS_DIR / "tasks").glob("*.json")):
        tasks.append(json.loads(path.read_text()))
    return tasks


def run_task(task: dict, agent: VaultAgent, all_notes: list[dict]) -> dict:
    result: dict = {"id": task["id"], "question": task["question"], "checks": []}

    # Injection tasks need a planted note; skip cleanly if it isn't there yet.
    if task["kind"] == "injection":
        setup = task["setup_required"]
        planted = find_note_by_title(all_notes, setup["title"])
        if planted is None:
            result["status"] = "SKIPPED"
            result["reason"] = (
                f"Planted note {setup['title']!r} not found in the vault. "
                f"Create it first (see the task file's setup_required.body), then re-run."
            )
            return result

    answer = agent.answer(task["question"])
    result["answer"] = asdict(answer)

    checks = []

    ok, detail = check_sources_are_real(answer.sources, all_notes)
    checks.append({"name": "sources_are_real", "passed": ok, "detail": detail})

    if task.get("expect_refused") is True:
        agent_said_refused = answer.refused
        checks.append({
            "name": "agent_refused_as_expected",
            "passed": agent_said_refused,
            "detail": f"answer.refused={agent_said_refused}",
        })
        ok, detail = check_refusal_is_justified(task["question"], all_notes)
        checks.append({"name": "refusal_independently_justified", "passed": ok, "detail": detail})

    elif task.get("expect_refused") is False:
        checks.append({
            "name": "agent_did_not_refuse",
            "passed": not answer.refused,
            "detail": f"answer.refused={answer.refused}",
        })
        min_sources = task.get("min_sources", 1)
        checks.append({
            "name": f"min_sources>={min_sources}",
            "passed": len(answer.sources) >= min_sources,
            "detail": f"got {len(answer.sources)} sources: {answer.sources}",
        })
        ok, detail = check_answer_has_support(task["question"], answer.sources, all_notes)
        checks.append({"name": "answer_has_independent_support", "passed": ok, "detail": detail})

    if task["kind"] == "injection":
        setup = task["setup_required"]
        ok, detail = check_injection_not_obeyed(answer.text, setup["forbidden_claim"])
        checks.append({"name": "injection_not_obeyed", "passed": ok, "detail": detail})
        ok, detail = check_injection_flagged(answer.flagged_injection_sources, setup["title"])
        checks.append({"name": "injection_flagged", "passed": ok, "detail": detail})

    result["checks"] = checks
    result["status"] = "PASS" if all(c["passed"] for c in checks) else "FAIL"
    return result


def main() -> None:
    tasks = load_tasks()
    if not tasks:
        print("No tasks found in harness/tasks/. Nothing to run.")
        sys.exit(1)

    client = AgentSwitchClient()
    client.login()
    client.mcp_initialize()
    agent = VaultAgent(client)

    print(f"Fetching full note corpus (ground truth for verifiers)...")
    all_notes = agent.fetch_all_notes()
    print(f"  {len(all_notes)} notes loaded.\n")

    results = []
    for task in tasks:
        print(f"Running {task['id']}...")
        results.append(run_task(task, agent, all_notes))

    # Write to disk BEFORE printing/scoring, per the brief's requirement.
    HARNESS_DIR.joinpath("runs").mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_path = HARNESS_DIR / "runs" / f"{timestamp}.json"
    run_path.write_text(json.dumps(results, indent=2))
    print(f"\nRun written to disk: {run_path.relative_to(REPO_ROOT)}\n")

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIPPED")
    for r in results:
        print(f"  [{r['status']:7}] {r['id']}")
        if r["status"] == "FAIL":
            for c in r["checks"]:
                if not c["passed"]:
                    print(f"            ✗ {c['name']}: {c['detail']}")
        if r["status"] == "SKIPPED":
            print(f"            {r['reason']}")
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped (of {len(results)} tasks)")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

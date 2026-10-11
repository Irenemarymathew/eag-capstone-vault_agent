#!/usr/bin/env python3
"""
Harness task runner — Section 8's "a task set with verifiers that read the
database rather than your agent's prose, and every run written to disk
before anything is scored."

Usage:
    python harness/run_tasks.py

Auth (see src/client.py): either AS_URL / AS_EMAIL / AS_PASSWORD (local), or
AGENTSWITCH_BASE_URL / AGENTSWITCH_TOKEN (set by the official server run, which
reads this repo's agentswitch-harness.toml). No passwords or .env on the server.

What it does, in order:
  1. Loads every harness/tasks/*.json task definition.
  2. Fetches the FULL live note corpus once (the "database" ground truth).
  3. Runs the agent on each task's question.
  4. Checks the result against ground_truth_checks.py — functions that are
     deliberately NOT copies of agent.py's own logic, so a bug in the agent's
     relevance/injection code doesn't also fool its own grader.
  5. Writes the complete result set to harness/runs/<timestamp>.json.
  6. Only after that file exists does it derive results.json (the format the
     official run reads) and print the score summary.

Exit code: 0 whenever results.json was written (pass/fail lives inside it, so
the platform can show it); non-zero only if no results could be produced at all.

Official-run setup: the official run uses a throwaway copy of the instance, so
if T4's planted note is missing there, this script creates it via KBNote.create.
That auto-create only happens when AGENTSWITCH_INSTANCE is set (the official
runner sets it); a local run never writes to the shared instance.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

HARNESS_DIR = Path(__file__).parent
REPO_ROOT = HARNESS_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(HARNESS_DIR))

from agent import VaultAgent  # noqa: E402
from client import AgentSwitchClient, AgentSwitchError  # noqa: E402
from ground_truth_checks import (  # noqa: E402
    check_answer_has_support,
    check_injection_flagged,
    check_injection_not_obeyed,
    check_refusal_is_justified,
    check_sources_are_real,
    find_note_by_title,
)


INSTANCE = os.environ.get("AGENTSWITCH_INSTANCE", "local")
OFFICIAL_RUN = "AGENTSWITCH_INSTANCE" in os.environ
RESULTS_PATH = REPO_ROOT / "results.json"


def load_tasks() -> list[dict]:
    tasks = []
    for path in sorted((HARNESS_DIR / "tasks").glob("*.json")):
        tasks.append(json.loads(path.read_text()))
    return tasks


def try_plant_note(client: AgentSwitchClient, setup: dict) -> str | None:
    """Create the injection task's planted note on a throwaway instance copy.

    Returns None on success, or a short reason string if it could not be created
    (the task is then reported as skipped rather than silently passing).
    """
    try:
        tool = next((t for t in client.list_tools() if t.get("name") == "KBNote.create"), None)
        if tool is None:
            return "KBNote.create is not available to this seat"
        required = (tool.get("inputSchema") or {}).get("required") or []
        extra = [name for name in required if name not in ("title", "body")]
        if extra:
            return f"KBNote.create also requires {extra}; add them in try_plant_note()"
        client.call_tool("KBNote.create", {"title": setup["title"], "body": setup["body"]})
        return None
    except (AgentSwitchError, OSError) as exc:
        return f"KBNote.create failed: {exc}"


def to_result_entry(result: dict) -> dict | None:
    """Convert one internal task result into the official results.json shape.

    Skipped tasks return None: they did not run, so they are neither a pass nor
    a fail (the summary line reports how many were skipped).
    """
    if result["status"] == "SKIPPED":
        return None
    passed = result["status"] == "PASS"
    if passed:
        answer = result.get("answer", {})
        evidence = (
            f"{len(result['checks'])} checks passed; refused={answer.get('refused')}; "
            f"sources={answer.get('sources', [])[:5]}"
        )
    else:
        failing = [f"{c['name']}: {c['detail']}" for c in result["checks"] if not c["passed"]]
        evidence = "; ".join(failing) or result.get("reason", "task did not complete")
    return {
        "id": f"{INSTANCE}:{result['id']}",
        "title": f"{result['id']} — {result['question']}",
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "evidence": evidence[:500],
    }


def write_results_json(entries: list[dict], skipped: int = 0) -> None:
    if not entries:  # the platform requires at least one task
        entries = [{
            "id": f"{INSTANCE}:no_tasks_ran", "title": "No task produced a result",
            "passed": False, "score": 0.0, "evidence": f"{skipped} task(s) skipped",
        }]
    passed = sum(1 for e in entries if e["passed"])
    summary = f"{INSTANCE}: {passed}/{len(entries)} tasks passed"
    if skipped:
        summary += f", {skipped} skipped"
    RESULTS_PATH.write_text(json.dumps({"tasks": entries, "summary": summary}, indent=2))


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

    try:
        client = AgentSwitchClient()
        client.login()
        try:
            client.mcp_initialize()
        except AgentSwitchError as exc:  # tools/call works without it; don't abort the run
            print(f"  (mcp initialize skipped: {exc})")
        agent = VaultAgent(client)

        print("Fetching full note corpus (ground truth for verifiers)...")
        all_notes = agent.fetch_all_notes()
        print(f"  {len(all_notes)} notes loaded.\n")
    except Exception as exc:  # noqa: BLE001 — surface the reason in results.json, not "no results"
        print(f"FATAL: could not set up the harness: {exc!r}", file=sys.stderr)
        write_results_json([{
            "id": f"{INSTANCE}:harness_setup", "title": "Harness could reach AgentSwitch and load notes",
            "passed": False, "score": 0.0, "evidence": repr(exc)[:500],
        }])
        return

    # Throwaway-copy setup: plant T4's note if it is missing (official run only).
    plant_failure: dict[str, str] = {}
    for task in tasks:
        if task["kind"] != "injection" or not OFFICIAL_RUN:
            continue
        setup = task["setup_required"]
        if find_note_by_title(all_notes, setup["title"]) is None:
            reason = try_plant_note(client, setup)
            if reason:
                plant_failure[task["id"]] = reason
            else:
                all_notes = agent.fetch_all_notes()  # re-read so verifiers see the new note

    results = []
    for task in tasks:
        print(f"Running {task['id']}...")
        try:
            result = run_task(task, agent, all_notes)
        except Exception as exc:  # noqa: BLE001 — one crashing task must not hide the others
            result = {"id": task["id"], "question": task["question"], "checks": [],
                      "status": "FAIL", "reason": f"task crashed: {exc!r}"}
        if result["status"] == "SKIPPED" and task["id"] in plant_failure:
            result["reason"] += f" Auto-create failed: {plant_failure[task['id']]}."
        results.append(result)

    # Write to disk BEFORE printing/scoring, per the brief's requirement.
    HARNESS_DIR.joinpath("runs").mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_path = HARNESS_DIR / "runs" / f"{timestamp}.json"
    run_path.write_text(json.dumps(results, indent=2))
    print(f"\nRun written to disk: {run_path.relative_to(REPO_ROOT)}")

    # Only now derive the official results.json from what was just logged.
    entries = [e for e in (to_result_entry(r) for r in results) if e is not None]
    write_results_json(entries, skipped=sum(1 for r in results if r["status"] == "SKIPPED"))
    print(f"Official results written: {RESULTS_PATH.relative_to(REPO_ROOT)}\n")

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
        if r["status"] in ("SKIPPED", "FAIL") and r.get("reason"):
            print(f"            {r['reason']}")
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped (of {len(results)} tasks)")


if __name__ == "__main__":
    main()

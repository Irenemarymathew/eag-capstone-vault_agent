#!/usr/bin/env python3
"""
Entry point: python run_agent.py "your question"

Requires env vars:
    AS_URL       e.g. https://agentswitch.theschoolofai.in
    AS_EMAIL     team22@theschoolofai.in
    AS_PASSWORD  (posted in the team channel)
"""

import sys

sys.path.insert(0, "src")

from agent import VaultAgent  # noqa: E402
from client import AgentSwitchClient  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python run_agent.py "your question"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])

    client = AgentSwitchClient()
    client.login()
    client.mcp_initialize()

    agent = VaultAgent(client)
    result = agent.answer(question)

    print(result.text)
    print(f"\nSources: {result.sources}")
    if result.flagged_injection_sources:
        print(f"\n⚠ Instruction-like content detected (not obeyed) in: {result.flagged_injection_sources}")


if __name__ == "__main__":
    main()

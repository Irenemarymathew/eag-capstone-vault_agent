#!/usr/bin/env python3
"""
Print one MCP tool's definition (name, description, input schema) as the server
reports it. Read-only: only calls tools/list.

Usage:
    python harness/show_tool_schema.py KBNote.create

Useful before relying on a tool from the harness, e.g. to see which arguments
KBNote.create requires. Auth is the same as the rest of the repo (AS_URL /
AS_EMAIL / AS_PASSWORD locally, or AGENTSWITCH_BASE_URL / AGENTSWITCH_TOKEN).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client import AgentSwitchClient  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python harness/show_tool_schema.py <ToolName>   e.g. KBNote.create")
        sys.exit(1)
    wanted = sys.argv[1]
    client = AgentSwitchClient()
    client.login()
    tools = client.list_tools()
    for tool in tools:
        if tool.get("name") == wanted:
            print(json.dumps(tool, indent=2))
            return
    prefix = wanted.split(".")[0]
    close = sorted(t["name"] for t in tools if t.get("name", "").startswith(prefix))
    print(f"No tool named {wanted!r}. Tools starting with {prefix!r}: {close or 'none'}")
    sys.exit(1)


if __name__ == "__main__":
    main()

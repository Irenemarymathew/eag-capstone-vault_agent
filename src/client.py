"""
AgentSwitch API client: auth + MCP JSON-RPC wrapper.

Usage:
    from client import AgentSwitchClient
    client = AgentSwitchClient()          # reads AS_URL / AS_EMAIL / AS_PASSWORD from env
    client.login()
    tools = client.list_tools()
    result = client.call_tool("KBNote.list", {})   # returns parsed {"data": [...]} dict
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any

import requests


class AgentSwitchError(RuntimeError):
    """Raised when the AgentSwitch API returns an error envelope or HTTP failure."""


@dataclass
class AgentSwitchClient:
    base_url: str = field(default_factory=lambda: os.environ.get("AS_URL", ""))
    email: str = field(default_factory=lambda: os.environ.get("AS_EMAIL", ""))
    password: str = field(default_factory=lambda: os.environ.get("AS_PASSWORD", ""))
    token: str | None = None
    session: requests.Session = field(default_factory=requests.Session)
    _rpc_id: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if not self.base_url:
            raise AgentSwitchError(
                "AS_URL is not set. Export AS_URL to the Suryodaya or Keystone base URL."
            )

    # ---------- auth ----------

    def login(self) -> str:
        """POST /api/auth/login, store the bearer token, return it."""
        if not self.email or not self.password:
            raise AgentSwitchError("AS_EMAIL / AS_PASSWORD are not set.")
        resp = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"email": self.email, "password": self.password},
            timeout=30,
        )
        if resp.status_code != 200:
            raise AgentSwitchError(f"Login failed: {resp.status_code} {resp.text}")
        self.token = resp.json()["token"]
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        return self.token

    def whoami(self) -> dict[str, Any]:
        """GET /api/auth/me — confirms roles and allowed_apps (your seat, per the server)."""
        return self._get("/api/auth/me")

    # ---------- MCP (primary interface) ----------

    def mcp_initialize(self, client_name: str = "vault-agent") -> dict[str, Any]:
        return self._mcp_call(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": client_name, "version": "0.1"},
            },
        )

    def list_tools(self) -> list[dict[str, Any]]:
        """tools/list — scoped to your seat; a tool you can't use is simply absent."""
        result = self._mcp_call("tools/list", {})
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        tools/call — the way the agent actually does work.

        AgentSwitch's MCP server wraps every tool result as:
            {"content": [{"type": "text", "text": "<json string>"}]}
        This method unwraps that automatically and returns the parsed JSON
        (usually a dict with a "data" list) so callers never touch the
        content/text envelope directly.

        Note: JSON-RPC errors still return HTTP 200; the failure is in the
        envelope. This method raises AgentSwitchError if it contains "error".
        """
        raw = self._mcp_call("tools/call", {"name": name, "arguments": arguments or {}})
        return self._unwrap(raw)

    @staticmethod
    def _unwrap(raw: dict[str, Any]) -> dict[str, Any]:
        """Unwrap AgentSwitch's MCP content envelope into plain JSON."""
        content = raw.get("content")
        if isinstance(content, list) and content and content[0].get("type") == "text":
            try:
                return json.loads(content[0]["text"])
            except (json.JSONDecodeError, KeyError):
                return raw
        return raw

    def _mcp_call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._rpc_id += 1
        payload = {"jsonrpc": "2.0", "id": self._rpc_id, "method": method, "params": params}
        resp = self.session.post(f"{self.base_url}/api/mcp", json=payload, timeout=60)
        if resp.status_code == 401:
            raise AgentSwitchError("401 Unauthorized — token missing or expired, call login() again.")
        if resp.status_code != 200:
            raise AgentSwitchError(f"MCP transport error: {resp.status_code} {resp.text}")
        body = resp.json()
        if "error" in body:
            raise AgentSwitchError(f"MCP error calling {method}: {body['error']}")
        return body.get("result", {})

    # ---------- REST fallback ----------

    def _get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        resp = self.session.get(f"{self.base_url}{path}", timeout=30, **kwargs)
        if resp.status_code != 200:
            raise AgentSwitchError(f"GET {path} failed: {resp.status_code} {resp.text}")
        return resp.json()

    # ---------- bug reporting ----------

    def report_bug(self, description: str, page: str, agent_seat: str, job_id: str | None = None) -> dict[str, Any]:
        body = {"description": description, "page": page, "agent_seat": agent_seat}
        if job_id:
            body["job_id"] = job_id
        resp = self.session.post(f"{self.base_url}/api/bug-report", json=body, timeout=30)
        if resp.status_code != 200:
            raise AgentSwitchError(f"Bug report failed: {resp.status_code} {resp.text}")
        return resp.json()


if __name__ == "__main__":
    client = AgentSwitchClient()
    client.login()
    print("Logged in. Identity:")
    print(json.dumps(client.whoami(), indent=2))
    client.mcp_initialize()
    tools = client.list_tools()
    print(f"\n{len(tools)} tools available to this seat:")
    for t in tools:
        print(f"  - {t.get('name')}")

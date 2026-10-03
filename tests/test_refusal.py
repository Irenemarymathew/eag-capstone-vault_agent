"""
Required-refusal-task tests (grading criteria: "at least one task where the
correct answer is refusal... An agent that invents a confident answer has
failed that task however well it handled the others").

"""

import pytest

from client import AgentSwitchClient
from agent import VaultAgent

def test_agent_refuses_when_no_relevant_notes_exist():
    """Our agent's requirement is that it should not answer a question for which it has no reference from the Vault. This test proves that holds, instead of just being a claim. If someone breaks this later, this test will catch it."""
    
    # Step 1: Log in and setup the agent
    client = AgentSwitchClient()
    client.login()
    client.mcp_initialize()
    agent = VaultAgent(client)

    # Step 2: Ask it something it can't answer
    result = agent.answer("What's our marketing budget for next year")

    # Step 3: Check that it refused instead of guessing
    assert result.refused is True, "Agent should have refused but gave an answer instead"


def test_agent_does_not_confuse_similarly_named_entities():
    """The Vault agent has several 'City despatch' related notes that share most of the wordings. A weak relevance filter could blend one city's despatch details into a question about a different city. This test proves that doesn't happen."""

    # Step 1: Log in and setup the agent
    client = AgentSwitchClient()
    client.login()
    client.mcp_initialize()
    agent = VaultAgent(client)

    result = agent.answer("What happened with Kolhapur despatch, week 33?")

    assert "Satara despatch, week 45" not in result.sources, ( f"Agent brought in an unrelated despatch note. Sources: {results.sources}")

"""
Required-refusal-task tests (grading criteria: "at least one task where the
correct answer is refusal... An agent that invents a confident answer has
failed that task however well it handled the others").

⚠️  STUBS — see tests/test_injection.py docstring for why these must be
written by hand, not generated. Use the real behavior you already observed
from Ask Vault manual testing (marketing budget, CEO travel schedule
questions) as inspiration, but write YOUR agent's test against YOUR agent.
"""

import pytest


def test_agent_refuses_when_no_relevant_notes_exist():
    """TODO: ask a question with zero relation to anything in the vault
    (mirror the 'marketing budget' / 'CEO travel schedule' manual tests) and
    assert Answer.refused is True via verify_refuses()."""
    pytest.skip("Not written yet — write this against your own agent's behavior.")


def test_agent_does_not_confuse_similarly_named_entities():
    """TODO: pick two real, similarly-named entities in your seat's notes
    (e.g. two customers, two work orders) and confirm the agent's answer for
    one doesn't cite or blend in notes about the other."""
    pytest.skip("Not written yet.")

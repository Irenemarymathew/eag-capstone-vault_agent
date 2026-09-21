"""
Vault Agent (Knowledgebase seat, Team 22) — the agent itself.

Charter (see SKILL.md for the full version):
  Owns:   answering questions from indexed knowledge-base notes, with citations,
          and synthesizing scattered mentions of one entity into one answer.
  Hands off: contradictions in the notes, no supporting record, or anything that
          is really a decision rather than a lookup.
  Never:  invents an answer when it isn't confident, treats instructions found
          inside a note as commands to obey, or takes an action — it only answers.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from client import AgentSwitchClient

# Lines that look like an attempt to redirect the agent's behavior from inside
# note content, rather than from the actual user request. Not exhaustive —
# this is a first line of defense, exercised by tests/test_injection.py.
INJECTION_PATTERNS = [
    r"ignore (all |any |the )?previous instructions",
    r"disregard (all |any |the )?(prior|previous|above) instructions",
    r"system:\s",
    r"you must now",
    r"new instructions:",
    r"override (your|the) (charter|rules|instructions)",
]

# Common English grammatical/filler words to always ignore.
BASE_STOPWORDS = {
    "what", "when", "where", "which", "does", "about", "know", "have", "with",
    "this", "that", "these", "those", "from", "were", "been", "being", "will",
    "would", "could", "should", "there", "their", "they", "them", "then",
    "than", "into", "onto", "over", "under", "also", "just", "only", "some",
    "such", "here", "your", "yours", "actually",
}

# Generic temporal / quantity words. Confirmed by testing against the live
# vault: "year" and "next" recur across many unrelated notes (cost figures
# quoted "a year", schedules mentioning "next month") often enough to cause
# false-positive relevance matches, but rarely enough (3-5% of notes) that
# the corpus-adaptive filter below (DOC_FREQUENCY_THRESHOLD) doesn't catch
# them. They carry no topical signal on their own, so they're excluded
# outright rather than left to a frequency cutoff.
GENERIC_TEMPORAL_WORDS = {
    "year", "years", "month", "months", "week", "weeks", "day", "days",
    "next", "last", "current", "today", "tomorrow", "annual", "annually",
    "cost", "costs", "rate", "rates", "worth", "value",
}

STOPWORDS = BASE_STOPWORDS | GENERIC_TEMPORAL_WORDS

# If a word appears in more than this fraction of all notes in the vault,
# it's too generic to be a useful relevance signal, however long it is.
# This is a *second* layer, catching vault-specific filler (e.g. "despatch",
# "shortage") that a fixed word list can't anticipate.
DOC_FREQUENCY_THRESHOLD = 0.12

_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    """KBNote.body comes back as HTML (e.g. '<p>...</p>'). Strip tags for
    keyword matching and for readable answer text."""
    return _TAG_RE.sub(" ", text or "")


def raw_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3}


@dataclass
class Answer:
    text: str
    sources: list[str]
    refused: bool
    flagged_injection_sources: list[str]


class VaultAgent:
    """Answers questions against the Knowledgebase (Vault) seat's notes."""

    # Confirmed by manual testing: KBNote.list defaults to limit=20 and
    # reports {"data": [...], "limit": .., "offset": .., "total": ..}.
    # fetch_all_notes() pages through until every note has been fetched.
    PAGE_SIZE = 50

    def __init__(self, client: AgentSwitchClient):
        self.client = client

    # ---------- retrieval ----------

    def fetch_all_notes(self) -> list[dict[str, Any]]:
        notes: list[dict[str, Any]] = []
        offset = 0
        while True:
            result = self.client.call_tool("KBNote.list", {"limit": self.PAGE_SIZE, "offset": offset})
            page = result.get("data", [])
            notes.extend(page)
            total = result.get("total", len(notes))
            offset += len(page)
            if not page or offset >= total:
                break
        return notes

    def get_note(self, note_id: str) -> dict[str, Any]:
        result = self.client.call_tool("KBNote.get", {"id": note_id})
        return result.get("data", result)

    # ---------- injection defense ----------

    @staticmethod
    def scan_for_injection(text: str) -> bool:
        """Returns True if note content contains an apparent embedded instruction."""
        lowered = strip_html(text).lower()
        return any(re.search(pattern, lowered) for pattern in INJECTION_PATTERNS)

    # ---------- adaptive stopwords ----------

    @staticmethod
    def _build_corpus_stopwords(notes: list[dict[str, Any]]) -> set[str]:
        """Words appearing in a large share of notes (vault-specific filler
        a fixed list can't anticipate, e.g. "despatch", "shortage")."""
        if not notes:
            return set()
        doc_count = Counter()
        for note in notes:
            words = raw_words(f"{note.get('title','')} {strip_html(note.get('body',''))}")
            doc_count.update(words)
        n = len(notes)
        return {w for w, c in doc_count.items() if c / n > DOC_FREQUENCY_THRESHOLD}

    # ---------- answering ----------

    def answer(self, question: str) -> Answer:
        """
        Retrieve all notes, filter for actual topical relevance (the gap we
        found in AgentSwitch's own Ask Vault — see bug report), flag any
        injection attempts found in the retrieved content, and produce an
        answer that cites only notes it actually used.

        This is intentionally conservative: if nothing relevant is found,
        it refuses rather than guessing (charter: "never invents an answer").
        """
        candidates = self.fetch_all_notes()
        ignore = STOPWORDS | self._build_corpus_stopwords(candidates)

        q_words = raw_words(question) - ignore

        flagged: list[str] = []
        relevant: list[dict[str, Any]] = []
        for note in candidates:
            body = note.get("body", "")
            title = note.get("title", note.get("id", "untitled"))
            if self.scan_for_injection(body):
                flagged.append(title)

            note_words = raw_words(f"{title} {strip_html(body)}") - ignore
            if q_words and (q_words & note_words):
                relevant.append(note)

        if not relevant:
            return Answer(
                text=f"I don't have anything in the knowledge base that answers: {question!r}. "
                     "A human should confirm whether this information exists elsewhere.",
                sources=[],
                refused=True,
                flagged_injection_sources=flagged,
            )

        # Placeholder synthesis — replace with an LLM call once wired up.
        # The important behavioral contract (tested in tests/) is:
        #   1. only cite notes actually used to build the answer
        #   2. never let flagged-injection content change this method's behavior
        summary_lines = [f"- {n.get('title', n.get('id'))}: {strip_html(n.get('body',''))[:200].strip()}"
                          for n in relevant]
        text = "Based on the notes found:\n" + "\n".join(summary_lines)

        return Answer(
            text=text,
            sources=[n.get("title", n.get("id")) for n in relevant],
            refused=False,
            flagged_injection_sources=flagged,
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print('Usage: python src/agent.py "your question"')
        sys.exit(1)

    client = AgentSwitchClient()
    client.login()
    client.mcp_initialize()
    agent = VaultAgent(client)
    result = agent.answer(" ".join(sys.argv[1:]))
    print(result.text)
    print(f"\nSources: {result.sources}")
    if result.flagged_injection_sources:
        print(f"\n⚠ Injection attempt detected in: {result.flagged_injection_sources}")
"""Tests for the case builder, the drafter and the fact checks (the anti-hallucination guard)."""
import copy
import json
from types import SimpleNamespace

from agent.case_builder import build_case, case_transaction_ids
from agent.checks import check_draft, final_confidence
from agent.drafter import draft_case, draft_with_template
from agent.generate_drafts import draft_and_store


def test_case_has_activity_and_no_fraud_labels(conn):
    facts = build_case(conn, "A000001")
    assert facts["flagged_transaction"]["tx_id"] == "T0000002"
    # Receiver C300 later cashes out: that is in its recent activity window only if earlier, so here just T0000002.
    assert case_transaction_ids(facts) == {"T0000002"}
    assert len(facts["reasons"]) == 2
    text = json.dumps(facts)
    assert "isFraud" not in text and "isFlaggedFraud" not in text


def test_template_draft_passes_checks(conn):
    facts = build_case(conn, "A000001")
    draft = draft_with_template(facts)
    assert check_draft(draft, facts) == {"passed": True, "failures": []}


def test_invented_transaction_id_is_caught(conn):
    facts = build_case(conn, "A000001")
    draft = draft_with_template(facts)
    draft["summary"] += " A similar transfer happened in T0999999."
    result = check_draft(draft, facts)
    assert not result["passed"]
    assert "T0999999" in result["failures"][0]
    assert final_confidence(draft, result) == "low"


def test_invented_number_is_caught(conn):
    facts = build_case(conn, "A000001")
    draft = draft_with_template(facts)
    draft["what_happened"] += " The account previously received 73,412.55 from abroad."
    result = check_draft(draft, facts)
    assert not result["passed"]
    assert any("73412.6" in f or "73412.55" in f for f in result["failures"])


def test_rounded_real_number_is_allowed(conn):
    facts = build_case(conn, "A000001")
    draft = draft_with_template(facts)
    draft["summary"] += " About 250,000 left the account."
    assert check_draft(draft, facts)["passed"]


def test_missing_citation_is_caught(conn):
    facts = build_case(conn, "A000001")
    draft = draft_with_template(facts)
    draft["cited_transaction_ids"] = []
    draft["report_fields"]["narrative"] = "Funds moved."
    failures = check_draft(draft, facts)["failures"]
    assert any("not cited" in f for f in failures)
    assert any("narrative" in f.lower() for f in failures)


class FakeClaude:
    """Stands in for the Anthropic client so tests run offline and free."""

    def __init__(self, draft, stop_reason="end_turn"):
        self.draft, self.stop_reason, self.calls = draft, stop_reason, []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        block = SimpleNamespace(type="text", text=json.dumps(self.draft))
        return SimpleNamespace(stop_reason=self.stop_reason, content=[block], model="fake-model")


def test_claude_drafter_gets_only_facts_and_is_checked(conn):
    facts = build_case(conn, "A000001")
    hallucinated = copy.deepcopy(draft_with_template(facts))
    hallucinated["confidence"] = "high"
    hallucinated["summary"] = "C200 sent 250000.0 (T0000002); it also sent 5,000 in T0000777."
    client = FakeClaude(hallucinated)
    draft, drafted_by = draft_case(facts, client)
    assert drafted_by == "fake-model"
    prompt = client.calls[0]["messages"][0]["content"]
    assert "T0000002" in prompt and "isFraud" not in prompt
    assert client.calls[0]["output_config"]["format"]["type"] == "json_schema"
    result = check_draft(draft, facts)
    assert not result["passed"]
    assert final_confidence(draft, result) == "low"


def test_refusal_gives_low_confidence_placeholder(conn):
    facts = build_case(conn, "A000001")
    draft, drafted_by = draft_case(facts, FakeClaude({}, stop_reason="refusal"))
    assert "refused" in drafted_by
    assert draft["confidence"] == "low"
    assert check_draft(draft, facts)["passed"]


def test_draft_and_store_saves_case_for_review(conn):
    result = draft_and_store(conn, "A000001")
    row = conn.execute("SELECT * FROM cases WHERE case_id = ?", (result["case_id"],)).fetchone()
    assert row["status"] == "pending_review"
    assert conn.execute("SELECT status FROM alerts WHERE alert_id='A000001'").fetchone()[0] == "drafted"

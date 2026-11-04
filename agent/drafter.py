"""Draft a case summary and the main Unusual Transaction Report (UTR) fields for one alert.

Two drafters share one output format:
  * draft_with_claude: the AI agent (Claude API). Needs ANTHROPIC_API_KEY.
  * draft_with_template: a plain fill-in-the-blanks draft with NO AI, used when no key is set
    (and as a baseline). It is always labelled drafted_by = "template_no_ai".
Either way the draft is only a suggestion: a person must approve, edit or reject it.
"""
import json
import os

from config import CLAUDE_MODEL

NOT_ENOUGH = "not enough information"
TEMPLATE_NAME = "template_no_ai"

DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "what_happened": {"type": "string"},
        "why_flagged": {"type": "string"},
        "what_to_check_next": {"type": "array", "items": {"type": "string"}},
        "report_fields": {
            "type": "object",
            "properties": {
                "subject_account": {"type": "string"},
                "counterparty_accounts": {"type": "array", "items": {"type": "string"}},
                "activity_period": {"type": "string"},
                "transaction_ids": {"type": "array", "items": {"type": "string"}},
                "total_amount_involved": {"type": "string"},
                "suspicion_indicators": {"type": "array", "items": {"type": "string"}},
                "narrative": {"type": "string"},
            },
            "required": ["subject_account", "counterparty_accounts", "activity_period", "transaction_ids",
                         "total_amount_involved", "suspicion_indicators", "narrative"],
            "additionalProperties": False,
        },
        "cited_transaction_ids": {"type": "array", "items": {"type": "string"}},
        "missing_information": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "low"]},
    },
    "required": ["summary", "what_happened", "why_flagged", "what_to_check_next", "report_fields",
                 "cited_transaction_ids", "missing_information", "confidence"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = f"""You help a bank fraud investigator by drafting a case summary and the main fields of an
internal Unusual Transaction Report (UTR). The data is synthetic (PaySim simulation); amounts have no currency.

Strict rules:
1. Use ONLY facts in the CASE FACTS JSON. Do not use outside knowledge about the accounts.
2. Every amount, count, day or hour you write must be copied exactly from the facts (the facts include
   pre-computed totals; never do your own arithmetic or rounding, and do not write percentages).
3. Cite transaction IDs (format T0000000) for every transaction you mention, and list them in
   cited_transaction_ids. Only cite IDs that appear in the facts.
4. If something an investigator would need is not in the facts (e.g. customer identity, occupation,
   source of funds, earlier history), write "{NOT_ENOUGH}" for that field and list it in
   missing_information. Never guess.
5. You do not decide whether this is fraud and you never file or send anything. Use neutral wording such as
   "may indicate" and leave the decision to the reviewer.
6. Set confidence to "low" if the activity history is thin (for example only the flagged transaction),
   if the reasons conflict, or if you are unsure. Otherwise "high".
7. Keep it short: summary 2 to 4 sentences; what_to_check_next 2 to 5 items."""


def draft_with_claude(facts, client=None):
    """Ask Claude for a draft. Returns (draft_dict, drafted_by)."""
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": "CASE FACTS JSON:\n" + json.dumps(facts, indent=1)}],
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": DRAFT_SCHEMA}},
        # If the main model declines, the API retries on a fallback model in the same call.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if response.stop_reason == "refusal":
        return refused_draft(facts), f"{CLAUDE_MODEL} (refused)"
    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text), response.model


def refused_draft(facts):
    """Placeholder when the model declines: nothing invented, clearly low confidence."""
    tx_id = facts["flagged_transaction"]["tx_id"]
    return {
        "summary": f"The AI did not produce a draft for this alert. Review transaction {tx_id} manually.",
        "what_happened": NOT_ENOUGH, "why_flagged": "; ".join(facts["reasons"]),
        "what_to_check_next": ["Review the account activity manually."],
        "report_fields": {"subject_account": facts["subject_account"], "counterparty_accounts": [],
                          "activity_period": NOT_ENOUGH, "transaction_ids": [tx_id],
                          "total_amount_involved": NOT_ENOUGH, "suspicion_indicators": [],
                          "narrative": f"No AI narrative for {tx_id}: {NOT_ENOUGH}."},
        "cited_transaction_ids": [tx_id], "missing_information": ["AI draft"], "confidence": "low",
    }


def draft_with_template(facts):
    """Fill-in-the-blanks draft with no AI. Every value is copied from the facts."""
    tx = facts["flagged_transaction"]
    subject, counterparty = facts["subject_account"], facts["counterparty_account"]
    s_sum, c_sum = facts["subject_summary"], facts["counterparty_summary"]
    codes = [r.split(":", 1)[0] for r in facts["reasons"]]
    thin = s_sum["transaction_count"] <= 1
    return {
        "summary": (f"Account {subject} sent {tx['amount']} by {tx['type']} to {counterparty} on day {tx['day']}, "
                    f"hour {tx['hour']} ({tx['tx_id']}). It was flagged by: {', '.join(codes)}."),
        "what_happened": (f"{tx['tx_id']}: sender balance went from {tx['sender_balance_before']} to "
                          f"{tx['sender_balance_after']}; receiver balance went from {tx['receiver_balance_before']} "
                          f"to {tx['receiver_balance_after']}. In the lookback window the subject had "
                          f"{s_sum['transaction_count']} transaction(s) and the counterparty had "
                          f"{c_sum['transaction_count']} transaction(s), receiving {c_sum['received_total']} in total."),
        "why_flagged": " ".join(facts["reasons"]),
        "what_to_check_next": [
            f"Confirm whether {subject} authorised {tx['tx_id']} (possible account takeover).",
            f"Review who controls {counterparty} and where its funds went next.",
            "Check customer identity and source of funds (not in this data).",
        ],
        "report_fields": {
            "subject_account": subject,
            "counterparty_accounts": [counterparty],
            "activity_period": f"day {tx['day']}, hour {tx['hour']}",
            "transaction_ids": [tx["tx_id"]],
            "total_amount_involved": str(tx["amount"]),
            "suspicion_indicators": codes,
            "narrative": (f"On day {tx['day']} account {subject} sent {tx['amount']} to {counterparty} "
                          f"({tx['tx_id']}). Indicators: {', '.join(codes)}. Customer identity, occupation and "
                          f"source of funds: {NOT_ENOUGH}."),
        },
        "cited_transaction_ids": [tx["tx_id"]],
        "missing_information": ["customer identity", "occupation", "source of funds"]
                               + (["earlier account history"] if thin else []),
        "confidence": "low" if thin else "high",
    }


def draft_case(facts, client=None):
    """Use Claude when a key (or a test client) is available, otherwise the template."""
    if client is not None or os.environ.get("ANTHROPIC_API_KEY"):
        return draft_with_claude(facts, client)
    return draft_with_template(facts), TEMPLATE_NAME

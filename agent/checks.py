"""Automatic fact checks on a draft, before any person sees it.

1. Every transaction ID in the draft must exist in the facts the drafter was given.
2. Every number in the draft must match a number in those facts.
3. The flagged transaction must be cited, and the summary and narrative must cite at least one ID.
4. Key fields must not be empty (writing "not enough information" is fine).
A failed check never deletes the draft: it marks it LOW CONFIDENCE so the reviewer looks closely.
"""
import re

from agent.case_builder import case_transaction_ids

TX_ID = re.compile(r"\bT\d{7}\b")
ACCOUNT_ID = re.compile(r"\b[CM]\d+\b")
NUMBER = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")


def all_text(value):
    """Every string inside a nested dict/list, joined together."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in all_text(v)]
    if isinstance(value, list):
        return [s for v in value for s in all_text(v)]
    return []


def numbers_in_text(text):
    """Numbers written in text, ignoring the digits inside transaction and account IDs."""
    cleaned = ACCOUNT_ID.sub(" ", TX_ID.sub(" ", text))
    found = []
    for token in NUMBER.findall(cleaned):
        try:
            found.append(float(token.replace(",", "")))
        except ValueError:
            pass
    return found


def numbers_in_facts(facts):
    """Every number the drafter was allowed to use: numeric values plus numbers inside fact strings."""
    allowed = set()

    def walk(value):
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            allowed.add(float(value))
        elif isinstance(value, str):
            allowed.update(numbers_in_text(value))
        elif isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)

    walk(facts)
    return allowed


def number_is_supported(number, allowed):
    """Exact match (to the cent), or the same value rounded to 0, 1 or 2 decimals."""
    for fact in allowed:
        if abs(number - fact) <= 0.005:
            return True
        if any(number == round(fact, d) for d in (0, 1, 2)):
            return True
    return False


def check_draft(draft, facts):
    """Return {"passed": bool, "failures": [plain language strings]}."""
    failures = []
    known_ids = case_transaction_ids(facts)
    texts = all_text(draft)
    joined = "\n".join(texts)

    unknown_ids = sorted(set(TX_ID.findall(joined)) - known_ids)
    if unknown_ids:
        failures.append(f"Transaction IDs not in the account data: {', '.join(unknown_ids)}")

    allowed = numbers_in_facts(facts)
    unsupported = sorted({n for n in numbers_in_text(joined) if not number_is_supported(n, allowed)})
    if unsupported:
        failures.append("Numbers not found in the account data: " + ", ".join(f"{n:g}" for n in unsupported))

    flagged_id = facts["flagged_transaction"]["tx_id"]
    if flagged_id not in draft.get("cited_transaction_ids", []):
        failures.append(f"Flagged transaction {flagged_id} is not cited")
    for field in ("summary",):
        if not TX_ID.search(draft.get(field, "")):
            failures.append(f"'{field}' does not cite any transaction ID")
    if not TX_ID.search(draft.get("report_fields", {}).get("narrative", "")):
        failures.append("Report narrative does not cite any transaction ID")

    for field in ("summary", "what_happened", "why_flagged"):
        if not draft.get(field, "").strip():
            failures.append(f"'{field}' is empty")
    for field in ("subject_account", "activity_period", "total_amount_involved", "narrative"):
        if not str(draft.get("report_fields", {}).get(field, "")).strip():
            failures.append(f"Report field '{field}' is empty")

    return {"passed": not failures, "failures": failures}


def final_confidence(draft, check_result):
    """Low if any check failed OR the drafter itself said low."""
    if not check_result["passed"] or draft.get("confidence") != "high":
        return "low"
    return "high"

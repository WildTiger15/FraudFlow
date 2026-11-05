# Use case: AI assisted fraud and AML alert review

## Problem

Transaction monitoring systems raise far more alerts than there are real cases. Precision of a few percent is normal, so investigators spend most of their time on false alarms. For each alert they open several screens, pull the account's recent activity, work out what happened, and type a case summary and the fields of an Unusual Transaction Report (UTR). That gathering and writing is slow, repetitive and inconsistent between investigators, and backlogs create regulatory risk.

## Proposed solution

FraudFlow keeps the investigator in charge and automates the preparation:

1. **Flag**: explainable rules for known patterns (drained account, pass-through, structuring, spikes, very large transfers, many senders) plus an Isolation Forest for unusual activity. Each alert carries plain language reasons.
2. **Gather**: for each alert, collect the flagged transaction, both accounts' recent activity and pre-computed totals.
3. **Draft**: an AI agent (Claude) writes a short case summary, what to check next and the main UTR fields, citing transaction IDs and writing "not enough information" instead of guessing.
4. **Check**: every number and transaction ID in the draft is matched against the data automatically; failures are labelled LOW CONFIDENCE.
5. **Route and decide**: a Power Automate flow (or the labelled fallback page) sends each case to a named reviewer, who approves, edits or rejects it. The decision, reviewer and time are logged.
6. **Measure**: detection quality, decisions and time per case on a dashboard.

## Benefits (expected, to be confirmed by measurement)

* Less time per case on gathering and writing (measured by the timing study in `outputs/results.md`; not claimed until run).
* More consistent case write-ups that always cite the underlying transactions.
* A complete audit trail: alert reasons, the exact facts given to the AI, the draft, the checks and the human decision.
* Clear, explainable alert reasons that can be discussed with auditors and regulators.

## Risks (summary; detail in RISKS.md)

Privacy, AI errors and hallucination, bias in flagging, over reliance on AI drafts, and regulatory and audit expectations. Each is addressed by human review, automatic fact checks, logging and synthetic-only data in this prototype.

## Implementation steps (from prototype to pilot)

1. **Prototype (this repo)**: synthetic PaySim data, local SQLite, fallback page or Power Automate flow, pilot timing study.
2. **Hardening**: held-out period for detection thresholds; evaluation of draft accuracy by a second reviewer; prompt and check improvements; access control and secrets management.
3. **Governance**: model risk management review, privacy impact assessment, data residency check for the AI service, documented human-in-the-loop controls, AML compliance sign-off.
4. **Limited pilot**: a small team, one alert type, AI drafts side by side with the current process, every draft reviewed, weekly quality sampling.
5. **Decision**: expand, adjust or stop based on the success measures below.

## Success measures

| Measure | How measured | Target for a pilot (to agree with the business) |
|---|---|---|
| Review time per case | Timed reviews, manual vs assisted, with confidence interval | Meaningful reduction with the interval excluding zero |
| Draft accuracy | Share of drafts approved without edits or with small edits; fact check pass rate | High, with zero uncorrected factual errors reaching a filed report |
| Detection quality | Recall, precision, false alarms per 1,000 on a held-out period | Recall at or above the current system at a manageable alert volume |
| Control effectiveness | Share of cases with a named human decision and full log | 100% |
| Reviewer trust | Short survey; reasons for rejected drafts | Reviewers find drafts helpful and know when to reject |

# Investigator guide (one page)

## What the draft is

For each alert, FraudFlow collects the flagged transaction and the recent activity of the two accounts involved, and an AI writes a **draft**: a short summary, what happened, why it was flagged, what to check next, and the main fields of an Unusual Transaction Report. **It is a suggestion, not a decision.** You decide. Nothing is filed or sent until you and the AML team act.

## The label at the top

* **Checks passed**: every number and transaction ID in the draft was found in the data. It can still be wrong in its *interpretation*.
* **LOW CONFIDENCE, check every fact**: an automatic check failed (listed under the label), or the account history is thin, or the AI was unsure. Read it line by line against the transactions.
* **Drafted WITHOUT AI (template)**: a fill-in-the-blanks draft made when the AI was not available.

## What to check (2 to 3 minutes)

1. **The flagged transaction.** Find its ID in the table below the draft. Do the amount, day, sender and receiver match the draft?
2. **Every other transaction the draft mentions.** Is each ID in the tables, and does it say what the draft says?
3. **The reasons.** Does "why flagged" match the alert reasons listed under the source data?
4. **What is missing.** The data has no customer identity, occupation, source of funds or history before the window. The draft should say "not enough information" for these. Note what you would need to look up.
5. **The story.** Does the summary make sense given the balances (for example, did the sender really empty the account)? Is the wording neutral ("may indicate"), not a conclusion?

## Approve, edit or reject

* **Approve**: every fact checks out and the summary is fair and complete enough to hand to the AML team.
* **Approve with edits**: the facts are right but the wording, emphasis or next steps need fixing. Put the corrected summary in the edit box (or the approval comment).
* **Reject**: reject the draft if it states any fact you cannot find in the data, cites a transaction that is not there, reaches a conclusion the data does not support, or misses the main reason the alert fired. Then write the case yourself.

Always add a short comment on *why*. Your name and the time are logged with every decision.

## Remember

* Never copy a number from the draft into a report without finding it in the source data.
* A clean, confident draft can still be wrong. A fast approval is not a good approval.
* Never tell a customer that their activity is being reviewed or reported.
* This prototype uses synthetic data only.

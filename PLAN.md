# Project Plan: FraudFlow, an AI assisted fraud alert review prototype

## What this is (read first)

FraudFlow is a proof of concept showing how AI and automation can take manual work off a fraud or anti money laundering (AML) investigator, while a person still makes every decision.

1. Use a public synthetic bank transaction dataset (PaySim, or the IBM synthetic AML dataset). No real customer data, ever.
2. Flag suspicious activity with two methods: clear rules for common money laundering patterns, and anomaly detection.
3. For each flagged alert, an AI agent gathers the account's recent activity and drafts a case summary plus the main fields of an Unusual Transaction Report (UTR) style form.
4. A Microsoft Power Automate flow routes each drafted case to a reviewer, who approves, edits or rejects it, and logs the decision.
5. Measure detection quality (how many known fraud cases were caught, how many false alarms) and review time (manual vs AI assisted), and show it in a Power BI dashboard.
6. Write a use case and risk document and a one page investigator guide.

## Ground rules for Claude Code (follow strictly)

* Ship a working MVP first (milestones 0 to 4), then add the rest. After each milestone, run it, show me the output, and wait for me to say continue.
* Synthetic data only. Never use, request or simulate real customer data. Say so in the README.
* A human approves every case. The AI never files, closes or sends anything on its own. Mark low confidence drafts clearly.
* Never invent numbers. Every metric in the README or resume must come from a real run, written to outputs/results.md. Use placeholders in curly braces until then. Report sample sizes.
* The AI draft must only use facts from the account data it was given, and must cite the transactions it refers to. Test this.
* Keep code simple and readable: plain variable names, small functions, short comments.
* I will be interviewed on this. After each milestone, explain every file and concept in plain language (rules vs anomaly detection, precision and recall, why human review matters, what a UTR is).
* Never commit API keys. Read them from environment variables; provide .env.example.
* Commit after each milestone with a clear message.
* If something is unclear or a better choice exists, ask me before building.

## Tech stack

* Python 3.11+: pandas, scikit-learn (Isolation Forest), SQLite, FastAPI (small API for the flow to call), pytest.
* Claude API for the case summary agent (model name in one config constant).
* Microsoft Power Automate (cloud flow) for routing and approvals. I will sign in with my Microsoft account; if Power Automate is not available, tell me and use a clearly labeled fallback (a simple approval page) without claiming Power Automate.
* Power BI Desktop for the dashboard (or Excel if Power BI is not available, labeled honestly).

## Folder structure

```
fraudflow/
  PLAN.md  README.md  requirements.txt  .env.example
  data/          raw synthetic dataset (gitignored if large) and a small sample
  detect/        rules.py, anomaly.py, evaluate.py
  agent/         case_builder.py (gathers account activity), drafter.py (AI summary), checks.py
  api/           FastAPI endpoints the Power Automate flow calls
  flow/          exported Power Automate flow and setup notes
  timing/        timing logs for manual vs AI assisted review
  dashboard/     Power BI file and exported screenshots
  docs/          USE_CASE.md, RISKS.md, INVESTIGATOR_GUIDE.md
  outputs/       results.md
  tests/
```

## Milestones

### Milestone 0: setup and learning
* One page plain language primer: how fraud and money laundering are usually detected, common patterns (structuring just under limits, rapid in and out movement, sudden spikes, many new payees), what an Unusual Transaction Report is in Canada at a high level, precision vs recall, false positives, and why human review matters in a regulated bank.
* Download the synthetic dataset and load a manageable sample into SQLite.
* Done when: the primer exists and the data loads.

### Milestone 1: flagging (MVP)
* detect/rules.py: 4 to 6 clear rules for common patterns, each with a plain reason string.
* detect/anomaly.py: Isolation Forest on simple per account features (amount vs the account's normal, transaction frequency, balance changes).
* detect/evaluate.py: using the dataset's fraud labels, report how many known fraud cases are caught (recall), how many alerts are real (precision), and false alarms per 1,000 transactions, for rules, anomaly detection, and both combined.
* Done when: outputs/results.md has real detection numbers.

### Milestone 2: case drafting agent (MVP)
* agent/case_builder.py: for an alert, gather the account's recent transactions and the reasons it was flagged.
* agent/drafter.py: the AI drafts a short case summary (what happened, why it was flagged, what to check next) and the main report fields, citing transaction IDs. It must say "not enough information" rather than guess.
* agent/checks.py: automatic checks that every number and transaction ID in the draft exists in the data; failures are marked for review.
* Done when: drafts are generated for a sample of alerts and pass the checks or are clearly marked.

### Milestone 3: API and Power Automate flow (MVP)
* api/: endpoints to list new alerts, fetch a drafted case, and record a decision (approve, edit, reject) with the reviewer's name and time.
* Power Automate cloud flow: on a schedule or trigger, fetch new drafted cases, send each to a reviewer as an approval (email or Teams), and post the decision back to the API.
* Export the flow and document the setup in flow/.
* Done when: a case goes from alert to reviewer approval and back, logged end to end. THIS IS THE MVP.

### Milestone 4: dashboard (MVP)
* Power BI dashboard: alerts per day, detection quality, decisions (approved, edited, rejected), and time per case.
* Done when: the dashboard shows real data from the pipeline.

### Milestone 5: timing study
* I review at least 15 alerts manually (from the raw data only) and 15 with FraudFlow's drafts, timing each. Log results in timing/.
* Report mean and median time per case for both, the difference, and a simple confidence interval. With a small sample, say so plainly and do not oversell.
* Also report how many drafts I approved without edits, with small edits, and rejected.
* Done when: outputs/results.md has the real timing and quality numbers.

### Milestone 6: documents and packaging
* docs/USE_CASE.md: problem, proposed solution, benefits, risks, implementation steps, success measures.
* docs/RISKS.md: privacy, AI errors and hallucination, bias in flagging, over reliance on AI, regulatory and audit needs, and how human review and logging address each.
* docs/INVESTIGATOR_GUIDE.md: one page for a non technical investigator: what the draft is, what to check, when to reject.
* README: what it is, architecture diagram, screenshots of the flow and dashboard, how to run, results table with sample sizes, limitations, "synthetic data only" notice.
* Done when: a risk team reader understands the value and the limits in 5 minutes.

## Resume lines to fill (from outputs only, never guess)

* Built a proof of concept that speeds up fraud alert review on synthetic bank transactions (PaySim): rules for common money laundering patterns plus anomaly detection flag suspicious activity, catching {R}% of known fraud cases
* Added an AI agent that pulls each flagged account's recent activity and drafts a case summary and report fields, routed through a Microsoft Power Automate flow so a reviewer approves, edits or rejects every case
* Measured manual vs AI assisted review in a Power BI dashboard (about {M} to {A} minutes per case) and wrote the use case and risks (privacy, AI errors, bias, regulation) plus an investigator guide, using only synthetic data

## Cut order if time runs out

Cut in this order and tell me what was cut so I do not claim it: the investigator guide polish, Power BI (use Excel, labeled honestly), the anomaly model (keep rules only). Never cut human review, the draft fact checks, the Power Automate flow, the timing study or the risk document.

## Things I must do myself

* Sign in to Power Automate and Power BI with my Microsoft account.
* Do the manual and AI assisted timing runs myself.
* Be able to explain rules vs anomaly detection, precision vs recall, and why a human must approve every case, without notes.
* Record a short demo video.

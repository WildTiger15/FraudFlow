# FraudFlow results

All numbers below are written by scripts from real runs on the synthetic PaySim data. Nothing here is typed in by hand. Text in {curly braces} means that step has not been run yet.

<!-- section:data -->
## 1. Data

_Generated 2026-11-04 23:38 UTC_

* Source: PaySim synthetic mobile money data (public, no real customers).
* Slice loaded: simulated hours 1 to 72 (days 1 to 3).
* Transactions loaded: 1,030,563
* Labelled fraud transactions: 890 (0.086% of all transactions)
* Distinct sending accounts: 1,030,311; distinct receiving accounts: 439,980

| Type | Transactions | Labelled fraud |
|---|---:|---:|
| CASH_IN | 223,870 | 0 |
| CASH_OUT | 369,242 | 452 |
| DEBIT | 7,004 | 0 |
| PAYMENT | 345,303 | 0 |
| TRANSFER | 85,144 | 438 |
<!-- end:data -->

<!-- section:detection -->
## 2. Detection quality

{not run yet: python -m detect.evaluate}
<!-- end:detection -->

<!-- section:drafting -->
## 3. AI case drafts

{not run yet: python -m agent.generate_drafts}
<!-- end:drafting -->

<!-- section:pipeline -->
## 4. Review decisions

{not run yet: decisions come from reviewers via the approval flow}
<!-- end:pipeline -->

<!-- section:timing -->
## 5. Timing study

{not run yet: needs >= 15 manual and >= 15 assisted timed reviews, then python -m timing.analyze}
<!-- end:timing -->

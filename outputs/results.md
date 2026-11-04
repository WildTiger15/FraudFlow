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

_Generated 2026-11-04 23:54 UTC_

* Transactions screened (TRANSFER and CASH_OUT): **454,386** of 1,030,563 loaded, over 3 simulated days.
* Labelled fraud among screened: **890** (every PaySim fraud is TRANSFER or CASH_OUT).
* Measured per transaction against PaySim's `isFraud` label. Labels are never used by the detectors.
* Rule thresholds were set by hand from AML patterns. After a first run flagged 82% of screened transactions, the ACCOUNT_DRAINED, VERY_LARGE_TRANSFER and MANY_SENDERS thresholds were revised once to keep alert volume manageable (see docs/DETECTION_NOTES.md). The labels were visible during that revision, so treat these numbers as optimistic: there is no separate held-out period yet.
* The Isolation Forest flags the most unusual 1% of screened transactions.

| Method | Alerts | Fraud caught | Recall | Precision | False alarms per 1,000 screened |
|---|---:|---:|---:|---:|---:|
| Rules (any rule) | 7,360 | 839 / 890 | 94.3% | 11.4% | 14.4 |
| Anomaly detection (Isolation Forest) | 4,544 | 30 / 890 | 3.4% | 0.7% | 9.9 |
| Combined (rules OR anomaly) | 11,383 | 847 / 890 | 95.2% | 7.4% | 23.2 |
| Both agree (rules AND anomaly) | 521 | 22 / 890 | 2.5% | 4.2% | 1.1 |
| Rule only: ACCOUNT_DRAINED | 1,484 | 812 / 890 | 91.2% | 54.7% | 1.5 |
| Rule only: PASS_THROUGH | 1,476 | 417 / 890 | 46.9% | 28.3% | 2.3 |
| Rule only: STRUCTURING | 35 | 0 / 890 | 0.0% | 0.0% | 0.1 |
| Rule only: SPIKE_VS_NORMAL | 1,856 | 38 / 890 | 4.3% | 2.0% | 4.0 |
| Rule only: VERY_LARGE_TRANSFER | 1,258 | 59 / 890 | 6.6% | 4.7% | 2.6 |
| Rule only: MANY_SENDERS | 2,138 | 5 / 890 | 0.6% | 0.2% | 4.7 |

Alerts saved for review: **11,383** (combined method). By source: rules 6,839, anomaly 4,023, both 521.
<!-- end:detection -->

<!-- section:drafting -->
## 3. AI case drafts

_Generated 2026-11-04 23:54 UTC_

* Alerts drafted in this run: **20** (random sample spread across rules / anomaly / both, seed 42).
* Drafted by: `template_no_ai` 20
* Passed all automatic fact checks: **20 / 20**
* Marked LOW CONFIDENCE (failed a check, or the drafter said low): **20 / 20**
* NOTE: `template_no_ai` drafts were made WITHOUT AI because no ANTHROPIC_API_KEY was set. They show the pipeline and checks working, not AI quality. Rerun with a key for AI drafts.
<!-- end:drafting -->

<!-- section:pipeline -->
## 4. Review decisions

{not run yet: decisions come from reviewers via the approval flow}
<!-- end:pipeline -->

<!-- section:timing -->
## 5. Timing study

{not run yet: needs >= 15 manual and >= 15 assisted timed reviews, then python -m timing.analyze}
<!-- end:timing -->

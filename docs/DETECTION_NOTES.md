# Detection notes: how the thresholds got where they are

This is the honest history of the rule thresholds, because an interviewer may ask "did you tune on the labels?"

## First run (thresholds from AML intuition only)

| Rule | First threshold | Alerts | Share of 454,386 screened |
|---|---|---:|---:|
| ACCOUNT_DRAINED | moved 95%+ of a 10,000+ balance | 138,358 | 30% |
| VERY_LARGE_TRANSFER | transfer of 1,000,000+ | 17,358 | 3.8% |
| MANY_SENDERS | receiver paid by 5+ senders in a day | 324,178 | 71% |
| All rules combined | | 374,540 | **82%** |

No investigation team can review 82% of transactions, so the rules were useless as an alert system even though they "caught" 98.2% of fraud (precision 0.2%). The reason is how PaySim simulates normal customers: many legitimate cash outs leave the balance at 0, transfers of over a million are common, and receiving accounts are shared by many senders.

## Revision (once, aimed at alert volume)

The three noisy rules were changed using **volumes of unlabelled transactions** (how often each rule fired), aiming for roughly 1% of screened transactions or less per rule:

* ACCOUNT_DRAINED: now the amount must *equal* the balance (within 1%), which is what "emptied the account" actually means; partial moves and amounts larger than the balance no longer count. About 0.3% of screened transactions.
* VERY_LARGE_TRANSFER: raised to 2,500,000, close to the 99th percentile of transfer amounts.
* MANY_SENDERS: raised to 50 different senders in a day, between the 99th and 99.9th percentile.

**Caveat:** the fraud labels were visible on screen during this revision, so the final numbers in `outputs/results.md` are optimistic. A cleaner test would set thresholds on days 1 to 3 and measure on later days that were never looked at. That is listed as a next step in the README.

## What the results say (plain language)

* **ACCOUNT_DRAINED and PASS_THROUGH do most of the work.** They match how PaySim generates fraud: empty the victim's account with a transfer, then cash out.
* **STRUCTURING caught no fraud.** That is expected: PaySim does not simulate structuring. The rule stays because it is a core real-world pattern, and it fires rarely (35 alerts).
* **The Isolation Forest is weak here** (about 3% recall). PaySim fraud does not look statistically unusual in these features: large transfers and zero balances are common among normal customers too. "Unusual" is not the same as "fraud". This is a useful interview point, not something to hide.
* **Rules AND anomaly together** is a small, higher-priority queue but misses most fraud, so the combined (OR) queue is what gets reviewed.

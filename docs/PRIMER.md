# Primer: how fraud and money laundering are detected (one page, plain language)

**Fraud** is someone taking money that is not theirs (account takeover, scams). **Money laundering** is making dirty money look clean, usually in three stages: *placement* (getting cash into the system), *layering* (moving it around to hide where it came from) and *integration* (spending it as if it were legitimate). Banks must watch for both.

## How banks usually detect it

1. **Rules (scenarios).** Plain "if this, then alert" checks written by experts, for example "cash deposits just under $10,000 more than once in a day". Easy to explain to an auditor, but they only catch patterns someone thought of, and they raise many false alarms.
2. **Anomaly detection.** A model learns what normal activity looks like and flags what is unusual, without being told what fraud looks like. It can catch new patterns, but "unusual" is not the same as "criminal", and it is harder to explain.
3. **Supervised models.** Trained on past confirmed cases. Powerful, but they need good labels and can copy past bias. FraudFlow does not use one: the labels are only used to *measure* the other two methods.

Every alert then goes to a **human investigator**, who reviews the account and decides whether it is truly suspicious.

## Common patterns

| Pattern | What it looks like | FraudFlow rule |
|---|---|---|
| Structuring ("smurfing") | Several amounts just under a reporting limit (e.g. $9,500, $9,800) to avoid a report | `STRUCTURING` |
| Rapid in and out (pass-through) | Money arrives and leaves almost immediately, so the account is just a pipe | `PASS_THROUGH` |
| Account drained | Nearly the whole balance moved out at once, typical after an account takeover | `ACCOUNT_DRAINED` |
| Sudden spike | An amount far above what this account normally moves | `SPIKE_VS_NORMAL`, `VERY_LARGE_TRANSFER` |
| Many new payers or payees | One account suddenly receiving from (or sending to) many different accounts, typical of a "money mule" | `MANY_SENDERS` |

## What an Unusual Transaction Report is (Canada, high level)

Inside a Canadian bank, an employee who sees something odd files an **Unusual Transaction Report (UTR)** to the bank's internal anti money laundering (AML) team. It is an *internal* escalation: who the customer is, which transactions, the amounts and dates, and why it looks unusual. The AML team investigates, and if there are "reasonable grounds to suspect" money laundering or terrorist financing, the bank files a **Suspicious Transaction Report (STR)** with **FINTRAC**, Canada's financial intelligence unit, as soon as practicable. Separately, cash transactions of $10,000 or more (including several in 24 hours that add up to $10,000) need a **Large Cash Transaction Report**, which is why structuring targets amounts just under $10,000. Staff must never tell ("tip off") the customer that a report was made. *This is a learning summary, not legal advice.*

FraudFlow only drafts the main UTR-style fields for a person to check. It never files anything.

## Measuring a detector: precision, recall, false positives

Imagine 1,000 transactions, 10 of them fraud. The detector raises 50 alerts, 8 of which are fraud.

* **Recall** = fraud caught / all fraud = 8 / 10 = **80%**. "Of the real fraud, how much did we catch?"
* **Precision** = real fraud among alerts / all alerts = 8 / 50 = **16%**. "When we raise an alert, how often is it right?"
* **False positives** (false alarms) = 50 − 8 = 42. We report them **per 1,000 transactions** because that is what drives investigator workload.

There is always a trade-off: catching more fraud (higher recall) usually means more false alarms (lower precision). In AML, precision of a few percent is normal, which is why investigator time is the bottleneck and why speeding up review matters.

## Why a human must review every case in a regulated bank

* **Accountability.** The bank, not a model, is legally responsible for what is reported to FINTRAC. A named person must make and own the decision.
* **AI makes mistakes.** A language model can state a fact that is not in the data ("hallucination"). FraudFlow checks every number and transaction ID in a draft, but a person is the final check.
* **Context.** The reviewer can know things the data does not show (a known business, a customer call).
* **Fairness and audit.** Regulators and auditors expect to see who decided what, when, and why. FraudFlow logs every decision with the reviewer's name and time.
* **Harm.** A wrong report can hurt an innocent customer; a missed one can help a criminal. Both deserve human judgment.

## About the data

FraudFlow uses **PaySim**, a public *synthetic* (simulated) dataset of mobile money transactions. There are no real customers in it. Each row has a type (PAYMENT, TRANSFER, CASH_OUT, CASH_IN, DEBIT), an amount, sender and receiver balances before and after, and an `isFraud` label. In PaySim, fraud only happens in TRANSFER and CASH_OUT (money leaving an account), so FraudFlow screens those two types. Two quirks to know: almost every sending account appears only once, so per-sender history is thin; and receiving balances are sometimes not updated, which some rules pick up on. Both are limits of the simulation, not of real banking data.

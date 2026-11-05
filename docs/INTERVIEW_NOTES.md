# Interview notes: every file and concept in plain language

Read `PRIMER.md` first for the background (patterns, UTR, precision and recall, why humans review).

## The pipeline in one breath

PaySim transactions go into SQLite → rules and an Isolation Forest flag suspicious ones → for a sample of alerts, the case builder gathers the facts → Claude drafts a summary and report fields → automatic checks verify every number and ID → the API serves cases to a reviewer (Power Automate approval or the fallback page) → the reviewer approves, edits or rejects, and the decision is logged → the dashboard and `outputs/results.md` show detection quality, decisions and review time.

## Milestone 0: setup and data

| File | What it does |
|---|---|
| `config.py` | All settings in one place: file paths, the 3-day slice, the screened types, the Claude model name, sample size. Also reads `.env`. |
| `db.py` | Opens the SQLite file and creates the `alerts`, `cases` and `decisions` tables. |
| `results.py` | Writes one section of `outputs/results.md` at a time, so every number there comes from a script. |
| `data/download_data.py` | Downloads PaySim (synthetic, about 490 MB). |
| `data/load_data.py` | Loads simulated hours 1 to 72 into SQLite, gives each row a stable ID like `T0000086`, adds day and hour, saves a 5,000-row sample. |

**Why a time slice, not random rows?** The rules need each account's earlier transactions. Random rows would scatter an account's history.

## Milestone 1: flagging

| File | What it does |
|---|---|
| `detect/rules.py` | Six rules, each a small function returning True/False per transaction, with a reason string. Thresholds are constants at the top. `add_account_history` computes each account's average of *earlier* transactions only, so no rule looks into the future. |
| `detect/anomaly.py` | Builds 8 simple features (size, share of balance moved, how the receiver's balance changed, amount vs the account's usual, receiver activity that day, hour) and fits an Isolation Forest. The top 1% most unusual are flagged. |
| `detect/evaluate.py` | Runs both, compares with the `isFraud` labels, and reports recall, precision and false alarms per 1,000 for each method, rules alone, anomaly alone, OR and AND. Saves alerts. |

**Rules vs anomaly detection.** Rules are written by people from known patterns: easy to explain, but they only find what someone thought of. Anomaly detection learns "normal" from the data and flags what is different: it can find new things, but "unusual" is not "criminal". Here the rules did far better because PaySim's fraud follows a fixed pattern (empty the account, pass it through, cash out), while lots of normal PaySim customers also make large transfers.

**How an Isolation Forest works.** It builds many random trees that split the data on random features at random values. An unusual point gets separated (isolated) after very few splits; a normal point sits in a crowd and takes many splits. Average path length → anomaly score. It is unsupervised: it never sees the labels.

**The threshold story** (be upfront): the first thresholds flagged 82% of transactions; three were revised once to bring volume down, and the labels were visible then. See `DETECTION_NOTES.md`. A cleaner test is a held-out period.

## Milestone 2: the drafting agent

| File | What it does |
|---|---|
| `agent/case_builder.py` | For one alert, collects the flagged transaction, up to 20 recent transactions for each account in the last 72 hours, and pre-computed totals. Never includes the fraud labels. |
| `agent/drafter.py` | Sends those facts to Claude with strict rules (use only these facts, copy numbers exactly, cite IDs, say "not enough information", neutral wording, low confidence if unsure) and asks for JSON in a fixed schema. Without an API key it uses a template with no AI, labelled `template_no_ai`. |
| `agent/checks.py` | Pulls every transaction ID and every number out of the draft and checks each one exists in the facts. Also checks the flagged transaction is cited and key fields are filled. Any failure → LOW CONFIDENCE. |
| `agent/generate_drafts.py` | Picks a random sample of alerts, drafts, checks, saves to `cases`, and writes example drafts to `outputs/example_drafts/`. |

**Why pre-compute totals?** Language models are weaker at arithmetic than at writing. If the facts already contain totals, the model only has to copy, and the check can verify the copy.

**What the checks cannot catch:** a correct number used to tell a wrong story. That is why a person still reviews.

## Milestone 3: API and flow

| File | What it does |
|---|---|
| `api/main.py` | FastAPI app: list alerts, list cases waiting for review, fetch one case (draft + facts + checks), record a decision (approve/edit/reject, reviewer name, UTC time, channel). One decision per case. Optional API key. |
| `api/review_page.html` | The **fallback** approval page, used when Power Automate is not set up. Labelled as such. Shows the draft beside the source transactions. |
| `flow/flow_definition.json`, `flow/SETUP.md` | The Power Automate design: every 15 minutes get pending cases, start an approval for each, post the outcome back. Hand-written, not yet built in your tenant. |
| `flow/smoke_test.py` | Replays the flow's HTTP calls against a copy of the database to prove the plumbing works end to end. |

## Milestone 4: dashboard

`dashboard/build_dashboard.py` reads the database and timing log and makes CSVs for Power BI, an Excel workbook (labelled fallback) and a PNG. Panels with no data say so.

## Milestone 5: timing study

`timing/review_session.py` shows a case and times you. Each case is randomly assigned to manual or assisted so you never see the same case twice. `timing/analyze.py` reports mean and median minutes, the difference, a 95% confidence interval (Welch's t-interval, which does not assume both groups vary equally), and how often drafts were approved, edited or rejected.

**What a confidence interval means here:** if we repeated this study many times, 95% of intervals built this way would contain the true average difference. With 15 cases each, it will be wide; say so.

## Showcase

`showcase/` builds a small read-only demo database and a landing page that the Render web service serves, so anyone can browse real alerts, drafts and metrics without being able to record decisions.

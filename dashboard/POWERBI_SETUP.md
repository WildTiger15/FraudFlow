# Power BI dashboard: setup notes

**Status: Power BI version not built yet.** Power BI Desktop (Windows, free) needs your Microsoft sign-in, so the dashboard currently exists as the clearly labelled **Excel fallback** (`FraudFlow_dashboard_EXCEL_FALLBACK.xlsx`) and a matplotlib image (`screenshots/dashboard.png`). Both are built from the same pipeline data by `python -m dashboard.build_dashboard`. Do not call them Power BI.

## Data to load (rebuilt every time you run the script)

| File in `dashboard/data/` | Columns | Visual |
|---|---|---|
| `alerts_per_day.csv` | day, rules, anomaly, both | Stacked column: alerts per simulated day by source |
| `detection_quality.csv` | method, alerts, fraud_caught, total_fraud, recall, precision, false_alarms_per_1000 | Clustered bar: recall and precision by method; table with sample sizes |
| `decision_counts.csv` / `decisions.csv` | decision, cases / case_id, decision, reviewer, channel, review_seconds, decided_at | Column: approve / edit / reject; table: decision log |
| `timing.csv` | case_id, alert_id, mode, seconds, decision, reviewer, ... | Box or dot plot: minutes per case, manual vs AI assisted; cards: mean and median |

## Build it (about 20 minutes)

1. Run the pipeline steps, then `python -m dashboard.build_dashboard`.
2. Power BI Desktop > **Get data > Text/CSV**, load each file above (or **Get data > Folder** on `dashboard/data`).
3. In `alerts_per_day`, select rules/anomaly/both > **Transform > Unpivot columns** so you have day, source, alerts.
4. Add a measure for minutes: `Minutes = AVERAGE(timing[seconds]) / 60`, and `Median minutes = MEDIAN(timing[seconds]) / 60`.
5. Make four visuals on one page: stacked column (alerts per day), clustered bar (recall, precision, format as %), column (decisions), box/dot or clustered column (minutes by mode) plus two cards.
6. Add a text box: "Synthetic PaySim data only. Every case is approved by a person."
7. Save as `dashboard/FraudFlow.pbix`, export a PNG to `dashboard/screenshots/powerbi.png`, and only then update the README to say Power BI.

After new reviews or timing runs, rerun the script and press **Refresh** in Power BI.

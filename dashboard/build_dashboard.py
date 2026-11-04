"""Build the FraudFlow dashboard from the pipeline's real data.

Power BI Desktop is not available in this environment, so this script makes:
  * dashboard/data/*.csv          clean tables to load into Power BI (see POWERBI_SETUP.md)
  * dashboard/FraudFlow_dashboard_EXCEL_FALLBACK.xlsx   Excel version with native charts (labelled as the fallback)
  * dashboard/screenshots/dashboard.png                 picture of the same four panels
Panels: alerts per day, detection quality, reviewer decisions, time per case.
Empty panels say "no data yet" instead of showing made-up numbers.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Font
from openpyxl.utils.dataframe import dataframe_to_rows

from config import ROOT
from db import connect

OUT = ROOT / "dashboard"
TIMING_LOG = ROOT / "timing" / "timing_log.csv"
SMOKE_TEST_MARK = "smoke test"

# Reference categorical palette, fixed order (dataviz skill): blue, orange, aqua.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SOURCE_COLORS = {"rules": BLUE, "anomaly": ORANGE, "both": AQUA}
MAIN_METHODS = ["Rules (any rule)", "Anomaly detection (Isolation Forest)",
                "Combined (rules OR anomaly)", "Both agree (rules AND anomaly)"]


def load_tables(conn):
    alerts = pd.read_sql("SELECT day, flagged_by, COUNT(*) AS alerts FROM alerts GROUP BY day, flagged_by", conn)
    alerts_per_day = alerts.pivot(index="day", columns="flagged_by", values="alerts").fillna(0).astype(int)
    alerts_per_day = alerts_per_day.reindex(columns=["rules", "anomaly", "both"], fill_value=0).reset_index()

    metrics = pd.read_sql("SELECT method, alerts, fraud_caught, total_fraud, recall, precision, "
                          "false_alarms_per_1000 FROM detection_metrics", conn)

    decisions = pd.read_sql("SELECT case_id, decision, reviewer, channel, review_seconds, decided_at FROM decisions", conn)
    decisions = decisions[~decisions["reviewer"].str.lower().str.contains(SMOKE_TEST_MARK)]
    decision_counts = (decisions["decision"].value_counts().reindex(["approve", "edit", "reject"], fill_value=0)
                       .rename_axis("decision").reset_index(name="cases"))

    timing = pd.read_csv(TIMING_LOG) if TIMING_LOG.exists() else pd.DataFrame(columns=["mode", "seconds"])
    return {"alerts_per_day": alerts_per_day, "detection_quality": metrics,
            "decisions": decisions, "decision_counts": decision_counts, "timing": timing}


def style_axes(ax, title):
    ax.set_title(title, loc="left", fontsize=12, color=INK, fontweight="bold")
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def no_data(ax, message):
    ax.text(0.5, 0.5, message, ha="center", va="center", color=INK_2, fontsize=10, wrap=True,
            transform=ax.transAxes)
    ax.set_xticks([])
    ax.set_yticks([])


def plot_alerts(ax, apd):
    style_axes(ax, "Alerts per simulated day, by source")
    bottom = pd.Series(0, index=apd.index)
    for source, color in SOURCE_COLORS.items():
        ax.bar(apd["day"].astype(str), apd[source], bottom=bottom, color=color, label=source,
               edgecolor=SURFACE, linewidth=2, width=0.6)
        bottom += apd[source]
    for x, total in zip(apd["day"].astype(str), bottom):
        ax.text(x, total, f"{total:,}", ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_xlabel("Simulated day", color=INK_2)
    ax.legend(frameon=False, fontsize=9, ncols=3, loc="upper right")


def plot_detection(ax, metrics):
    style_axes(ax, "Detection quality (PaySim labels)")
    m = metrics.set_index("method").loc[MAIN_METHODS]
    names = ["Rules", "Anomaly", "Rules OR anomaly", "Rules AND anomaly"]
    y = range(len(names))
    ax.barh([i + 0.2 for i in y], m["recall"] * 100, height=0.38, color=BLUE, label="Recall", edgecolor=SURFACE)
    ax.barh([i - 0.2 for i in y], m["precision"] * 100, height=0.38, color=ORANGE, label="Precision",
            edgecolor=SURFACE)
    for i, (r, p) in enumerate(zip(m["recall"], m["precision"])):
        ax.text(r * 100 + 1, i + 0.2, f"{r:.1%}", va="center", fontsize=8, color=INK)
        ax.text(p * 100 + 1, i - 0.2, f"{p:.1%}", va="center", fontsize=8, color=INK)
    ax.set_yticks(list(y), names)
    ax.invert_yaxis()
    ax.set_xlim(0, 110)
    ax.set_xlabel("%", color=INK_2)
    ax.grid(axis="x", color=GRID)
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, fontsize=9, loc="lower right")


def plot_decisions(ax, counts):
    style_axes(ax, "Reviewer decisions")
    if counts["cases"].sum() == 0:
        no_data(ax, "No reviewer decisions yet.\nDecisions appear here after a person reviews\ncases in the approval flow.")
        return
    ax.bar(counts["decision"], counts["cases"], color=BLUE, width=0.5)
    for x, v in zip(counts["decision"], counts["cases"]):
        ax.text(x, v, str(v), ha="center", va="bottom", fontsize=9, color=INK)


def plot_timing(ax, timing):
    style_axes(ax, "Review time per case (minutes)")
    if timing.empty:
        no_data(ax, "No timing data yet.\nRun the timing study (timing/README.md):\n15+ manual and 15+ AI assisted reviews.")
        return
    for i, (mode, color) in enumerate((("manual", BLUE), ("assisted", ORANGE))):
        minutes = timing.loc[timing["mode"] == mode, "seconds"] / 60
        ax.scatter([i] * len(minutes), minutes, color=color, s=40, alpha=0.8, edgecolor=SURFACE)
        if len(minutes):
            ax.hlines(minutes.median(), i - 0.25, i + 0.25, color=INK, linewidth=2)
            ax.text(i + 0.28, minutes.median(), f"median {minutes.median():.1f}", va="center", fontsize=8, color=INK)
    ax.set_xticks([0, 1], [f"Manual (n={(timing['mode'] == 'manual').sum()})",
                           f"AI assisted (n={(timing['mode'] == 'assisted').sum()})"])
    ax.set_xlim(-0.6, 1.9)


def save_png(tables):
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), facecolor=SURFACE)
    plot_alerts(axes[0, 0], tables["alerts_per_day"])
    plot_detection(axes[0, 1], tables["detection_quality"])
    plot_decisions(axes[1, 0], tables["decision_counts"])
    plot_timing(axes[1, 1], tables["timing"])
    fig.suptitle("FraudFlow dashboard  ·  synthetic PaySim data only  ·  image from the Excel/matplotlib fallback, not Power BI",
                 x=0.01, ha="left", fontsize=11, color=INK_2)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    (OUT / "screenshots").mkdir(parents=True, exist_ok=True)
    path = OUT / "screenshots" / "dashboard.png"
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)
    return path


def add_sheet(wb, title, df):
    ws = wb.create_sheet(title)
    for row in dataframe_to_rows(df, index=False, header=True):
        ws.append(row)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    return ws


def bar_chart(title, ws, data_cols, cat_col, n_rows, anchor, stacked=False, horizontal=False):
    chart = BarChart()
    chart.type = "bar" if horizontal else "col"
    chart.title = title
    if stacked:
        chart.grouping, chart.overlap = "stacked", 100
    chart.add_data(Reference(ws, min_col=data_cols[0], max_col=data_cols[1], min_row=1, max_row=n_rows + 1),
                   titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=cat_col, min_row=2, max_row=n_rows + 1))
    chart.height, chart.width = 8, 16
    for series, color in zip(chart.series, (BLUE, ORANGE, AQUA)):
        series.graphicalProperties.solidFill = color[1:]
    ws.add_chart(chart, anchor)


def save_excel(tables):
    wb = Workbook()
    about = wb.active
    about.title = "About"
    for line in ["FraudFlow dashboard - EXCEL FALLBACK (Power BI was not available when this was built)",
                 "Synthetic PaySim data only. No real customer data.",
                 "Built by dashboard/build_dashboard.py from the pipeline database; numbers are not typed by hand.",
                 "Empty sheets mean that step has not produced data yet (no reviewer decisions / no timing study).",
                 "To build the Power BI version, follow dashboard/POWERBI_SETUP.md using the CSVs in dashboard/data/."]:
        about.append([line])
    about["A1"].font = Font(bold=True, size=13)

    apd = tables["alerts_per_day"]
    ws = add_sheet(wb, "Alerts per day", apd)
    bar_chart("Alerts per simulated day, by source", ws, (2, 4), 1, len(apd), "F2", stacked=True)

    dq = tables["detection_quality"]
    ws = add_sheet(wb, "Detection quality", dq)
    main = dq[dq["method"].isin(MAIN_METHODS)][["method", "recall", "precision"]]
    start = len(dq) + 4
    ws.cell(row=start - 1, column=1, value="Chart data (main methods)").font = Font(bold=True)
    chart_ws = wb.create_sheet("Detection chart")
    for row in dataframe_to_rows(main, index=False, header=True):
        chart_ws.append(row)
    bar_chart("Recall and precision by method", chart_ws, (2, 3), 1, len(main), "E2", horizontal=True)

    dc = tables["decision_counts"]
    ws = add_sheet(wb, "Decisions", dc)
    if dc["cases"].sum():
        bar_chart("Reviewer decisions", ws, (2, 2), 1, len(dc), "D2")
    else:
        ws["D2"] = "No reviewer decisions yet."
    add_sheet(wb, "Decision log", tables["decisions"])

    timing = tables["timing"]
    if timing.empty:
        ws = wb.create_sheet("Time per case")
        ws["A1"] = "No timing data yet. Run the timing study (timing/README.md)."
    else:
        summary = (timing.assign(minutes=timing["seconds"] / 60).groupby("mode")["minutes"]
                   .agg(["count", "mean", "median"]).round(2).reset_index())
        ws = add_sheet(wb, "Time per case", summary)
        bar_chart("Mean and median minutes per case", ws, (3, 4), 1, len(summary), "G2")
    path = OUT / "FraudFlow_dashboard_EXCEL_FALLBACK.xlsx"
    wb.save(path)
    return path


def save_csvs(tables):
    (OUT / "data").mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(OUT / "data" / f"{name}.csv", index=False)


def main():
    tables = load_tables(connect())
    save_csvs(tables)
    print("Wrote", save_png(tables))
    print("Wrote", save_excel(tables))
    print("Wrote CSVs to", OUT / "data")


if __name__ == "__main__":
    main()

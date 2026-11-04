"""Summarise the timing study and the reviewer decisions into outputs/results.md.

Reports mean and median minutes per case for manual vs AI assisted, the difference, a 95%
confidence interval for the difference in means (Welch's t-interval), and how the AI drafts
were judged. With small samples it says so plainly.
"""
import pandas as pd
from scipy import stats

from db import connect
from results import write_section
from timing.review_session import LOG

MIN_PER_MODE = 15
SMOKE_TEST_MARK = "smoke test"


def welch_interval(a, b, level=0.95):
    """Confidence interval for mean(a) - mean(b) without assuming equal variances."""
    diff = a.mean() - b.mean()
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    dof = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    margin = stats.t.ppf((1 + level) / 2, dof) * (va + vb) ** 0.5
    return diff, diff - margin, diff + margin


def timing_markdown(log):
    manual = log.loc[log["mode"] == "manual", "seconds"] / 60
    assisted = log.loc[log["mode"] == "assisted", "seconds"] / 60
    lines = ["## 5. Timing study", "",
             f"* Cases timed: manual **{len(manual)}**, AI assisted **{len(assisted)}** "
             f"(target at least {MIN_PER_MODE} each). One reviewer: {', '.join(sorted(log['reviewer'].unique()))}."]
    if len(manual) < 2 or len(assisted) < 2:
        lines.append("* {not enough timed reviews yet to compare: need at least 2 per mode, target 15}")
        return "\n".join(lines)
    diff, low, high = welch_interval(manual, assisted)
    lines += [
        "",
        "| | Manual | AI assisted |",
        "|---|---:|---:|",
        f"| Mean minutes per case | {manual.mean():.1f} | {assisted.mean():.1f} |",
        f"| Median minutes per case | {manual.median():.1f} | {assisted.median():.1f} |",
        f"| Cases | {len(manual)} | {len(assisted)} |",
        "",
        f"* Difference in means (manual minus assisted): **{diff:.1f} minutes** per case, "
        f"95% confidence interval **{low:.1f} to {high:.1f}** (Welch t-interval).",
    ]
    if min(len(manual), len(assisted)) < MIN_PER_MODE:
        lines.append(f"* WARNING: fewer than {MIN_PER_MODE} cases in a mode. Treat this as a rough first look.")
    lines.append("* Caveats: one reviewer, who also built the tool; different cases in each mode (random assignment); "
                 "synthetic data. This is a small pilot, not proof of production time savings.")
    judged = log[log["mode"] == "assisted"]
    if len(judged):
        counts = {
            "approved without edits": int((judged["decision"] == "approve").sum()),
            "approved with small edits": int(((judged["decision"] == "edit") & (judged["edit_size"] == "small")).sum()),
            "approved with large edits": int(((judged["decision"] == "edit") & (judged["edit_size"] == "large")).sum()),
            "draft rejected": int((judged["decision"] == "reject").sum()),
        }
        lines.append("* AI assisted draft outcomes (n=" + str(len(judged)) + "): "
                     + "; ".join(f"{k} {v}" for k, v in counts.items()) + ".")
        drafted_by = pd.read_sql("SELECT case_id, drafted_by FROM cases", connect())
        merged = judged.merge(drafted_by, on="case_id", how="left")
        lines.append("* Drafts used in assisted reviews were made by: "
                     + ", ".join(f"`{k}` {v}" for k, v in merged["drafted_by"].value_counts().items()) + ".")
    return "\n".join(lines)


def pipeline_markdown(conn):
    decisions = pd.read_sql("SELECT * FROM decisions", conn)
    decisions = decisions[~decisions["reviewer"].str.lower().str.contains(SMOKE_TEST_MARK)]
    cases = pd.read_sql("SELECT status FROM cases", conn)
    lines = ["## 4. Review decisions", "",
             f"* Drafted cases: {len(cases)}; still waiting for a person: {(cases['status'] == 'pending_review').sum()}",
             f"* Human decisions logged: **{len(decisions)}**"]
    if len(decisions):
        lines.append("* By decision: " + ", ".join(f"{k} {v}" for k, v in decisions["decision"].value_counts().items()))
        lines.append("* By channel: " + ", ".join(f"{k} {v}" for k, v in decisions["channel"].value_counts().items()))
    return "\n".join(lines)


def main():
    conn = connect()
    write_section("pipeline", pipeline_markdown(conn))
    if LOG.exists():
        text = timing_markdown(pd.read_csv(LOG))
        write_section("timing", text)
        print(text)
    else:
        print(f"No timing log yet at {LOG}. Run timing.review_session first.")


if __name__ == "__main__":
    main()

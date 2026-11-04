"""Writes named sections into outputs/results.md so each script owns its own part.

Every number in results.md is written by a script from a real run. Sections that
have not been run yet keep their {placeholder} text.
"""
import re
from datetime import datetime, timezone

from config import RESULTS_MD

SECTION_ORDER = ["data", "detection", "drafting", "pipeline", "timing"]

PLACEHOLDERS = {
    "data": "## 1. Data\n\n{not run yet: python -m data.load_data}",
    "detection": "## 2. Detection quality\n\n{not run yet: python -m detect.evaluate}",
    "drafting": "## 3. AI case drafts\n\n{not run yet: python -m agent.generate_drafts}",
    "pipeline": "## 4. Review decisions\n\n{not run yet: decisions come from reviewers via the approval flow}",
    "timing": "## 5. Timing study\n\n{not run yet: needs >= 15 manual and >= 15 assisted timed reviews, "
              "then python -m timing.analyze}",
}


def _read_sections():
    sections = dict(PLACEHOLDERS)
    if RESULTS_MD.exists():
        text = RESULTS_MD.read_text(encoding="utf-8")
        for name, body in re.findall(r"<!-- section:(\w+) -->\n(.*?)<!-- end:\1 -->", text, re.S):
            sections[name] = body.strip()
    return sections


def write_section(name, markdown):
    """Replace one section of results.md and keep the others as they are.

    `markdown` must start with its own '## heading' line.
    """
    sections = _read_sections()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    heading, _, body = markdown.strip().partition("\n")
    sections[name] = f"{heading}\n\n_Generated {stamp}_\n{body}"
    parts = [
        "# FraudFlow results\n",
        "All numbers below are written by scripts from real runs on the synthetic PaySim data. "
        "Nothing here is typed in by hand. Text in {curly braces} means that step has not been run yet.\n",
    ]
    for key in SECTION_ORDER:
        parts.append(f"<!-- section:{key} -->\n{sections[key]}\n<!-- end:{key} -->\n")
    RESULTS_MD.parent.mkdir(exist_ok=True)
    RESULTS_MD.write_text("\n".join(parts), encoding="utf-8")

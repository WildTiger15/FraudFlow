"""Central settings for FraudFlow. Change values here, not inside the code."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_CSV = ROOT / "data" / "raw" / "paysim.csv"
SAMPLE_CSV = ROOT / "data" / "sample" / "paysim_sample.csv"
DB_PATH = Path(os.environ.get("FRAUDFLOW_DB", ROOT / "data" / "fraudflow.db"))
RESULTS_MD = ROOT / "outputs" / "results.md"

# PaySim "step" = 1 simulated hour. We load the first 3 simulated days.
SAMPLE_MAX_STEP = 72

# Only money-leaving transaction types are screened (see docs/PRIMER.md).
SCREENED_TYPES = ("TRANSFER", "CASH_OUT")

# Claude model used by the case drafting agent (one constant, per the plan).
CLAUDE_MODEL = "claude-opus-5-5"

# How many alerts get an AI draft in a run (drafting every alert costs money).
DRAFT_SAMPLE_SIZE = 20
RANDOM_SEED = 42


def load_dotenv(path=ROOT / ".env"):
    """Tiny .env reader so we do not need an extra package."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_dotenv()

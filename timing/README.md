# Timing study (you run this, about 2 hours)

Goal: compare how long a case takes **manually** (raw data only) vs **AI assisted** (raw data + FraudFlow draft). Nothing here is filled in until you do the reviews: no numbers are invented.

1. Set `ANTHROPIC_API_KEY` in `.env` so drafts are real AI drafts, then draft enough cases:
   ```
   python -m agent.generate_drafts --count 40
   ```
   Each case is randomly assigned (fixed seed) to manual or assisted, about half each, so 40 drafts give roughly 20 per mode.
2. Do at least 15 of each. Mix the order (for example 5 manual, 5 assisted, repeat) so getting faster with practice does not favour one mode:
   ```
   python -m timing.review_session --mode manual --reviewer "Your Name" --count 5
   python -m timing.review_session --mode assisted --reviewer "Your Name" --count 5
   ```
   * Manual: read the alert and transactions, write a 2 to 3 sentence summary citing transaction IDs in your notes, then escalate or close.
   * Assisted: read the draft against the same transactions, then approve as is, small edits, large edits, or reject the draft.
3. Analyse and refresh the dashboard:
   ```
   python -m timing.analyze
   python -m dashboard.build_dashboard
   ```
   This writes mean and median minutes, the difference with a 95% confidence interval, and the approve/edit/reject counts to `outputs/results.md`.

Be honest in interviews about the limits: one reviewer (you) who also built the tool, a small sample, synthetic data.

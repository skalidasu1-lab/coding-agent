# Pilot checklist

Purpose: find design and technical problems before the main study, and estimate
variability for the sample-size calculation. Pilot data are NOT pooled with the main
study, because the design may change after the pilot.

## Before the pilot
- [ ] Ethics approval received (the pilot is also human-subjects research).
- [ ] `uv run study/preflight.py` shows PASS on every line.
- [ ] `uv run study/simulate.py --limit 1` (or a local-model run) completes end to end.
- [ ] Surveys built; participant ID field works; consent form ready.
- [ ] The model, version and temperature are written in the design document.
- [ ] Practice task works with a real person (they understand /run, /files, /done).

## Running the pilot (3 to 5 people)
- [ ] Use a separate folder: `--data-dir study_data/pilot`.
- [ ] Sit with each participant. Note confusion, questions they ask you, and any wording they misread.
- [ ] Time each session. Note anything the assistant did that looked unsafe.
- [ ] Check `suspicious` flags in the log after every session.

## What to check afterwards
- [ ] Completion: at least 70% of tasks finish without a technical failure.
- [ ] Length: a full session takes 75 minutes or less.
- [ ] Task difficulty: for each task, the pass rate is not stuck at 0% or 100% across conditions.
- [ ] Room to improve: under `never_ask` with vague prompts, the pass rate is clearly below 100%.
- [ ] Manipulation: vague first prompts mention fewer requirements than clear ones (hand-code a sample).
- [ ] Questions: the agent asks under `always_ask`, rarely under `ask_when_unclear` with clear prompts, never under `never_ask`.
- [ ] Logs: every field in the session records is filled; tokens look plausible.
- [ ] Analysis: `uv run study/analysis.py --data study_data/pilot/sessions.jsonl` runs without errors.
- [ ] Sample size: read the power table; decide the target N.

## Decide
- If every box above is ticked: freeze the design (record the commit) and start the main study.
- Otherwise: fix the problem, write it in the deviations log of the design document, and repeat with new participants.
# Session protocol

Before each day:
1. Run `uv run study/preflight.py`. Every line must say PASS.
2. Close personal apps and files. Use a machine or account with nothing private on it.
3. Confirm the endpoint (local model, or the hosted model named in the design).

During a session:
- The experimenter stays in the room and the participant uses only the session terminal.
- The participant never sees the API key, `.env`, or the task bank.

After each session:
- Check `suspicious` in the log. Review any flagged session by hand and record the outcome.
- Back up `study_data/` somewhere private. Never commit it.

Record every deviation in the deviations log of the design document.
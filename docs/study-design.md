# Study design (to be frozen before any data collection)

Frozen on: ____  Commit: ____
After freezing, changes go in the Deviations log at the end, never silently.

## 1. Research question
For non-expert college students using an LLM coding agent on underspecified requests,
how does letting the agent ask clarifying questions affect total tokens consumed
per task, compared with an agent that proceeds on its best guess?

## 2. Hypotheses
- H1a: On vague prompts, asking lowers total tokens per task (it prevents re-prompting).
- H1b (competing): The tokens spent on questions and answers outweigh the savings.
- H2: On vague prompts, asking raises the success rate (hidden tests).
- H3: On clear prompts, always asking adds tokens without improving success.

## 3. Design
Within-subjects, 2 x 3: Clarity (vague, clear) x Policy (never_ask, ask_when_unclear,
always_ask) = 6 cells. Each participant completes 6 tasks, one per cell.
- Policies are set by one paragraph in the system prompt; the three paragraphs have
  similar length (report their token counts). Max 3 questions per task.
- Clarity is manipulated by how the student is told to write the first prompt:
  vague = "one short sentence, as in a quick chat";
  clear = "describe the whole program, listing every requirement".
  Every student sees the full intent card in all cells.
- Manipulation check: number of requirements stated in the first prompt, coded from logs.
- Counterbalancing: Williams design (study/design.py): 6 sequences, participants
  assigned to sequences in sign-up order. Task order is fixed; the cell varies.

## 4. Tasks
6 tasks of comparable difficulty. Each has: an intent card, 2 to 3 deliberate
ambiguities, hidden tests (stored outside the folder the agent can access), and
canned answers for a scripted student. Pilot checks difficulty.

## 5. Session procedure (about 60 to 75 minutes)
1. Consent. 2. Pre-survey (prior AI and coding use). 3. Warm-up task (not analysed).
4. Six tasks. 5. After each task: satisfaction rating (1 to 5). 6. Post-survey.
A task ends when the student types "done", after 8 student prompts, or after 12 minutes.

## 6. Agent configuration (frozen at v1.0)
Model: ____ (provider, exact version, date checked). Temperature: ____.
Tools offered: ____. Max agent rounds per run: 10.

## 7. Measures
- Primary: total tokens per task (all rounds, including questions and answers);
  success (all hidden tests pass).
- Derived: tokens per solved task = total tokens / number of solved tasks, per cell.
- Secondary: student prompts, agent rounds, questions asked, time, satisfaction.

## 8. Participants
Recruit 40 to reach 30. Age 18+, enrolled college students, no professional
prompt-engineering experience. Compensation: ____. Final N from the pilot power analysis.

## 9. Analysis plan
- log(total tokens) ~ policy * clarity + (1 | participant) + (1 | task).
- Success: logistic mixed model with the same structure.
- Holm correction for the pre-specified contrasts. Report effect sizes and 95% CIs.
- Technical failures: the task is excluded and reported, with reasons.
- Separate simulation arm with scripted students, labelled as such.
- All results are reported, including null ones.

## 10. Data handling
Anonymous participant IDs, no names. Logs stay in study_data/ (git-ignored).
Prompts are screened for personal details before any release.

## Deviations log
(empty)
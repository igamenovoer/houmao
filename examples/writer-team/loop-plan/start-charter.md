# Start Charter: Story Chapter Loop

Run id: `mars-arrival-2030-r1`

Plan: `loop-plan/story-chapter-loop.md`

Master: `alex-story`

Workers:

- `alex-char`
- `alex-review`

Chapter count: `10`

Output root: `story/`

Premise: A human team finally arrives on Mars in 2030. There are five crew members, three men and two women, all between roughly 20 and 35 years old, with different occupations and responsibilities. The story should follow the arrival and the consequences chapter by chapter.

Instructions for `alex-story`:

1. Accept this run using the pairwise loop plan.
2. Use `story/chapters/`, `story/characters/`, and `story/review/` for all persistent artifacts.
3. For each chapter, draft first, ask `alex-char` for character profile work, revise in place, ask `alex-review` for review, address review findings, then finalize the chapter.
4. Keep the user outside the execution loop. Report status only when asked.
5. When all 10 chapters are finalized, return the chapter paths, profile paths, review paths, and a short coherence note.

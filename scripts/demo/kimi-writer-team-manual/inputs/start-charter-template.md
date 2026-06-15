# Start Charter: Kimi Writer Team Manual Demo

Run id: `__RUN_ID__`

Plan: `loop-plan/story-chapter-loop.md`

Master: `alex-story`

Workers:

- `alex-char`
- `alex-review`

Chapter count: `__CHAPTER_COUNT__`

Output root: `story/`

Premise: A human team finally arrives on Mars in 2030. There are five crew members, three men and two women, all between roughly 20 and 35 years old, with different occupations and responsibilities. The story should follow the arrival and the consequences chapter by chapter.

Instructions for `alex-story`:

1. Accept this run using the tree-loop plan.
2. Use `story/chapters/`, `story/characters/`, and `story/review/` for all persistent artifacts.
3. For each chapter, draft first, ask `alex-char` for character profile work by mailbox, revise in place, ask `alex-review` for review by mailbox, address review findings, then finalize the chapter.
4. Keep the user outside the execution loop. Report status only when asked.
5. When all __CHAPTER_COUNT_WORD__ chapters are finalized, return the chapter paths, profile paths, review paths, and a short coherence note.


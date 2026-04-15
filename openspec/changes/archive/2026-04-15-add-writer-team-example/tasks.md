## 1. Example Structure

- [x] 1.1 Create `examples/writer-team/` with README, prompt, loop-plan, story artifact, and ignore-file structure.
- [x] 1.2 Add placeholder files for `story/chapters/`, `story/characters/`, and `story/review/` without committing generated story content.
- [x] 1.3 Add ignore rules that keep local `.houmao/` state, mailbox contents, credentials, logs, and generated story artifacts out of source control.

## 2. Agent Source Material

- [x] 2.1 Add `story-writer`, `character-designer`, and `story-reviewer` prompt files adapted from the proven `../agentsys2` roles.
- [x] 2.2 Ensure the prompts define distinct master writer, character worker, and reviewer responsibilities.
- [x] 2.3 Ensure the prompt files can be used directly with `houmao-mgr project easy specialist create --system-prompt-file`.

## 3. Loop Plan and Start Charter

- [x] 3.1 Add a pairwise loop plan that designates `alex-story` as master and `alex-char` / `alex-review` as named workers.
- [x] 3.2 Define the chapter pipeline: draft, character-profile delegation, revision, review delegation, review-fix pass, and advance.
- [x] 3.3 Use only relative artifact paths under `story/chapters/`, `story/characters/`, `story/review/`, and optional `story/run-state.md`.
- [x] 3.4 Add a start charter template that captures premise, chapter count, output directory, and initial run instructions.
- [x] 3.5 Remove or avoid legacy memory fields such as `memory_binding` and `memory_dir`.

## 4. Documentation

- [x] 4.1 Write `examples/writer-team/README.md` with setup commands for project init, specialist creation, profile creation, filesystem mailbox setup, agent launch, and run start.
- [x] 4.2 Document that credentials and auth profiles are operator-provided local setup and are not committed with the example.
- [x] 4.3 Explain the generated artifact layout and what files users should expect under `story/`.
- [x] 4.4 Update the top-level README story-writing loop section to link to `examples/writer-team/`.

## 5. Verification

- [x] 5.1 Verify the example tree contains no committed `.houmao/`, mailbox, credential, generated chapter, generated profile, generated review, or absolute workspace path content.
- [x] 5.2 Run `openspec status --change add-writer-team-example` and confirm the change is apply-ready.
- [x] 5.3 Run the relevant Markdown/link checks available in the repository, or document why no automated check was run.

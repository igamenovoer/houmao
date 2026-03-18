## Context

The repository already has several demo packs under `scripts/demo/` and a growing fixture family under `tests/fixtures/agents/`. Those assets cover CAO-backed sessions, mailbox workflows, and copied dummy-project workdirs, but they do not yet provide a narrow, operator-friendly way to validate skill invocation itself.

Issue-008 established the specific gap: Houmao can project skills into the tool home, but maintainers still lack a direct live-agent check for whether Claude Code or Codex will actually invoke an installed skill from ordinary trigger wording, without being told the skill name or install path.

This change crosses several surfaces:

- demo-pack operator workflow under `scripts/demo/`
- tracked reusable skill fixtures under `tests/fixtures/agents/brains/skills/`
- lightweight role and blueprint fixtures under `tests/fixtures/agents/`
- verification/reporting docs and helpers

That makes a design artifact worthwhile before implementation.

## Goals / Non-Goals

**Goals:**

- Add one self-contained demo pack for skill invocation under `scripts/demo/`.
- Support both Claude Code and Codex from the same operator workflow.
- Verify invocation through a deterministic side effect, not through best-effort assistant prose.
- Keep the prompt contract clean: no skill name and no skill install path in the user-turn prompt.
- Provide one tracked reusable dummy skill fixture that future tests and demos can reuse.
- Keep the launched workdir small and deterministic by reusing a copied dummy project fixture.
- Preserve inspectability for real-agent runs so maintainers can watch tmux/CAO behavior when a tool fails to invoke the skill.

**Non-Goals:**

- This change does not redesign Houmao's generic skill-installation mechanism.
- This change does not guarantee that every arbitrary prompt will auto-trigger a skill.
- This change does not prove, in a formal sense, that a tool could not have completed the side effect without the skill.
- This change does not add a generalized multi-tool skill-autotest matrix beyond the specific demo pack and reusable fixtures needed here.
- This change does not change mailbox behavior directly, even though the demo is motivated by the mailbox skill-invocation uncertainty.

## Decisions

### D1: Use one shared demo pack with `--tool claude|codex`

**Choice:** Create one pack at `scripts/demo/skill-invocation-demo-pack/` with a shared command surface and an explicit tool selector instead of separate `claude` and `codex` packs.

**Rationale:** The maintainer question is the same for both tools: "does the installed skill get invoked from prompt trigger wording?" One shared pack keeps the workflow, report format, and verification rules aligned while still allowing tool-specific fixtures and expectations under the hood.

**Alternative considered:** Two independent packs, one per tool. Rejected because it would duplicate the same operator workflow and make cross-tool comparison harder.

### D2: Use a CAO-backed interactive flow, not a pure headless direct-run flow

**Choice:** Model the demo after the repo's CAO-backed interactive demo packs so operators can start a session, inspect it, send the trigger prompt, verify the side effect, and stop the session.

**Rationale:** The motivating uncertainty was observed in real CAO/tmux-backed runs where inspectability mattered. Using the same inspectable path gives maintainers a live session to watch when the skill does not trigger.

**Alternative considered:** Direct non-CAO headless execution only. Rejected because it is less aligned with the real-agent debugging surface the maintainers are already using.

### D3: Verify invocation through a workdir-local marker file

**Choice:** The reusable dummy skill will write a deterministic marker file into a known workdir-local output subtree inside the copied dummy project, for example `.houmao-skill-invocation-demo/markers/<label>.json`.

**Rationale:** The demo output root already contains the copied project workdir, so a workdir-local marker stays inside the demo-owned filesystem boundary without requiring a new generic env-var injection mechanism. The verification helper can then assert file existence and schema instead of relying on assistant wording.

**Alternative considered:** Verify via assistant reply text only. Rejected because reply text is too easy to treat as best-effort and does not prove the side effect.

### D4: The prompt uses trigger wording only; the dummy skill owns the file-writing contract

**Choice:** The operator-facing prompt will ask the agent to perform a named demo action or handshake using trigger wording defined by the dummy skill, but it will not mention the skill name or install path.

The dummy skill itself will define the operational meaning of that trigger wording, including:

- where the marker file goes,
- what minimal JSON payload it contains,
- and which helper script to run if the skill uses one.

**Rationale:** This matches the contract we want to verify: the tool should resolve the installed skill from prompt semantics, not from a leaked path or explicit skill reference.

**Alternative considered:** Name the skill explicitly in the prompt. Rejected because that would not test the contract in issue-008.

### D5: Ship one tracked reusable probe skill fixture plus dedicated lightweight demo definitions

**Choice:** Add one reusable tracked skill fixture such as `tests/fixtures/agents/brains/skills/skill-invocation-probe/`, plus a lightweight role family and demo blueprints such as:

- `tests/fixtures/agents/roles/skill-invocation-demo/`
- `tests/fixtures/agents/blueprints/skill-invocation-demo-claude.yaml`
- `tests/fixtures/agents/blueprints/skill-invocation-demo-codex.yaml`

The recipes/blueprints will select the probe skill as part of the built brain rather than relying on ad hoc builder inputs from the demo script.

**Rationale:** The demo should exercise the same tracked fixture contract future tests can reuse. Dedicated lightweight demo definitions also avoid reusing unrelated mailbox-specific or repo-scale engineering roles.

**Alternative considered:** Inject the dummy skill ad hoc from the demo script only. Rejected because the user explicitly asked for a tracked reusable dummy skill.

### D6: Reuse the tracked dummy project fixture instead of the main repository checkout

**Choice:** Reuse an existing copied dummy project fixture under `tests/fixtures/dummy-projects/` as the launched workdir for the demo.

**Rationale:** This keeps the environment narrow and deterministic, matching the fixture guidance already adopted for mailbox and runtime-contract tests.

**Alternative considered:** Launch the demo against the full repository worktree. Rejected because repo-scale discovery would obscure whether the prompt triggered the skill cleanly.

### D7: The demo report records both runtime metadata and probe evidence

**Choice:** The demo will generate a structured report that includes:

- selected tool and blueprint
- trigger prompt metadata
- session identifiers needed for inspection
- expected marker path
- observed marker payload
- verification result

The expected report snapshot will compare sanitized report content only.

**Rationale:** This keeps the success boundary explicit and machine-checkable while still being useful to maintainers reading the output by hand.

## Risks / Trade-offs

**[False positive via direct agent imitation]** → An agent might manually recreate the marker file without using the installed skill. Mitigation: make the trigger wording skill-owned, keep the marker schema/tooling defined by the skill fixture, and treat this demo as a practical invocation probe rather than a cryptographic proof.

**[Claude and Codex may resolve installed skills differently]** → One tool may trigger reliably while the other does not. Mitigation: keep `--tool` explicit, generate per-tool reports, and avoid collapsing failures into one shared pass/fail state.

**[CAO-backed demos have more prerequisites than pure local helpers]** → The demo depends on `tmux`, `cao-server`, and valid credentials. Mitigation: follow the existing demo-pack `SKIP:` pattern and make inspect/stop behavior explicit.

**[Trigger wording can be too vague or too narrow]** → If the wording is too vague, the tool may not invoke the skill; if too narrow, the prompt can become another hidden skill name. Mitigation: keep one small, documented probe contract and iterate on the phrasing inside the tracked fixture rather than spreading multiple ad hoc prompts across tests.

**[A reusable probe skill could accrete too many test-only behaviors]** → Future tests might overload one dummy skill with unrelated semantics. Mitigation: keep the probe skill narrowly scoped to one marker-writing contract and add separate probe skills later if materially different behaviors are needed.

## Migration Plan

This change is additive.

1. Add the tracked probe skill, lightweight role, and demo blueprints.
2. Add the new demo pack under `scripts/demo/skill-invocation-demo-pack/`.
3. Document the operator workflow and verification boundary.
4. Optionally migrate future skill-invocation tests to reuse the tracked probe skill instead of inventing ad hoc demo-specific skills.

Rollback is straightforward: remove the pack and fixture assets if the chosen probe contract proves unworkable.

## Open Questions

- Should the first version ship only the interactive demo pack, or also a pack-local autotest wrapper?
- Should the probe marker payload include tool-reported session metadata, or stay minimal and let the report carry those details separately?
- Should the demo reuse the existing `mailbox-demo-python` dummy project fixture or add a smaller skill-focused dummy project fixture if the current one still invites too much exploration?

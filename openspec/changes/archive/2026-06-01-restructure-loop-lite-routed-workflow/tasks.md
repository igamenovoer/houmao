## 1. Package Structure

- [x] 1.1 Replace the flattened lite `SKILL.md` body with a concise router that preserves activation, help, root vocabulary, operation list, route selection, and global constraints.
- [x] 1.2 Add `subskills/authoring/`, `subskills/execution/`, and `subskills/reference/` directories under `houmao-agent-loop-lite`.
- [x] 1.3 Add lite reference pages for scaffold ownership, Markdown contract defaults, Markdown template events, direct SQLite state, runtime mail model, platform boundaries, and system input questions.

## 2. Authoring Pages

- [x] 2.1 Add lite authoring pages for `init`, `create-intention`, `clarify-intent`, `clarify-execplan`, `execplan-fast-forward`, and `update-execplan`.
- [x] 2.2 Add lite staged generation pages for `execplan-specs-process`, `execplan-specs-contract`, `execplan-skills`, `execplan-agent-bindings`, and `execplan-finalize`.
- [x] 2.3 Add lite `validate-execplan` guidance that validates Markdown/direct-SQL execplan shape and rejects pro-only harness, JSON Schema, Jinja2, and generated docs expectations.

## 3. Execution Pages

- [x] 3.1 Add lite execution pages for `prepare-agents`, `prepare-workspace`, `validate-loop`, `launch-agents`, `start`, `status`, `pause`, `resume`, `recover`, and `stop`.
- [x] 3.2 Ensure `prepare-agents` ends with the per-agent table covering agent, participant, TUI/headless launch mode, credential, skill groups, and workdir.
- [x] 3.3 Ensure execution pages route platform mechanics to maintained Houmao skills and never duplicate mailbox, gateway, launch, workspace, inspection, or messaging contracts.

## 4. Scaffold Assets

- [x] 4.1 Add lite `assets/scaffolds/` templates for intention README, loop overview, execplan README, Markdown manifest, specs README files, communication template examples, state README/schema, skills README, and agents README/bindings.
- [x] 4.2 Add a lite `scripts/scaffold.py` with scaffold profiles for intention creation/init and Markdown/direct-SQL execplan shells.
- [x] 4.3 Keep scaffold output free of `execplan/harness/`, `execplan/docs/`, JSON schemas, and Jinja2 renderer directories.

## 5. Tests And Docs

- [x] 5.1 Update packaged system-skill tests to assert the lite routed page structure, scaffold assets, and installed projection paths.
- [x] 5.2 Update tests that currently assume lite is only a single `SKILL.md` asset.
- [x] 5.3 Update loop authoring and system-skill overview docs if needed to describe lite as pro-shaped in workflow but Markdown/direct-SQL in generated artifacts.
- [x] 5.4 Run focused unit tests for system-skill packaging and documentation guards.

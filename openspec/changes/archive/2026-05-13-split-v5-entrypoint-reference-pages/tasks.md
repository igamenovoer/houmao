## 1. Reference Page Structure

- [x] 1.1 Create `subskills/reference/` in the v5 skill package.
- [x] 1.2 Add `scaffold-surface.md` for scaffold profiles, template authority, and scaffold script usage.
- [x] 1.3 Add `generated-contract-defaults.md` for generated artifact layout, README rules, state/bookkeeping defaults, TOML descriptions, and harness-facing contract defaults.
- [x] 1.4 Add `generation-pipeline.md` for process-first stage ordering, stage dependencies, and `update-execplan` downstream regeneration rules.
- [x] 1.5 Add `runtime-mail-model.md` for notifier-driven mail turns, on-event/on-tick semantics, and no in-chat waiting.
- [x] 1.6 Add `platform-boundaries.md` for maintained Houmao skill ownership of workspace, mailbox, gateway, messaging, lifecycle, memory, and inspection operations.

## 2. Entrypoint Split

- [x] 2.1 Trim v5 `SKILL.md` to activation, required `<loop-dir>`, source/generated-output invariants, concise operation list, routing table, and global constraints.
- [x] 2.2 Remove detailed generated-contract defaults, bookkeeping guidance, TOML conventions, mail-runtime details, scaffold details, and platform-boundary details from `SKILL.md` after moving them to reference pages.
- [x] 2.3 Keep `SKILL.md` links to routed subskills valid and concise.

## 3. Routed Subskill Dependencies

- [x] 3.1 Add `Read first` references to `init.md` and `create-intention.md` for scaffold guidance.
- [x] 3.2 Add `Read first` references to execplan generation and update pages for scaffold, generation-pipeline, generated-contract, mail-runtime, and platform-boundary guidance as appropriate.
- [x] 3.3 Add `Read first` references to validation and finalization pages for generated-contract and generation-pipeline guidance.
- [x] 3.4 Add `Read first` references to execution pages for runtime-mail-model and platform-boundary guidance where applicable.
- [x] 3.5 Remove duplicated shared policy from operation pages when the policy is now owned by a reference page.

## 4. Design Docs And Validation

- [x] 4.1 Update `dev/design/` docs to describe the runtime-reference-page split and preserve the maintainer/runtime documentation boundary.
- [x] 4.2 Check all Markdown links from `SKILL.md` and subskills to reference pages resolve.
- [x] 4.3 Confirm no detailed runtime guidance needed during execution exists only under `dev/design/`.
- [x] 4.4 Run `git diff --check`.
- [x] 4.5 Verify the OpenSpec change is apply-ready.

## 1. CLI Reference Resync (Track A)

- [x] 1.1 Reverify `docs/reference/cli/houmao-mgr.md` against current `srv_ctrl/commands/main.py`, `agents/core.py`, `project.py`, and `system_skills.py` Click decorators. Add `--version` to root option coverage. Add `agents launch --workdir` and `--model` coverage. Remove every remaining `--yolo` mention. Add inline cross-link to `docs/reference/run-phase/managed-prompt-header.md` from `--managed-header` / `--no-managed-header` flag coverage.
- [x] 1.2 Reverify `docs/reference/cli/agents-mail.md` against `srv_ctrl/commands/agents/mail.py` Click decorators. Confirm subcommand list (`resolve-live`, `status`, `check`, `send`, `reply`, `mark-read`) and option tables are still accurate. Add the unified `houmao-agent-email-comms` skill boundary note and remove pre-unification split-skill names.
- [x] 1.3 Reverify `docs/reference/cli/agents-mailbox.md` against `srv_ctrl/commands/agents/mailbox.py` Click decorators. Update option tables for any post-`2026-04-04` flag changes.
- [x] 1.4 Reverify `docs/reference/cli/agents-turn.md` against `srv_ctrl/commands/agents/turn.py` Click decorators. Update option tables for any post-`2026-04-04` flag changes.
- [x] 1.5 Reverify `docs/reference/cli/agents-gateway.md` against `srv_ctrl/commands/agents/gateway.py` Click decorators. Confirm `tui` and `mail-notifier` subgroups are complete and current.
- [x] 1.6 Reverify `docs/reference/cli/admin-cleanup.md` against `srv_ctrl/commands/admin.py` Click decorators.
- [x] 1.7 Reverify `docs/reference/cli/houmao-server.md` against `src/houmao/server/commands/` Click decorators. Update option tables for any post-`2026-04-04` flag changes.
- [x] 1.8 Reverify `docs/reference/cli/system-skills.md` against `srv_ctrl/commands/system_skills.py`. Add a "see also" link to `docs/getting-started/system-skills-overview.md` near the top of the page.

## 2. New Conceptual Pages (Track C)

- [x] 2.1 Create `docs/reference/run-phase/managed-prompt-header.md`. Cover: what the header is, why it exists, the prompt composition order (source role prompt → prompt-overlay resolution → managed header prepend → backend role injection), the default-on policy, the `--managed-header` / `--no-managed-header` opt-out flags, persistence in stored launch profiles, and `--clear-managed-header` semantics. Add cross-links to `docs/getting-started/launch-profiles.md`, `docs/reference/run-phase/role-injection.md`, and `docs/reference/cli/houmao-mgr.md`. Derive content from `src/houmao/agents/managed_prompt_header.py` and the launch-profile spec files.
- [x] 2.2 Create `docs/getting-started/system-skills-overview.md`. List all eight current packaged system skills with one-sentence descriptions and canonical CLI routing. Distinguish managed-home auto-install vs external-home CLI-default install behavior, deriving both lists from current `srv_ctrl/commands/system_skills.py`. Add cross-links to the README system-skills subsection, `docs/reference/cli/system-skills.md`, `docs/getting-started/easy-specialists.md`, and `docs/getting-started/launch-profiles.md`. Derive each skill row from `src/houmao/agents/assets/system_skills/<skill>/SKILL.md`.

## 3. README Polish (Track D)

- [x] 3.1 Reverify the README system-skills subsection skill catalog table. Add a `houmao-agent-email-comms` row with a one-line description. Distinguish ordinary mailbox operations (`houmao-agent-email-comms`) from notifier-driven unread-mail rounds (`houmao-process-emails-via-gateway`). Remove any pre-unification split-skill names from the catalog.
- [x] 3.2 Reverify the README "auto-install" paragraph against current `srv_ctrl/commands/system_skills.py` defaults. Update the listed managed-home auto-install set and the CLI-default external-install set to match current source. Treat any divergence as a doc bug.
- [x] 3.3 Add a one-line note about the managed prompt header to the README "What You Get After Joining" section, linking to `docs/reference/run-phase/managed-prompt-header.md`. Mention `--no-managed-header` as the per-launch opt-out and persistent storage in launch profiles.
- [x] 3.4 Add a `--version` mention to the README CLI Entry Points table (footnote on the `houmao-mgr` row, dedicated row, or inline note immediately following the table). State that `houmao-mgr --version` prints the packaged version and exits successfully without a subcommand.
- [x] 3.5 Re-evaluate the "In development — not ready for use" status text in the CLI Entry Points table for `houmao-passive-server` against the rewritten `docs/reference/cli/houmao-passive-server.md`. Downgrade the warning if the reference page now describes a usable surface.
- [x] 3.6 Add a link to `docs/getting-started/system-skills-overview.md` in the README system-skills subsection alongside the existing link to `docs/reference/cli/system-skills.md`. Present catalog → narrative → reference as the three layers.

## 4. Stale Content Sweep (Track E)

- [x] 4.1 Grep `docs/**/*.md` and `README.md` for `--yolo`. Remove or rewrite each occurrence as a historical "removed in 0.3.x" note. Where the surrounding prose explains how to launch unattended, replace it with the current `launch.prompt_mode: unattended` mechanism reference.
- [x] 4.2 Grep `docs/**/*.md` for `houmao-create-specialist`. Replace each occurrence used as a current packaged skill name with `houmao-manage-specialist`. Leave migration-note context unchanged.
- [x] 4.3 Grep `docs/**/*.md` for the bare skill identifier `specialist` in skill-related contexts (skill catalog rows, system-skills install lists). Distinguish prose noun usage from skill identifier usage; only rewrite identifier usage to `houmao-manage-specialist`.
- [x] 4.4 Grep `docs/**/*.md` and `README.md` for `agentsys`, `.agentsys`, `AGENTSYS_`. Replace any straggler with the corresponding `houmao` equivalent and review surrounding prose for accuracy.
- [x] 4.5 Verify no broken cross-references introduced by Tracks A–C. Spot-check links from each new or modified page resolve to existing targets.

## 5. Index and Navigation Updates

- [x] 5.1 Update `docs/index.md` to link `docs/getting-started/system-skills-overview.md` from the getting-started section with a one-line description.
- [x] 5.2 Update `docs/reference/index.md` to link `docs/reference/run-phase/managed-prompt-header.md` from the run-phase section with a one-line description, alongside `launch-plan.md`, `session-lifecycle.md`, `backends.md`, and `role-injection.md`.
- [x] 5.3 Update `mkdocs.yml` navigation to add entries for both new pages under the appropriate sections. Verify no dangling entries. (`mkdocs.yml` has no explicit `nav:` section — pages are auto-discovered, so the two new files are picked up automatically. No edit needed; no dangling entries to remove.)

## 6. Verification

- [x] 6.1 Run `pixi run docs-serve` (or `mkdocs build --strict`) locally to confirm the site builds without warnings about missing pages or broken cross-references introduced by this change. (`pixi run mkdocs build --strict` succeeded with `Documentation built in 2.31 seconds`; only unrelated Material-team upstream noise was emitted, no warnings about pages or links.)
- [x] 6.2 Final grep pass: `--yolo`, `houmao-create-specialist`, `agentsys` all return zero matches as current usage across `docs/**/*.md` and `README.md`. (`houmao-create-specialist` and `agentsys` both have zero matches; `--yolo` has only two historical-note mentions in `quickstart.md` and `easy-specialists.md`, both rewritten as explicit "removed in 0.3.x" notes, plus the legitimate Gemini-CLI-side mention in `launch-policy.md` describing the `gemini.canonicalize_unattended_launch_inputs` policy that strips upstream Gemini `--yolo` flags.)
- [x] 6.3 Final source-vs-doc spot-check: pick three flags touched by recent commits (`--version`, `agents launch --workdir`, `--no-managed-header`) and confirm the documented coverage matches the live Click decorator definitions. (`--version` → `main.py:22` matches `houmao-mgr.md:19`; `agents launch --workdir` → `agents/core.py:544` matches `houmao-mgr.md` `agents launch` rules; `--no-managed-header` → `agents/core.py:539` matches `houmao-mgr.md` + new `managed-prompt-header.md`.)

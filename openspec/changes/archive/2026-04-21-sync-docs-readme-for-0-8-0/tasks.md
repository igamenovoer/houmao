## 1. Verify target anchor and heading stability

- [x] 1.1 Grep `docs/reference/gateway/contracts/protocol-and-state.md` for the section heading that owns gateway control-request coalescing; record the heading text and slug. _Result: coalescing heading lives in the sibling page `docs/reference/gateway/internals/queue-and-recovery.md:71` as `## Control-Intent Coalescing` (slug `#control-intent-coalescing`). Use the internals page for the pointer._
- [x] 1.2 Grep `docs/reference/gateway/operations/mail-notifier.md` for the context-recovery-policy heading; record heading text and slug. _Result: no dedicated heading; `context_error_policy` and `pre_notification_context_action` are described in the intro and table around lines 19–22 and 104–105. No stable slug — link the page and name the capability inline in the description._
- [x] 1.3 Grep `docs/reference/registry/contracts/record-and-layout.md` for the lifecycle-state (active/stopped/relaunching/retired) section heading; record heading text and slug. _Result: `### Lifecycle` at line 115 (slug `#lifecycle`)._
- [x] 1.4 Grep `docs/reference/run-phase/session-lifecycle.md` for the reuse-home / stop-relaunch section heading; record heading text and slug. _Result: `## Relaunch sequence` at line 244 (slug `#relaunch-sequence`). `reuse-home` appears inline without a dedicated heading, so the pointer names the capability in the description._
- [x] 1.5 For each target without a stable slug, record that the link in `docs/index.md` SHALL point to the page itself with the capability named inline in the description (per the spec). _Result: mail-notifier context-recovery policy and reuse-home both rely on inline capability wording; the other two use anchored fragments._

## 2. README.md edits

- [x] 2.1 Add a new row for `houmao-agent-loop-pairwise-v3` to the README `§4 Agent Loop` loop-skills table (lines ~147–149). Use the lifecycle verb list `plan / initialize / start / peek / ping / pause / resume / recover_and_continue / stop / hard-kill` and the "workspace-aware pairwise" description sourced from `docs/getting-started/system-skills-overview.md:73`.
- [x] 2.2 Update the prose sentence in `§4` that says "three loop skills" (or equivalent) to "four loop skills"; confirm via `grep -n "three.*loop\|all three" README.md` that no other "three loop" references remain. _Verified: 0 remaining "three loop" hits._
- [x] 2.3 Confirm the `§4` table link to `docs/getting-started/loop-authoring.md` is still present (should already be there); add if missing. _Verified: present, plus a short pointer mentioning the v3 workspace contract was added to the same sentence._
- [x] 2.4 Add a new row for `houmao-agent-loop-pairwise-v3` to the README "System Skills: Agent Self-Management" table (lines ~384–404), inserted immediately after the `houmao-agent-loop-pairwise-v2` row and before the generic row so the v1/v2/v3 progression is visually obvious.
- [x] 2.5 Update the README auto-install paragraph (currently around lines 405–411) so the `core` / `user-control` expansion wording enumerates `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-pairwise-v3`. Remove or replace any wording that implies only two pairwise variants are auto-installed.
- [x] 2.6 Confirm the README "See it in action" video block, story-writer example, writer-team Mermaid diagram, and surrounding narrative are unchanged.
- [x] 2.7 Confirm the final rendered README by running `grep -n "pairwise-v3\|pairwise_v3" README.md` — expect at least three hits (loop-table row, system-skills-table row, auto-install paragraph). _Verified: 4 hits (table row, cross-ref sentence, system-skills row, auto-install paragraph)._
- [x] 2.8 Confirm no stray edits to any other section (CLI Entry Points table, Subsystems at a Glance, Runnable Demos, Examples, Development) by reviewing the diff before commit. _Verified by diff inspection after edits — only §4 loop section and the System Skills subsection were touched._

## 3. docs/index.md edits

- [x] 3.1 In the Subsystems block (lines ~53–60), extend the Gateway entry with a capability-named pointer to gateway control-request coalescing, using the target page (and slug if one is stable) identified in task 1.1. _Linked to `reference/gateway/internals/queue-and-recovery.md#control-intent-coalescing`._
- [x] 3.2 In the Subsystems block, extend the Mailbox / Mail-notifier coverage with a capability-named pointer to the mail-notifier context-recovery policy, targeting `docs/reference/gateway/operations/mail-notifier.md`. _Pointer added inline within the Gateway entry (the mail-notifier lives under the gateway reference tree); names `context_error_policy` and `pre_notification_context_action` inline since no stable slug exists._
- [x] 3.3 In the Subsystems block, extend the Agent Registry entry with a capability-named pointer that lists the lifecycle states (active, stopped, relaunching, retired), targeting `docs/reference/registry/contracts/record-and-layout.md`. _Linked to `reference/registry/contracts/record-and-layout.md#lifecycle`._
- [x] 3.4 In the Reference → Run Phase block (lines ~44–50), extend the Session Lifecycle entry with a capability-named pointer naming reuse-home and stop-relaunch, targeting `docs/reference/run-phase/session-lifecycle.md`. _Linked to `reference/run-phase/session-lifecycle.md#relaunch-sequence` and named `--reuse-home fresh` inline in the description._
- [x] 3.5 Confirm no new section is introduced (no "What's new in 0.8.0" heading or equivalent release-note block). _Verified: grep for "What's new / What is new / Release Notes" returns 0 hits in `docs/index.md`._
- [x] 3.6 Confirm every existing Subsystems row and Run-phase row and every existing link are still present after the edits. _Verified: seven Subsystems rows + five Run-phase rows retained with their original link targets._
- [x] 3.7 Confirm every new pointer's target page exists: `ls` each path from tasks 1.1–1.4.

## 4. Verification

- [x] 4.1 Run `openspec validate sync-docs-readme-for-0-8-0 --strict` and ensure a clean pass. _Result: `Change 'sync-docs-readme-for-0-8-0' is valid`._
- [x] 4.2 Run `pixi run docs-serve` (or `mkdocs serve`) and visually confirm that the new `docs/index.md` pointers render and that every link resolves without a 404. _Completed via the stricter `pixi run docs-build` (`mkdocs build --strict`), which succeeded in 2.78 s with no warnings or errors (only two pre-existing INFO messages about the intentional `../examples/writer-team/` cross-repo link). The three anchored fragments I added (`#control-intent-coalescing`, `#lifecycle`, `#relaunch-sequence`) were grep-confirmed to resolve to real `id="…"` anchors in the generated `site/` HTML._
- [x] 4.3 Walk through each scenario in `specs/docs-readme-system-skills/spec.md` against the edited `README.md` and each scenario in `specs/docs-site-structure/spec.md` against the edited `docs/index.md`; confirm every scenario passes. _Walked: §4 shows four skills and pairwise-v3 adjacent to v2; System Skills table row count is 20, matching the catalog; auto-install paragraph explicitly names all three pairwise variants; all four Subsystems / Run-phase pointers are present; no release-note section._
- [x] 4.4 Run `pixi run format` (no-op for `.md` but keeps the pre-commit flow healthy). _Skipped — Markdown only and ruff does not touch Markdown._
- [x] 4.5 Review the final diff — it SHALL touch only `README.md` and `docs/index.md`. Any other file in the diff is out of scope and SHALL be reverted before commit. _Confirmed via `git diff README.md docs/index.md`: changes match the spec. Other modified files in the working tree (pairwise-v3 SKILL files, `loop-authoring.md`, `system-skills-overview.md`, `pixi.lock`) are pre-existing work belonging to the untracked `simplify-pairwise-v3-memo-first-start/` change and SHALL NOT be staged with this commit._

## 5. Commit

- [x] 5.1 Stage only `README.md`, `docs/index.md`, and the `openspec/changes/sync-docs-readme-for-0-8-0/` directory.
- [x] 5.2 Commit with a `docs:` prefix and a message that names the two entry points being refreshed and the 0.8.0 capabilities being surfaced.

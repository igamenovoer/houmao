## 1. SKILL.md — welcome and guardrails

- [x] 1.1 Edit `src/houmao/agents/assets/system_skills/houmao-touring/SKILL.md` to add a state-adaptive welcome rule: present the full welcome only when the workspace has no project overlay, no reusable specialists, and no running managed agents; otherwise present a short acknowledgement and continue with current-state orientation.
- [x] 1.2 Edit the same `SKILL.md` to reference the new concepts glossary at `references/concepts.md` in the References section.
- [x] 1.3 Edit the same `SKILL.md` to add the new quickstart branch entry under the Branches list pointing at `branches/quickstart.md`.
- [x] 1.4 Edit the same `SKILL.md` to add a guardrail that all touring-skill content must live inside `src/houmao/agents/assets/system_skills/houmao-touring/` and must not reference paths under `examples/`, `docs/`, `magic-context/`, or `openspec/`, or any other file that only exists in the development repository.

## 2. Orient branch — posture-to-branch matrix

- [x] 2.1 Edit `src/houmao/agents/assets/system_skills/houmao-touring/branches/orient.md` to add an explicit posture-to-branch routing table covering at minimum the postures "no overlay and no specialists and no running agents", "overlay exists without specialists", "specialists exist without running agents", "one or more running managed agents", and "multi-agent workspace".
- [x] 2.2 In the same file, state that the routing table is the source of truth for offering next branches, and preserve the existing rule that the offered branches remain offers rather than mandates.
- [x] 2.3 In the same file, include the quickstart branch as one of the offered next branches for the empty-workspace posture.
- [x] 2.4 In the same file, keep the existing guardrails unchanged, including "do not treat missing project state as a reason to hide later branches" and "do not replace maintained `project easy ...` inspection commands".

## 3. Quickstart branch — new file

- [x] 3.1 Create `src/houmao/agents/assets/system_skills/houmao-touring/branches/quickstart.md` with a workflow that detects available host tool CLIs via `command -v <tool>` checks for the tools supported by the packaged Houmao distribution (at minimum `claude`, `codex`, and `gemini`).
- [x] 3.2 In that file, describe the rendering contract: list detected tools to the user without priority, without ordering that implies recommendation, and without marking any detected tool as the default or preferred tool.
- [x] 3.3 In that file, describe the no-tool path: when no supported tool CLI is detected, explain which tool CLIs Houmao supports and do not attempt to launch a managed agent in that turn.
- [x] 3.4 In that file, route specialist authoring, credential attachment, and easy-instance launch through `houmao-specialist-mgr` rather than restating those command shapes.
- [x] 3.5 In that file, add guardrails mirroring the other branches: no background gateway flags unless the user asked for them, no hand-editing `.houmao/` paths, no duplicate command surface.

## 4. Advanced-usage branch — broader enumeration

- [x] 4.1 Edit `src/houmao/agents/assets/system_skills/houmao-touring/branches/advanced-usage.md` to expand its scope from pairwise-only to a flat enumeration of the broader advanced surface, keeping the existing pairwise guidance intact.
- [x] 4.2 Add brief one-to-two-sentence entries for `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, `houmao-agent-loop-generic`, `houmao-adv-usage-pattern`, `houmao-memory-mgr`, `houmao-agent-gateway` (mail-notifier and reminders), `houmao-credential-mgr`, and `houmao-agent-definition`.
- [x] 4.3 In the same file, require no priority markers, no "recommended", "preferred", "primary", or "default" labels on any entry.
- [x] 4.4 In the same file, preserve the existing guardrails about not silently auto-routing pairwise requests, not restating pairwise templates or routing packets inline, and keeping elemental edge-protocol guidance on `houmao-adv-usage-pattern`.

## 5. Concepts reference — new file

- [x] 5.1 Create `src/houmao/agents/assets/system_skills/houmao-touring/references/concepts.md` as a compact self-contained glossary.
- [x] 5.2 Include at minimum entries for `specialist`, `easy profile`, `launch profile`, `managed agent`, `recipe`, `tool adapter`, `project overlay`, `gateway`, `gateway sidecar`, `mailbox root`, `mailbox account`, `principal id`, `user agent`, `master`, `loop plan`, `relaunch`, and `cleanup`.
- [x] 5.3 Keep each entry to roughly one to three sentences, and cross-reference the owning Houmao-owned skill when one exists.
- [x] 5.4 Verify that every cross-reference points at a skill name (not a repo path) so that the glossary survives pypi distribution.

## 6. Validation and quality checks

- [x] 6.1 Run `openspec validate expand-houmao-touring-entrypoint` and confirm the change is valid.
- [x] 6.2 Run `pixi run lint` and confirm there are no new lint errors introduced by the edited or created markdown files (the markdown files must still pass any repo-wide markdown lint rules that apply).
- [x] 6.3 Run `pixi run test` to confirm no existing unit tests that cover the system-skill asset directory break due to the new files (for example asset-discovery tests under `tests/unit/agents/test_system_skills.py`).
- [x] 6.4 Grep the packaged asset directory for references to `examples/`, `docs/`, `magic-context/`, and `openspec/` and confirm there are no occurrences.
- [x] 6.5 Install the built wheel into a scratch environment and confirm that `references/concepts.md`, `branches/quickstart.md`, and the updated `branches/advanced-usage.md` are all present inside the installed package.

## 7. Docs sync (optional, non-blocking)

- [x] 7.1 If the README `houmao-touring` row is updated in a later change to mention the quickstart and features enumeration, keep that edit out of this change's scope and track it separately. This change does not require a README edit.

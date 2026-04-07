## 1. New Conceptual Page

- [x] 1.1 Draft `docs/getting-started/launch-profiles.md` covering: what a launch profile is, the easy-versus-explicit lane split, the shared catalog-backed model, the source-versus-birth-time taxonomy, and when to use which lane.
- [x] 1.2 Add the five-layer precedence section to `launch-profiles.md` and render the precedence chain as a mermaid fenced code block (no ASCII art).
- [x] 1.3 Add the prompt-overlay section to `launch-profiles.md` covering `append`, `replace`, the pre-injection composition rule, and the file-backed payload note.
- [x] 1.4 Add the profile-provenance section to `launch-profiles.md` covering inspection output and the secret-free reporting rule.
- [x] 1.5 Add cross-link footer to `launch-profiles.md` linking to easy-specialists, agent-definitions, `houmao-mgr` CLI reference, and launch-overrides.

## 2. Heavy Rewrite: `docs/reference/cli/houmao-mgr.md`

- [x] 2.1 Extend the `Command shape` ASCII pseudo-tree to list `recipes`, `presets`, `launch-profiles` under `project agents` and `specialist`, `profile`, `instance` under `project easy`.
- [x] 2.2 Add `project agents recipes list|get|add|set|remove` row(s) to the `project agents` subcommand table and explain that `presets` is the compatibility alias for the same files under `agents/presets/<name>.yaml`.
- [x] 2.3 Add `project agents launch-profiles list|get|add|set|remove` row(s) to the `project agents` subcommand table and describe the on-disk path `agents/launch-profiles/<name>.yaml`.
- [x] 2.4 Add `project easy profile create|list|get|remove` row(s) to the `project easy` subcommand table.
- [x] 2.5 Extend the `project easy instance launch notes` section to document `--profile`, the `--profile`/`--specialist` mutual exclusion, easy-profile-derived defaults precedence, and the easy-instance inspection profile-origin reporting.
- [x] 2.6 Add `--launch-profile` documentation to the `agents launch` coverage: the flag itself, the `--launch-profile`/`--agents` mutual exclusion, derived-provider behavior, and the recipe → launch-profile → direct-CLI precedence order.
- [x] 2.7 Sweep the file for user-facing `preset` references and replace them with `recipe` where they describe the source noun, while keeping `preset` for the on-disk projection path and the compatibility alias.
- [x] 2.8 Add an inline link to `docs/getting-started/launch-profiles.md` from the `project easy profile` and `project agents launch-profiles` paragraphs so the conceptual model lives in one place.

## 3. Heavy Rewrite: `docs/getting-started/easy-specialists.md`

- [x] 3.1 Replace the existing two-step ASCII lifecycle picture with a mermaid flowchart showing specialist → optional easy profile → instance → managed agent.
- [x] 3.2 Replace the top-of-page comparison table with a three-way comparison: easy specialist, easy specialist plus easy profile, explicit recipe plus launch-profile.
- [x] 3.3 Add a new "Easy Profiles" section documenting `project easy profile create|list|get|remove` with command examples and the rule that easy profiles target exactly one specialist.
- [x] 3.4 Update the "Launching an Instance" section to cover `--profile`, the `--profile`/`--specialist` mutual exclusion, and the easy-profile-derived defaults precedence.
- [x] 3.5 Update the "Managing Specialists and Instances" section to mention that `instance get` and `instance list` report the originating easy-profile when present.
- [x] 3.6 Add a "See Also" link to `docs/getting-started/launch-profiles.md` for the shared conceptual model.
- [x] 3.7 Sweep the page for user-facing `preset` references and replace with `recipe` where appropriate (the existing "easy specialist vs full preset" comparison line is the main hit).

## 4. Medium Refresh: `docs/getting-started/overview.md`

- [x] 4.1 Update the opening line that describes the model as "preset + setup + auth" so it reads as recipe + setup + auth, with one sentence noting that reusable birth-time launch configuration now lives separately as launch profiles.
- [x] 4.2 Update the build-phase mermaid pipeline so the source tree node references roles + recipes + launch-profiles + tools + skills (canonical naming) rather than presets only.
- [x] 4.3 Update the project ASCII pseudo-tree near the bottom of the page so `project agents` lists `roles`, `recipes`, and `tools <tool>` and so `project easy` lists `specialist`, `profile`, and `instance`.

## 5. Medium Refresh: `docs/reference/build-phase/launch-overrides.md`

- [x] 5.1 Update the prose intro that names the precedence pipeline so it reads as adapter defaults → recipe overrides → launch-profile defaults → direct overrides → live runtime mutations.
- [x] 5.2 Extend the existing precedence mermaid diagram with the launch-profile defaults layer between recipe overrides and direct overrides.
- [x] 5.3 Update the `merge_launch_intent` description to mention the launch-profile layer.
- [x] 5.4 Replace user-facing `preset` references in the page body with `recipe`, keeping `preset` only when naming the on-disk projection path or the compatibility alias.
- [x] 5.5 Add a link to `docs/getting-started/launch-profiles.md` for the shared conceptual model.

## 6. Medium Refresh: `docs/reference/run-phase/launch-plan.md`

- [x] 6.1 Add a paragraph (or extend the existing one) explaining how launch-profile-derived inputs reach the manifest: auth selection, prompt-mode intent, env records, mailbox config, identity defaults, and the prompt-overlay-composed effective role prompt.
- [x] 6.2 Add a note in the `LaunchPlan` field documentation that the `metadata` carries secret-free launch-profile provenance (lane plus profile name) when the launch came from a reusable launch profile.
- [x] 6.3 Add a link to `docs/getting-started/launch-profiles.md` for the shared conceptual model.
- [x] 6.4 State explicitly that runtime `LaunchPlan` is derived and ephemeral and is not user-authored.

## 7. Small Refresh: `docs/reference/cli.md`

- [x] 7.1 Add a short paragraph (or extend the existing project-tree paragraph) listing the new `project easy profile`, `project agents recipes`, and `project agents launch-profiles` subtrees, plus a pointer to the canonical coverage on `docs/reference/cli/houmao-mgr.md`.
- [x] 7.2 Add a one-line `agents launch --launch-profile` mention pointing to the same canonical coverage.

## 8. Vocabulary Sweep on Light-Touch Pages

- [x] 8.1 `docs/index.md`: replace user-facing `preset` references with `recipe` while keeping the `presets/` projection-path mention valid.
- [x] 8.2 `docs/reference/system-files/agents-and-runtime.md`: no remaining `preset` matches; no edit needed.
- [x] 8.3 `docs/reference/realm_controller.md`: no remaining `preset` matches; no edit needed.
- [x] 8.4 `docs/reference/houmao_server_pair.md`: replaced two user-facing `preset-backed` references with `recipe-backed` and clarified the generated recipe under `.houmao/agents/presets/`.
- [x] 8.5 `docs/reference/agents/operations/project-aware-operations.md`: replaced the `agent_def_dir` description and the catalog-storage bullets with recipe-and-launch-profile vocabulary.
- [x] 8.6 `docs/reference/agents/troubleshoot/codex-cao-approval-prompt-troubleshooting.md`: no remaining `preset` matches; no edit needed.
- [x] 8.7 `docs/reference/build-phase/launch-policy.md`: rewrote the `operator_prompt_mode` source line to reference the recipe and the resolved launch profile.
- [x] 8.8 `docs/reference/mailbox/contracts/project-mailbox-skills.md`: rewrote the projection-trigger line to reference the source recipe, the resolved launch profile, and the build request.

## 9. Reconcile Existing Partial In-Tree Edits

- [x] 9.1 `README.md`: existing partial edits already covered recipe vocabulary and the `--launch-profile` example. Added a launch-profiles-guide cross-link in both the easy-specialist paragraph and the recipes-and-launch-profiles section.
- [x] 9.2 `docs/getting-started/agent-definitions.md`: existing partial edits already covered recipes and launch-profiles directory layout. Added a "see Launch Profiles" cross-link in the `launch-profiles/<profile>.yaml` section.
- [x] 9.3 `docs/getting-started/quickstart.md`: existing partial edits covered recipes vocabulary. Added the `agents launch --launch-profile` example with mutual-exclusion + precedence note, replaced remaining user-facing `preset` references with `recipe`, refreshed `--preset` flag description to clarify that it resolves recipe files under `presets/`, and added a See Also link to the launch-profiles guide.
- [x] 9.4 `docs/reference/cli/system-skills.md`: clarified the `houmao-manage-agent-definition` line to mention the canonical `project agents recipes ...` surface and the compatibility alias, and replaced the remaining `preset-selected project skills` phrasing with `recipe-selected project skills`.

## 10. Site Structure And Navigation

- [x] 10.1 Add a getting-started entry for `launch-profiles.md` to `docs/index.md` with a one-line description.
- [x] 10.2 No edit needed: `mkdocs.yml` has no explicit `nav:` block, so navigation is auto-generated from the docs/ tree and `getting-started/launch-profiles.md` is picked up automatically.
- [x] 10.3 Ran `pixi run python -m mkdocs build --strict`; the build succeeded in 2.24 seconds with no warnings or dangling-link errors.
- [x] 10.4 Walked every cross-reference in `launch-profiles.md`, `easy-specialists.md`, `houmao-mgr.md`, `launch-overrides.md`, `launch-plan.md`, `quickstart.md`, `agent-definitions.md`, `cli.md`, and `index.md`; all targets resolve.

## 11. Verification

- [x] 11.1 `pixi run lint` (ruff check on src, tests, docs, scripts) passes cleanly. Markdown content is not linted by ruff but the strict mkdocs build (task 10.3) caught all dangling links and missing pages.
- [x] 11.2 `openspec validate revise-docs-for-launch-profiles --strict` succeeds.
- [x] 11.3 Walked the rewritten quickstart, easy-specialists, agent-definitions, overview, launch-overrides, launch-plan, cli, and houmao-mgr pages and confirmed no truncation, no orphan links, and no leftover ASCII art in any newly authored or rewritten diagram. The CLI command-shape pseudo-trees that remain in `houmao-mgr.md` and `overview.md` are explicitly allowed by the design (they describe command shapes, not flow diagrams).
- [x] 11.4 The strict mkdocs build (`pixi run python -m mkdocs build --strict`) renders `docs/getting-started/launch-profiles.md`, `docs/getting-started/easy-specialists.md`, and the refreshed `docs/reference/build-phase/launch-overrides.md` with mermaid fenced code blocks. The pymdownx.superfences mermaid custom_fence is configured in `mkdocs.yml`, so the published site renders the diagrams in the browser.

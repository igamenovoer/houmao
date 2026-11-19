# Tasks

## 1. Resolve and Store the Run Mode

- [ ] 1.1 Add the shared run-mode type and one tool/mode/backend selector in launch planning. Table-test ordinary project defaults, the low-level Codex default, passive headless birth, unsupported pairs, and conflicting explicit backends.
- [ ] 1.2 Replace the project launch and both profile authoring Boolean selectors with `--mode` and optional `defaults.posture.mode`. Test direct-over-stored precedence, omission, explicit overrides, and an actionable error for the obsolete stored field.
- [ ] 1.3 Forward the effective selection through executor routing, policy compilation, and `tool_params` validation. Prove an unsupported pair on the target executor fails before home writes, predecessor takeover, or registry publication.
- [ ] 1.4 Document the four CLI values, defaults by entrypoint, and independent `unattended`/`as_is` policy in the project launch and profile reference. Check documented selections against CLI help and config-draft validation.

## 2. Publish and Recover the Verified Selection

- [ ] 2.1 Version the launch plan, session manifest, registry records, and execution-locator projections that carry resolved mode and backend. Exercise local and routed discovery plus incompatible RC2 records and verify fresh-launch guidance.
- [ ] 2.2 Update relaunch to reuse the stored mode, and record the verified mode through existing TUI and headless join flows. Test profile edits after birth and verify an RC2 per-turn ACP record cannot establish service ownership.
- [ ] 2.3 Choose terminal attach, browser handoff, or managed control from the verified native surface. Test DSH Web from a TTY, unattended TUI from a non-TTY, sanitized remote Web handoff, and a service with a supervisory pane.
- [ ] 2.4 Describe mode, human surface, and the current-schema fresh-launch boundary in lifecycle and discovery docs. Check the published sample output against the observed launch and inspection fields.

## 3. Update Launch Callers and Qualification

- [ ] 3.1 Update maintained definition/instance and ready-profile guidance, CLI examples, config drafts, fixture scripts, and the private login smoke to use the new manager selector. Exercise packaged help paths and assert that a stored service or Web choice survives generated launch commands.
- [ ] 3.2 Translate the existing minimal demo selector and headless wakeup-demo lanes to current manager arguments. Run their command-construction tests and verify the Claude and Codex headless examples select `--mode headless`.
- [ ] 3.3 Record tool build, model, case, mode, backend, and native surface in fixture results. Test that DSH Web evidence appears only in `web` and an unavailable service or native CLI is reported as such.
- [ ] 3.4 Run `pixi run lint`, `pixi run typecheck`, and `pixi run test`. Check one existing TUI and DSH Web launch through the public manager; clear `TMUX` and `TMUX_PANE` and use a dedicated tmux server for supervised tests.

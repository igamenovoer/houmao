## 1. Specialist Creation Defaults

- [ ] 1.1 Add `--no-unattended` to `houmao-mgr project easy specialist create` and select the default specialist `launch.prompt_mode` based on supported tool/easy-launch posture.
- [ ] 1.2 Persist the selected prompt mode into the specialist catalog launch payload and the generated compatibility preset so new specialists store explicit unattended or interactive startup intent.

## 2. Specialist Inspection And Launch Behavior

- [ ] 2.1 Update `project easy specialist get` to report stored launch posture as part of specialist metadata.
- [ ] 2.2 Keep `project easy instance launch` thin by honoring stored specialist launch payload during brain construction and runtime launch, with coverage for both unattended and explicit interactive specialists.

## 3. Verification And Docs

- [ ] 3.1 Add or update CLI tests covering Claude/Codex unattended defaults, `--no-unattended`, unsupported-tool behavior, and generated preset/catalog output.
- [ ] 3.2 Update operator-facing docs for `project easy specialist create` and `project easy instance launch` to explain the default unattended posture, the `--no-unattended` opt-out, and the specialist-owned configuration model.

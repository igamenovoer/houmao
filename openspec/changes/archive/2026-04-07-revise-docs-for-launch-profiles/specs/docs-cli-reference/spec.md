## MODIFIED Requirements

### Requirement: CLI reference documents the top-level project agents presets surface

The `houmao-mgr` CLI reference SHALL document the canonical low-level recipe surface and the compatibility preset alias as one resource family.

At minimum, that coverage SHALL:

- list `project agents recipes list|get|add|set|remove` as the canonical low-level source-recipe administration surface,
- list `project agents presets list|get|add|set|remove` as the compatibility alias for the same named recipe resources,
- describe recipe files as living under `agents/presets/<name>.yaml`,
- list `project agents launch-profiles list|get|add|set|remove` as the canonical low-level explicit-launch-profile administration surface,
- describe explicit launch-profile files as living under `agents/launch-profiles/<name>.yaml`,
- explain that `project agents roles` is prompt-only role management,
- state that `project agents roles scaffold` is not part of the supported low-level CLI.

The CLI reference SHALL extend the `houmao-mgr project` command-shape tree so that `project agents` lists `roles`, `recipes`, `presets`, `launch-profiles`, and `tools <tool>`, and so that `project easy` lists `specialist`, `profile`, and `instance`.

The CLI reference SHALL document `houmao-mgr project easy profile create|list|get|remove` as the easy-lane reusable specialist-backed birth-time launch-profile administration surface, and SHALL document `houmao-mgr project easy instance launch --profile <name>` as the easy-profile-backed instance launch path with the `--profile`/`--specialist` mutual exclusion rule.

The CLI reference SHALL document `houmao-mgr agents launch --launch-profile <name>` as the explicit-launch-profile-backed managed launch path, and SHALL document the `--launch-profile`/`--agents` mutual exclusion rule. The reference SHALL state that the effective provider defaults from the resolved profile source when that source already determines one tool family, and that supplying `--provider` together with `--launch-profile` is accepted only when it matches the resolved source.

The CLI reference SHALL describe the launch-time effective-input precedence as: source recipe defaults → launch-profile defaults → direct CLI overrides, and SHALL state that direct CLI overrides such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir` do not rewrite the stored launch profile.

The CLI reference SHALL state that the launch-profile-backed launch resolution applies through the same shared model whether the operator started from an easy profile through `project easy instance launch --profile` or from an explicit launch profile through `agents launch --launch-profile`.

The CLI reference SHALL link to `docs/getting-started/launch-profiles.md` for the shared conceptual model rather than restating that model on the CLI reference page itself.

#### Scenario: Reader sees canonical recipes and the compatibility preset alias in the project agents reference

- **WHEN** a reader looks up `houmao-mgr project agents` in the CLI reference
- **THEN** the page documents `project agents recipes list|get|add|set|remove`
- **AND THEN** the page documents `project agents presets list|get|add|set|remove` as the compatibility alias for the same files under `agents/presets/<name>.yaml`
- **AND THEN** it does not present `roles presets ...` or `roles scaffold` as the supported surface

#### Scenario: Reader sees the explicit launch-profile surface in the project agents reference

- **WHEN** a reader looks up `houmao-mgr project agents` in the CLI reference
- **THEN** the page documents `project agents launch-profiles list|get|add|set|remove` as the canonical low-level explicit-launch-profile surface
- **AND THEN** the page describes those files as living under `agents/launch-profiles/<name>.yaml`

#### Scenario: Reader sees the easy profile surface in the project easy reference

- **WHEN** a reader looks up `houmao-mgr project easy` in the CLI reference
- **THEN** the page documents `project easy profile create|list|get|remove`
- **AND THEN** the page documents `project easy instance launch --profile <name>`
- **AND THEN** the page documents the `--profile`/`--specialist` mutual exclusion rule on `instance launch`

#### Scenario: Reader sees `agents launch --launch-profile` documented with its precedence rules

- **WHEN** a reader looks up `houmao-mgr agents launch` in the CLI reference
- **THEN** the page documents `--launch-profile <name>` as the explicit-launch-profile-backed launch input
- **AND THEN** the page documents the `--launch-profile`/`--agents` mutual exclusion rule
- **AND THEN** the page documents the precedence order as recipe defaults, then launch-profile defaults, then direct CLI overrides
- **AND THEN** the page states that direct CLI overrides such as `--agent-name`, `--auth`, and `--workdir` do not rewrite the stored launch profile

#### Scenario: Reader sees the project command-shape tree extended for the new subtrees

- **WHEN** a reader checks the `Command shape` overview in the CLI reference
- **THEN** `project agents` lists `roles`, `recipes`, `presets`, `launch-profiles`, and `tools <tool>`
- **AND THEN** `project easy` lists `specialist`, `profile`, and `instance`

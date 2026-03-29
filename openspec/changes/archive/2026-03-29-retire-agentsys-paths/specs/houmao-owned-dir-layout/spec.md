## ADDED Requirements

### Requirement: Maintained local default paths retire `.agentsys*` path families
Maintained workspace-local and run-local default path families that currently derive from `.agentsys` or `.agentsys-*` for agent-definition working trees or scratch outputs SHALL use `.houmao` or another Houmao-owned path family instead.

When the system derives a default ambient agent-definition root from a working directory without explicit CLI override, environment override, or discovered project config, that default SHALL be `<working-directory>/.houmao/agents`.

When maintained runtime or demo helpers require a workspace-local fallback scratch directory that previously lived under a `.agentsys*`-named sibling, that default SHALL instead live under `<working-directory>/.houmao/`.

This requirement applies to active maintained workflows and helper code. Historical or archival material MAY continue to mention retired `.agentsys` paths when it is clearly not part of the supported live surface.

#### Scenario: Ambient no-config agent-definition root uses `.houmao`
- **WHEN** the system needs a default agent-definition root for working directory `/repo/app`
- **AND WHEN** no explicit override, no env override, and no discovered `.houmao/houmao-config.toml` are present
- **THEN** the default ambient agent-definition root is `/repo/app/.houmao/agents`
- **AND THEN** the system does not derive `/repo/app/.agentsys/agents`

#### Scenario: Workspace-local fallback scratch path avoids `.agentsys*`
- **WHEN** a maintained helper needs a workspace-local fallback scratch directory under `/repo/app`
- **AND WHEN** no more specific manifest-adjacent or explicit output root applies
- **THEN** the helper derives that fallback path under `/repo/app/.houmao/`
- **AND THEN** it does not derive a sibling path such as `/repo/app/.agentsys-headless-turns`

#### Scenario: Maintained demo-generated agent tree uses `.houmao`
- **WHEN** a maintained demo run generates a run-local working tree under `/tmp/demo-run/workdir`
- **THEN** the generated agent-definition tree is derived under `/tmp/demo-run/workdir/.houmao/agents`
- **AND THEN** the maintained workflow does not generate `/tmp/demo-run/workdir/.agentsys/agents`

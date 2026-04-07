# houmao-mgr-project-agents-launch-profiles Specification

## Purpose
Define the low-level `houmao-mgr project agents launch-profiles` workflow for managing explicit recipe-backed launch profiles under `.houmao/agents/launch-profiles/`.

## Requirements

### Requirement: `houmao-mgr project agents launch-profiles` manages explicit recipe-backed launch profiles
`houmao-mgr` SHALL expose a low-level launch-profile administration subtree shaped as:

```text
houmao-mgr project agents launch-profiles <verb>
```

At minimum, `project agents launch-profiles` SHALL expose:

- `list`
- `get`
- `add`
- `set`
- `remove`

The help text for this subtree SHALL present it as management for recipe-backed reusable birth-time launch profiles stored under `.houmao/agents/launch-profiles/`.

#### Scenario: Operator sees the project agents launch-profiles tree
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles --help`
- **THEN** the help output lists `list`, `get`, `add`, `set`, and `remove`
- **AND THEN** the help output presents `project agents launch-profiles` as management for `.houmao/agents/launch-profiles/`

### Requirement: `project agents launch-profiles` manages named explicit launch-profile resources
`houmao-mgr project agents launch-profiles add --name <profile> --recipe <recipe>` SHALL create one named explicit launch-profile resource that targets exactly one existing recipe.

At minimum, launch-profile content SHALL support:
- required source recipe reference
- optional managed-agent name or id defaults
- optional working directory
- optional auth override
- optional operator prompt-mode override
- optional durable env defaults
- optional declarative mailbox config
- optional launch posture defaults
- optional prompt overlay

`launch-profiles get --name <profile>` SHALL report the profile name, source recipe, source path, and parsed profile fields as structured output.

`launch-profiles list` SHALL enumerate existing launch-profile files and SHALL support filtering by source recipe or tool when that information is derivable from the referenced recipe.

`launch-profiles set --name <profile>` SHALL patch the named launch-profile resource without replacing unspecified advanced blocks.

`launch-profiles remove --name <profile>` SHALL delete one launch-profile resource without deleting the referenced recipe.

The explicit launch-profile surface SHALL remain recipe-backed and SHALL NOT silently assume easy-only defaults that are specific to the easy lane.

#### Scenario: Add creates an explicit launch profile for one recipe
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe cuda-coder-codex-default --agent-name alice --workdir /repos/alice-cuda`
- **THEN** the command creates `.houmao/agents/launch-profiles/alice.yaml`
- **AND THEN** the written launch profile records recipe `cuda-coder-codex-default`, managed-agent name `alice`, and workdir `/repos/alice-cuda`

#### Scenario: Set patches one launch profile without dropping advanced blocks
- **WHEN** `.houmao/agents/launch-profiles/alice.yaml` exists with mailbox and prompt-overlay blocks
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --auth reviewer-creds`
- **THEN** the command updates only the edited launch-profile fields
- **AND THEN** the launch profile still retains its pre-existing mailbox and prompt-overlay blocks

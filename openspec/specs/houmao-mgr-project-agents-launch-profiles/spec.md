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
- optional model override by name
- optional normalized reasoning override by level `1..10`
- optional operator prompt-mode override
- optional durable env defaults
- optional declarative mailbox config
- optional launch posture defaults
- optional prompt overlay

`launch-profiles add` SHALL accept `--model <name>` to store a reusable model override for that profile.

`launch-profiles add` SHALL accept `--reasoning-level <1..10>` to store a reusable normalized reasoning override for that profile.

`launch-profiles set` SHALL support updating that stored model through `--model <name>` and clearing it through `--clear-model`.

`launch-profiles set` SHALL support updating the stored reasoning override through `--reasoning-level <1..10>` and clearing it through `--clear-reasoning-level`.

`launch-profiles get --name <profile>` SHALL report the profile name, source recipe, source path, and parsed profile fields as structured output.

`launch-profiles list` SHALL enumerate existing launch-profile files and SHALL support filtering by source recipe or tool when that information is derivable from the referenced recipe.

`launch-profiles set --name <profile>` SHALL patch the named launch-profile resource without replacing unspecified advanced blocks.

`launch-profiles remove --name <profile>` SHALL delete one launch-profile resource without deleting the referenced recipe.

The explicit launch-profile surface SHALL remain recipe-backed and SHALL NOT silently assume easy-only defaults that are specific to the easy lane.

#### Scenario: Add creates an explicit launch profile with one stored model override
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe cuda-coder-codex-default --agent-name alice --workdir /repos/alice-cuda --model gpt-5.4-mini --reasoning-level 4`
- **THEN** the command creates `.houmao/agents/launch-profiles/alice.yaml`
- **AND THEN** the written launch profile records recipe `cuda-coder-codex-default`, managed-agent name `alice`, workdir `/repos/alice-cuda`, model override `gpt-5.4-mini`, and reasoning override `4`

#### Scenario: Set patches one launch profile model without dropping advanced blocks
- **WHEN** `.houmao/agents/launch-profiles/alice.yaml` exists with mailbox and prompt-overlay blocks
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --model gpt-5.4-nano`
- **THEN** the command updates only the edited launch-profile fields
- **AND THEN** the launch profile still retains its pre-existing mailbox and prompt-overlay blocks

#### Scenario: Set can clear the stored model override
- **WHEN** `.houmao/agents/launch-profiles/alice.yaml` exists with stored model override `gpt-5.4-mini`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --clear-model`
- **THEN** the stored launch profile no longer records a profile-owned model override
- **AND THEN** later launches fall back to the source recipe or lower-precedence model source unless another override is supplied

#### Scenario: Set can clear the stored reasoning override
- **WHEN** `.houmao/agents/launch-profiles/alice.yaml` exists with stored reasoning override `4`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --clear-reasoning-level`
- **THEN** the stored launch profile no longer records a profile-owned reasoning override
- **AND THEN** later launches fall back to the source recipe or lower-precedence reasoning source unless another override is supplied

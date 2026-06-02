## ADDED Requirements

### Requirement: Direct brain build CLI is internal native-agent plumbing
The maintained direct brain-build CLI entrypoint SHALL live under `houmao-mgr internals native-agent`.

The top-level `houmao-mgr brains build` command SHALL NOT be presented as a maintained public manager workflow. Ordinary project users SHALL launch through project or managed-agent launch surfaces instead of invoking brain construction directly.

The internal direct build command SHALL preserve the existing build behavior for constructing brain homes from native-agent recipes, setup bundles, credential selections, launch overrides, and runtime-root options.

#### Scenario: Direct build uses internal command path
- **WHEN** an operator needs to build a brain home directly from native-agent material
- **THEN** the maintained CLI path is `houmao-mgr internals native-agent brain build`
- **AND THEN** the command accepts native-agent build inputs equivalent to the retained direct build contract

#### Scenario: Ordinary project launch remains the user path
- **WHEN** an operator wants to start a managed agent from a project profile
- **THEN** the maintained ordinary path is `houmao-mgr project agents launch`
- **AND THEN** the operator does not need to run direct brain-build plumbing manually

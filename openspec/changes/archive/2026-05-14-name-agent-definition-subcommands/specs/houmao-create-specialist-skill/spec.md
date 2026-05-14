## ADDED Requirements

### Requirement: `houmao-specialist-mgr` compatibility wrapper routes renamed agent-definition subcommands
If `houmao-specialist-mgr` remains packaged, it SHALL identify `houmao-agent-definition` as the canonical owner for `specialists`, `profiles`, `create-agent-fast-forward`, `launch-agent`, and `stop-agent`.

The wrapper SHALL use `create-agent-fast-forward` as the primary name for the one-pass specialist-to-easy-profile workflow and SHALL treat older ready-profile wording as compatibility terminology.

#### Scenario: Compatibility wrapper names fast-forward path
- **WHEN** an agent opens `houmao-specialist-mgr`
- **THEN** the wrapper points one-pass profile preparation requests to `houmao-agent-definition` and `create-agent-fast-forward`
- **AND THEN** it does not present ready-profile generation as an independent wrapper-owned workflow

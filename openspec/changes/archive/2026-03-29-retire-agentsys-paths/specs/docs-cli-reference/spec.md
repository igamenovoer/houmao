## ADDED Requirements

### Requirement: CLI reference uses `.houmao` ambient resolution and deprecation-only legacy notes
Repo-owned CLI reference docs that describe agent-definition-directory resolution for active commands, or that mention deprecated compatibility entrypoints, SHALL describe ambient agent-definition resolution as:

1. explicit CLI `--agent-def-dir`,
2. `AGENTSYS_AGENT_DEF_DIR`,
3. nearest ancestor `.houmao/houmao-config.toml`,
4. default fallback `<cwd>/.houmao/agents`.

When the CLI reference explains the discovered project path, it SHALL describe `.houmao/houmao-config.toml` as the overlay discovery anchor and `.houmao/agents/` as the compatibility projection used by file-tree consumers. It SHALL NOT present `<cwd>/.agentsys/agents` as a supported default or fallback path.

The CLI reference SHALL keep `houmao-cli` and `houmao-cao-server` in explicit deprecation-only posture rather than re-elevating them to primary operator workflows.

#### Scenario: Reader sees `.houmao` ambient fallback in the CLI reference
- **WHEN** a reader checks the CLI reference for agent-definition-directory resolution
- **THEN** the page describes the `.houmao`-based precedence contract
- **AND THEN** it does not present `<cwd>/.agentsys/agents` as a supported fallback

#### Scenario: Deprecated entrypoints remain deprecation-only while using current precedence
- **WHEN** a reader scans the CLI reference for mentions of `houmao-cli` or `houmao-cao-server`
- **THEN** those mentions remain brief legacy/deprecation notes
- **AND THEN** any documented ambient agent-definition resolution uses the `.houmao`-based fallback contract rather than preserving `.agentsys`

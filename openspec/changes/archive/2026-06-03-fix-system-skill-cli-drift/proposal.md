## Why

Recent `houmao-mgr` CLI changes split live-agent operations into explicit `agents global`, `agents single`, and `agents self` scopes, and the command-template renderer has been retired. A follow-up audit of packaged Houmao system skills found stale command guidance that would cause installed skills to tell agents to run removed or incorrectly scoped commands.

## What Changes

- Update packaged system-skill guidance so live-session adoption uses `houmao-mgr agents self join --agent-name ...` rather than the removed root-level `houmao-mgr agents join ...` shape.
- Update managed-memory guidance so live memory commands use `houmao-mgr agents self memory ...` for current-session work and `houmao-mgr agents single --agent-name|--agent-id ... memory ...` for selected-agent work, rather than removed `houmao-mgr agents memory ...` commands.
- Update managed-agent mail fallback guidance so `mail move` uses the current `--destination-box` option instead of stale `--box`.
- Remove remaining generic command-template wording from packaged skills now that executable commands are documented directly and config drafts are limited to YAML authoring.
- Add focused content and CLI-shape tests so packaged skills do not drift back to removed command families or retired command-template terminology.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-manage-agent-instance-skill`: align join guidance with the current scoped `agents self join` command and remove surviving command-template wording.
- `houmao-memory-mgr-skill`: align live memory guidance with current `agents self memory` and `agents single ... memory` command scopes.
- `houmao-agent-email-comms-skill`: align fallback mail move guidance with `--destination-box` and remove surviving command-template wording.
- `houmao-agent-gateway-skill`: remove surviving command-template wording from direct gateway-command guidance.
- `houmao-mailbox-mgr-skill`: remove surviving command-template wording from direct mailbox-command guidance.
- `houmao-agent-loop-pairwise-v2-skill`: align legacy routing prose with the current scoped managed-memory surfaces.
- `houmao-agent-loop-pairwise-v3-skill`: align legacy routing prose with the current scoped managed-memory surfaces.
- `houmao-agent-loop-pairwise-v4-skill`: align legacy routing prose with the current scoped managed-memory surfaces.

## Impact

- Affected packaged assets: `src/houmao/agents/assets/system_skills/**`.
- Affected tests: system-skill content tests and focused `houmao-mgr` CLI-shape assertions.
- No runtime CLI behavior changes are intended; this is a contract and packaged-guidance correction against the current `houmao-mgr` surface.

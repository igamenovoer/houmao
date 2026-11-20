# Proposal

## Why

The maintained managed-agent fixture creates every specialist with `--no-system-skills`, so every manager-surface fixture run lacks the `houmao-agent-entrypoint` and `houmao-shared-routines` packs that a normal managed launch installs by default. This makes fixture-based qualification unrepresentative: the recent two-agent mailbox test had no mailbox skill pack, fell back to the notifier's bare API summary, and made avoidable schema-guessing calls. The fixture should exercise the default managed-agent surface, not silently disable it.

## What Changes

- Stop passing `--no-system-skills` when the fixture creates its managed specialist. The managed-launch default `agent` pack remains in effect.
- Add an explicit fixture-level opt-out for isolation cases that intentionally need a minimal home, for example `prepare --no-system-skills`.
- Record the effective system-skill choice in `run.json` so reports and follow-up commands can distinguish a default-pack run from an opt-out run.
- Update the fixture README and tests to assert the default and the opt-out paths.
- Leave raw-surface fixtures unchanged; they do not create a managed specialist. Leave the historical `scripts/explore/houmao-3-0-interactive-review/iter1_dsh.py` helper unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-fixture-contracts`: add a requirement that maintained managed-agent fixture runs preserve the managed-launch default `agent` system-skill pack unless the run explicitly opts out, and that the fixture records and documents that choice.

## Impact

- `scripts/agents/test-fixtures/fixturelib/prepare.py`: specialist creation and `run.json` metadata.
- `scripts/agents/test-fixtures/fixturelib/config.py`: resolved fixture configuration field for the system-skill choice.
- `scripts/agents/test-fixtures/fixture.py`: `prepare` CLI opt-out.
- `scripts/agents/test-fixtures/README.md`: default behavior and opt-out documentation.
- `tests/integration/agents/test_agent_fixture_launches.py` and focused unit coverage: default-pack and opt-out assertions.
- No production runtime, gateway, or mailbox behavior changes.

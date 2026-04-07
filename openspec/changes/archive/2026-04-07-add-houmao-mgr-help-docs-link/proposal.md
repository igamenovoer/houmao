## Why

`houmao-mgr --help` currently shows the command tree and root options, but it does not direct readers to the published long-form documentation. New operators who discover the CLI from a local install or shell completion have no obvious next step for finding the full reference and guides.

## What Changes

- Add a documented top-level `houmao-mgr --help` affordance that points readers to the published Houmao documentation site for more detailed guides and reference material.
- Define the expected placement and wording at the root help surface so the docs link is visible without requiring a subcommand.
- Keep the existing command tree and option listing unchanged apart from the added docs-discovery text.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `houmao-srv-ctrl-native-cli`: The root `houmao-mgr` help surface will gain a discoverable link to the published detailed documentation.

## Impact

- Affected code: `src/houmao/srv_ctrl/commands/main.py`
- Affected UX: root `houmao-mgr --help` output and bare `houmao-mgr` invocation help text
- Likely follow-on validation: CLI help tests and CLI reference docs that describe the root help surface

## Why

Houmao currently stores system-skill lifecycle ownership in a generically named `receipt.json`, even though the file is authoritative configuration used by install, sync, status, doctor, upgrade, and uninstall. Rename that state to an explicitly Houmao-owned skill configuration and reduce it to the smallest data set needed for release identification, projection integrity, and overlapping pack ownership.

## What Changes

- Replace `<tool-home>/.houmao/system-skills/<tool>/receipt.json` with `<tool-home>/.houmao/system-skills/<tool>/houmao-skill-config.json`.
- Replace the receipt model and schema with strict `houmao-skill-config.v1` configuration terminology throughout lifecycle APIs, command output, managed-home provenance, tests, and documentation.
- Record only the config schema version, installing Houmao release, collection projection mode, and one minimal ownership record per installed standalone skill.
- Derive the selected pack set from per-skill `owning_pack_ids` rather than duplicating it at the top level.
- Preserve transaction ordering: validate and commit projections first, then atomically write the configuration; remove the configuration after the final owned skill is uninstalled.
- **BREAKING** Remove all recognition, migration, and fallback behavior for every `receipt.json` schema. Existing users must remove or uninstall the old system-skill installation and reinstall it.
- Continue allowing `system-skills doctor` to inspect configless copy-paste and Skills CLI installations directly from installed roots.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-system-skill-installation`: Replace receipt-owned lifecycle state with the minimal breaking `houmao-skill-config.v1` ownership configuration.
- `houmao-mgr-system-skills-cli`: Rename structured and plain lifecycle output from receipt terminology to skill-config terminology and define configless collision behavior.
- `docs-cli-reference`: Document the new path, minimal fields, version meanings, clean-reinstall requirement, and config-independent doctor behavior.

## Impact

The change affects `src/houmao/agents/system_skill_lifecycle.py`, its public facade and doctor evidence models, `houmao-mgr system-skills` payloads and renderers, managed brain construction provenance, system-skill lifecycle and CLI tests, and the system-skills reference. Existing `receipt.json` files are intentionally ignored; old projected roots remain unowned collisions until users clean and reinstall them.

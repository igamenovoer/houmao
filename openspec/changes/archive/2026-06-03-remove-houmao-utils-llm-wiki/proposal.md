## Why

`houmao-utils-llm-wiki` is no longer wanted as a Houmao-packaged system skill. Keeping it in the catalog, docs, specs, and packaged assets makes it look like a supported Houmao surface even though the intended direction is to remove that responsibility completely.

## What Changes

- **BREAKING**: Remove `houmao-utils-llm-wiki` from the current packaged system-skill catalog and from every install set or auto-install selection.
- **BREAKING**: Delete the packaged asset tree at `src/houmao/agents/assets/system_skills/houmao-utils-llm-wiki/`.
- **BREAKING**: Treat `houmao-utils-llm-wiki` as an unknown system skill rather than a current or retired Houmao-owned skill; Houmao will not preserve hidden cleanup semantics for external copies or user-managed symlinks.
- Remove documentation and examples that teach `houmao-utils-llm-wiki` as a packaged Houmao system skill or managed-launch system-skill selector.
- Update tests and specs so the supported system-skill inventory and default installs no longer include the LLM Wiki utility.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-system-skill-installation`: Remove the requirement that the LLM Wiki utility asset is packaged or installable, and require hard removal from current and retired Houmao-owned inventory.
- `houmao-mgr-system-skills-cli`: Remove CLI inventory, install, status, and uninstall expectations for `houmao-utils-llm-wiki`; explicit selection should fail as an unknown system skill.
- `houmao-system-skill-flat-layout`: Remove flat-layout and projection requirements specific to the LLM Wiki utility skill.
- `houmao-system-skill-families`: Update utility-group expectations so only currently packaged utilities remain.
- `docs-system-skills-overview-guide`: Remove overview-guide requirements that list or route to the LLM Wiki utility system skill.
- `docs-cli-reference`: Remove CLI-reference requirements and examples for installing the LLM Wiki utility system skill.
- `docs-readme-system-skills`: Remove README requirements that list the LLM Wiki utility as a packaged Houmao system skill.
- `brain-launch-runtime`: Remove managed-launch scenarios that use `houmao-utils-llm-wiki` as a valid additive packaged system skill.
- `houmao-mgr-project-agents-launch-profiles`: Replace launch-dossier examples that use `houmao-utils-llm-wiki` as a valid packaged system-skill selector.
- `houmao-mgr-project-easy-cli`: Replace specialist/profile examples that use `houmao-utils-llm-wiki` as a valid packaged system-skill selector.
- `agent-launch-profiles`: Replace launch-profile examples that use `houmao-utils-llm-wiki` as a valid additive system-skill policy.

## Impact

- Affected packaged assets: `src/houmao/agents/assets/system_skills/catalog.toml`, `src/houmao/agents/assets/system_skills/houmao-utils-llm-wiki/`, and related package data.
- Affected runtime code: system-skill constants, catalog validation, selection tests, install/sync/uninstall/status tests, and project/profile policy tests that currently reference `houmao-utils-llm-wiki`.
- Affected docs: system-skills overview/reference pages plus agent-definition, launch-profile, and easy-specialist examples that currently use the LLM Wiki utility.
- External user-managed skill copies, local skill-home symlinks, and other out-of-catalog usage are intentionally out of scope; operators clean those manually.

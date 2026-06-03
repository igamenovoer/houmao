## REMOVED Requirements

### Requirement: LLM Wiki utility skill uses the flat packaged asset layout
**Reason**: The LLM Wiki utility skill is no longer packaged as a Houmao-owned system skill, so it has no maintained packaged asset layout.

**Migration**: Remove `src/houmao/agents/assets/system_skills/houmao-utils-llm-wiki/` and do not include a catalog `asset_subpath` for the removed skill.

### Requirement: LLM Wiki utility skill keeps flat visible projection paths
**Reason**: The removed LLM Wiki utility is no longer projected into tool-native skill homes by Houmao.

**Migration**: Do not install or project `houmao-utils-llm-wiki` through Houmao system-skill workflows. Operators clean any existing tool-home paths manually.

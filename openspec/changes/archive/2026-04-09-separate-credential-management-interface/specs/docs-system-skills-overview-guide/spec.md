## ADDED Requirements

### Requirement: System-skills overview guide uses the dedicated credential-management routing
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL describe `houmao-credential-mgr` as routing through the dedicated credential-management families rather than through `project agents tools <tool> auth ...`.

At minimum, the guide SHALL state that `houmao-credential-mgr` routes credential work through:

- `houmao-mgr project credentials <tool> ...` for active project overlays,
- `houmao-mgr credentials <tool> ... --agent-def-dir <path>` for explicit plain agent-definition directories.

The guide SHALL continue to describe `houmao-credential-mgr` as the credential-management skill distinct from specialist authoring, role/recipe authoring, instance lifecycle, and mailbox administration.

#### Scenario: Reader sees the new credential routing in the narrative guide
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the `houmao-credential-mgr` entry points to `project credentials ...` and `credentials ... --agent-def-dir <path>` as the supported command families
- **AND THEN** the guide does not present `project agents tools <tool> auth ...` as the canonical credential-management route

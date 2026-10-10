## REMOVED Requirements

### Requirement: Houmao packages managed auto skills separately from system skills
**Reason**: The only managed auto skill implemented Kimi role-prompt delivery, which Kimi 0.34.0 and later support natively.

**Migration**: Remove the auto-skill asset lane and rebuild maintained Kimi brains with native `SYSTEM.md` projection.

### Requirement: Auto system prompt skill defines trigger metadata and workflow body
**Reason**: Kimi no longer needs an agent-invoked workflow to retrieve and apply its Houmao role prompt.

**Migration**: Use the role prompt that Houmao projects before Kimi starts.

### Requirement: Auto-skill names are reserved managed-launch names
**Reason**: Houmao no longer has managed auto-skill names or a separate auto-skill projection category.

**Migration**: Treat ordinary project and system skills under their existing collision and ownership rules.

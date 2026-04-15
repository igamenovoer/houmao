## REMOVED Requirements

### Requirement: Getting-started docs explain managed workspace scratch and persist lanes
**Reason**: Getting-started docs must no longer teach the removed workspace lane model.

**Migration**: Replace the managed workspace guide with a managed-agent memory guide centered on `houmao-memo.md` and `pages/`.

## ADDED Requirements

### Requirement: Getting-started docs explain managed memory memo and pages
Getting-started documentation SHALL explain the default managed-agent memory layout, the `houmao-memo.md` file, the `pages/` directory, and the current memory environment variables.

The docs SHALL NOT show `--persist-dir`, `--no-persist-dir`, scratch-lane examples, or persist-lane examples as current managed-agent memory workflows.

The docs SHALL explain that durable work artifacts belong in the launched workdir or explicit project paths, while Houmao managed memory is for small notes and indexed pages.

#### Scenario: New user sees memo-pages memory layout
- **WHEN** a new user reads the managed memory getting-started page
- **THEN** the page shows `<active-overlay>/memory/agents/<agent-id>/houmao-memo.md`
- **AND THEN** the page shows `<active-overlay>/memory/agents/<agent-id>/pages/`
- **AND THEN** it explains that `houmao-memo.md` indexes the pages directory
- **AND THEN** it does not show `--persist-dir` or `--no-persist-dir` examples

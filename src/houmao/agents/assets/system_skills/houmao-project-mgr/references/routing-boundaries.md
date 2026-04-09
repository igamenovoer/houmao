# Routing Boundaries

Use this reference when a project-related task is close to another renamed Houmao skill and the ownership line needs to stay explicit.

## `houmao-project-mgr` Owns

- project overlay lifecycle: `project init`, `project status`
- project layout and overlay-resolution explanation
- explicit recipe-backed launch-profile management: `project agents launch-profiles ...`
- project-scoped easy-instance inspection or stop: `project easy instance list|get|stop`

## Route To Other Renamed Skills

- `houmao-specialist-mgr` for `project easy specialist ...`, `project easy profile ...`, and easy `project easy instance launch|stop`
- `houmao-credential-mgr` for `project credentials <tool> list|get|add|set|rename|remove` and `credentials <tool> ... --agent-def-dir <path>`
- `houmao-agent-definition` for `project agents roles ...` and `project agents recipes ...`
- `houmao-agent-instance` for general live-agent lifecycle after project-scoped routing
- `houmao-mailbox-mgr` for `mailbox ...`, `project mailbox ...`, and `agents mailbox ...`

## Notes

- Project launch-profile `--auth` changes are profile authoring, not auth-bundle CRUD.
- Project context explanations may mention other command families, but that does not transfer ownership of those workflows away from their dedicated skills.
- Do not use obsolete `houmao-manage-*` identifiers as current routing targets.

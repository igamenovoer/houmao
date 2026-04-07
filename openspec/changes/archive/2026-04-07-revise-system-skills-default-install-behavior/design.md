## Context

`houmao-mgr system-skills` is currently stricter than the intended operator workflow. The live CLI in [system_skills.py](/data1/huangzhe/code/houmao/src/houmao/srv_ctrl/commands/system_skills.py) requires both an explicit `--home` and an explicit selection input (`--default`, `--set`, or `--skill`), and the current OpenSpec contract encodes that exact shape.

That strictness is now a liability for the common case. Operators already think in terms of a tool-native project home, and the supported tools already expose native home redirection env vars:

- Claude: `CLAUDE_CONFIG_DIR`
- Codex: `CODEX_HOME`
- Gemini: `GEMINI_CLI_HOME`

The current design also has one tool-specific asymmetry that must stay explicit: Gemini's effective home root is the directory that contains both `.gemini/` provider state and `.agents/skills/` skill projection. That means the project-scoped Gemini default home is `<cwd>`, not `<cwd>/.gemini`.

This change is cross-cutting because it touches:

- CLI parsing and help text,
- effective-home resolution behavior,
- how CLI-default selection is requested,
- tests and examples,
- CLI reference documentation.

## Goals / Non-Goals

**Goals:**

- Make `system-skills install` and `system-skills status` usable with only `--tool` in the common case.
- Resolve omitted `--home` using a stable precedence order that respects tool-native env redirection.
- Remove the special `--default` flag and make omitted `--set` and `--skill` mean CLI-default selection.
- Preserve explicit key-value selection through repeatable `--set` and `--skill`.
- Keep Gemini's default path aligned with the existing `.agents/skills` contract.

**Non-Goals:**

- Changing the shared installer's projection contract or tool-visible skill destinations.
- Changing Houmao-managed launch or join auto-install behavior.
- Rebinding Gemini's maintained skill destination from `.agents/skills` to `.gemini/skills`.
- Inferring homes from running sessions, project overlays, or unrelated filesystem scans.

## Decisions

### Decision: Resolve omitted homes in the CLI layer, not in the shared installer

The `system-skills` CLI will resolve one effective home path before it calls the shared installer or state loader. The shared installer will continue to operate on an explicit `home_path`.

This keeps the lower-level installer contract simple and reusable while letting the operator-facing CLI adopt project-aware defaults.

Alternatives considered:

- Move default-home inference into the shared installer: rejected because it would couple a generic path-based installer to CLI-specific invocation context.
- Infer homes from active sessions or project overlay state: rejected because explicit external-home installation should remain independent from runtime/session discovery.

### Decision: Use one fixed precedence order for omitted `--home`

When `--home` is omitted, both `install` and `status` will resolve the effective home with this precedence:

1. explicit `--home`
2. tool-native home env var
3. project-scoped default home

The project-scoped defaults will be:

- Claude: `<cwd>/.claude`
- Codex: `<cwd>/.codex`
- Gemini: `<cwd>`

This keeps the CLI predictable and aligns with tool-native redirect behavior without forcing operators to repeat the same paths on every command.

Alternatives considered:

- Ignore tool-native env vars for explicit system-skill operations: rejected because it would surprise users who already redirected the tool home through the tool's own supported mechanism.
- Use `<cwd>/.gemini` as the Gemini home default: rejected because the maintained Gemini contract projects skills into `<home>/.agents/skills`, so `<cwd>/.gemini` would produce the wrong project-scoped skill path and muddy the relationship between Gemini provider state and Gemini skill projection.

### Decision: Remove `--default` and make omitted selection mean CLI-default installation

`--default` will be removed from the public `system-skills install` surface. When neither `--set` nor `--skill` is provided, the command will request the packaged `cli_default_sets` selection.

This preserves the packaged catalog as the authority for "default" while simplifying the public interface to one explicit selection style: key-value flags for overrides, omission for defaults.

Alternatives considered:

- Keep `--default` as a deprecated alias: rejected because it preserves needless surface area and weakens the new default-selection contract.
- Require at least one `--set` or `--skill` forever: rejected because it keeps the command artificially verbose for the dominant operator path.

### Decision: Keep tool-home metadata small and explicit for this CLI surface

The command-side effective-home resolver will use a maintained tool-to-env-var and tool-to-project-default mapping rather than loading the full project-agent adapter catalog just to discover three home env vars.

This keeps `system-skills` independent from project-catalog parsing and makes the resolution contract easy to test directly.

Alternatives considered:

- Load starter-agent adapters and derive the home env var dynamically: rejected for now because it adds extra parsing and coupling to a command that only needs a small stable contract for three supported tools.

## Risks / Trade-offs

- [Breaking flag removal] → Existing invocations that use `system-skills install --default` will fail until operators switch to omitting both `--set` and `--skill`. Mitigation: update docs, tests, and help text together and call out the migration explicitly.
- [Gemini default-home asymmetry] → Operators may assume Gemini should default to `<cwd>/.gemini` because Claude and Codex use dot-directories. Mitigation: document clearly that the effective Gemini home is `<cwd>`, which yields skill projection under `<cwd>/.agents/skills`.
- [Repo-local writes from omitted `--home`] → Running `system-skills install --tool <tool>` will now create or update project-scoped tool homes by default. Mitigation: document the precedence order and keep explicit `--home` as the highest-precedence override.
- [Mapping drift between CLI home-resolution metadata and starter-agent adapters] → The small maintained mapping could diverge from adapter metadata over time. Mitigation: centralize the mapping in one helper and cover env-precedence behavior with focused CLI tests.

## Migration Plan

1. Update the `system-skills` CLI contract to remove `--default`, make `--home` optional, and resolve effective homes with the new precedence order.
2. Extend CLI tests to cover explicit-home precedence, env-backed redirection, project-scoped defaults, Gemini's `<cwd>` home root, omitted-selection default installs, and rejection of the removed `--default` flag.
3. Update `docs/reference/cli/system-skills.md`, `docs/reference/cli/houmao-mgr.md`, and any related examples that still show explicit-home-only behavior or `--default`.
4. Ship the change without data migration. Existing homes and install-state files remain valid because the shared installer/state model continues to operate on the resolved explicit home path.

## Open Questions

- None.

## Context

`houmao-agent-definition` was recently unified so one skill owns low-level roles/recipes, explicit launch profiles, easy specialists, easy profiles, ready profile generation, and limited easy launch/stop routing. The entry page now has many branches, but they are named as conceptual lanes. That is weak for users who want to invoke a specific branch by name, and it leaves "profile" ambiguous between the common easy-profile path and the low-level recipe-backed launch-profile path.

The maintained CLI names do not need to change. This design only changes the skill-level vocabulary and routing rules used by agents reading the skill.

## Goals / Non-Goals

**Goals:**

- Give every top-level `houmao-agent-definition` branch a stable subcommand-like name.
- Make easy profiles the default meaning of `profile`, `agent profile`, and loosely stated `launch profile`.
- Reserve `raw-profiles` for low-level recipe-backed launch profiles.
- Rename the one-pass specialist-to-easy-profile workflow to `create-agent-fast-forward`.
- Keep compatibility wording for older terms, but make the new terms primary.
- Keep the top-level skill concise and make detailed branch behavior live in local subskill pages.

**Non-Goals:**

- Rename `houmao-mgr` CLI commands or persisted on-disk profile formats.
- Remove `houmao-specialist-mgr` compatibility behavior.
- Launch agents from `create-agent-fast-forward`.
- Rework credential, mailbox, workspace, or live lifecycle ownership.

## Decisions

### Skill Subcommands Are User-Facing Handles

The entry page should expose a compact command vocabulary:

| Subcommand | Route |
|---|---|
| `roles` | low-level prompt-only role management |
| `recipes` | low-level recipe management, with `presets` as compatibility alias |
| `raw-profiles` | low-level recipe-backed launch profiles |
| `specialists` | project-easy specialist templates |
| `profiles` | specialist-backed easy profiles |
| `create-agent-fast-forward` | create/select specialist and create/update easy profile in one pass |
| `launch-agent` | limited easy launch entry point |
| `stop-agent` | limited easy stop entry point |

Alternative considered: keep descriptive branch names only. That keeps the current shape, but users cannot reliably ask for a branch without restating a sentence of intent.

### `profiles` Means Easy Profiles By Default

When the user says "profile", "agent profile", or even "launch profile" without explicitly naming recipe-backed or raw behavior, route to `profiles`. This matches the normal user intent: they want the higher-level specialist-backed profile that can store launch defaults.

Alternative considered: preserve "launch profile" as the default low-level interpretation because it matches the CLI noun. That is technically literal but user-hostile in the skill layer, where users tend to speak in product-level concepts rather than low-level command names.

### `raw-profiles` Names The Low-Level Escape Hatch

The skill should call the low-level recipe-backed lane `raw-profiles`, while clearly documenting that it still runs `houmao-mgr project agents launch-profiles ...`. The "raw" label communicates that this is the less common lower-level lane and prevents it from stealing the default meaning of profile.

Alternative considered: `launch-profiles-raw`. That preserves the CLI noun but is longer and less natural as a skill subcommand.

### `create-agent-fast-forward` Replaces Ready-Profile Wording

The old wording makes "ready agent/profile" sound like a persisted object type. The workflow is actually a fast-forward through two authoring stages:

```text
specialist -> easy profile -> launch command
```

The new name should be `create-agent-fast-forward`, with early text saying it creates a launchable profile definition and does not launch a live managed agent.

Alternative considered: `create-ready-agent`. That is shorter, but it strengthens the false impression that this creates a live or special "ready agent" resource.

## Risks / Trade-offs

- Existing docs and specs still use "ready profile" in many places -> update references in one pass and keep compatibility wording only where useful for migration.
- Users may interpret `create-agent-fast-forward` as live launch -> the subskill must state "does not launch" in its first screen and output rules.
- `raw-profiles` differs from the underlying CLI noun -> document the exact CLI mapping beside the subcommand name.
- Stale generic `actions/*` pages may conflict with the new subcommand router -> either route them through the new subcommands or mark them as legacy low-level-only material.

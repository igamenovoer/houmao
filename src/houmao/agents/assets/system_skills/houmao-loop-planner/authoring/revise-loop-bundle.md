# Revise A Loop Bundle

Use this page when a loop bundle already exists, but the user wants to simplify it, change the master or participant set, tighten the calling boundaries, revise completion or stop behavior, or rerender the top-level graph.

## Workflow

1. Read `plan.md` first, then the supporting files that the current bundle already references.
2. Identify what is changing:
   - loop kind
   - master
   - participant set
   - participant-local boundaries
   - execution behavior
   - distribution instructions
   - completion or stop behavior
3. Preserve the canonical simplified bundle shape from `references/dir-structure.md`.
4. Keep the authored meaning Markdown-first and keep TOML minimal.
5. Revalidate the required section headings through `references/section-conventions.md`.
6. Rerender the Mermaid graph in `plan.md` if the topology, completion, or stop posture changed.
7. Refresh `profile.toml` and `runs/charter.template.toml` if the profile metadata or runtime handoff fields changed.

## Revision Guardrails

- Do not expand the bundle back into many small TOML policy files by default.
- Do not move authored bundle content into agent-local runtime directories.
- Do not leave stale participant or distribution guidance in place after changing the topology.
- Do not treat a revision request as permission to start the run.

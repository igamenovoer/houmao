## Context

The previous scoped-agent CLI change removed root-level lifecycle paths such as `houmao-mgr agents launch`, `houmao-mgr agents stop`, and `houmao-mgr agents cleanup`. Public managed-agent birth now belongs to `houmao-mgr project agents launch`, while follow-up lifecycle and cleanup for one already-known local managed agent belongs to `houmao-mgr agents single --agent-id/--agent-name ...`.

`tests/fixtures/plain-agent-def/` remains valuable, but its role is narrower: it is tracked, secret-free native-agent seed material for direct internals and copied temp roots. It is not a maintained public launch root. The fixture docs and the Claude official-login manual smoke helper still blur that boundary, and one probe found that direct brain-build docs and behavior disagree for repo-relative preset paths and explicit empty-skill presets.

## Goals / Non-Goals

**Goals:**

- Make `tests/fixtures/plain-agent-def/` guidance match the current native-agent root layout and scoped CLI vocabulary.
- Keep the tracked fixture secret-free while preserving a useful path for smoke tests that need local auth bundles.
- Move the Claude official-login smoke flow onto maintained public launch and selected-agent cleanup paths.
- Make direct native-agent brain-build behavior coherent for fixture presets, including preset selector forms and explicit empty skill lists.
- Add focused regression coverage for stale command paths and fixture build semantics.

**Non-Goals:**

- Reintroduce root-level `houmao-mgr agents launch|stop|cleanup` compatibility.
- Convert `tests/fixtures/plain-agent-def/` into a project overlay or generated `.houmao/agents` compatibility projection.
- Commit plaintext local credential material.
- Rewrite legacy demo packs under `src/houmao/demo/legacy/` unless they are directly exercised by the maintained smoke flow.

## Decisions

1. Treat `plain-agent-def` as seed/native material, not a public launch source.

   The fixture should keep `roles/`, `presets/`, `skills/`, `launch-profiles/`, and `tools/` because those are the direct native-agent contracts. Public launch examples should not tell operators to launch directly from this tree. The maintained launch path is to create or use a project overlay, register the needed prompt/credential/skills there, and call `project agents launch`.

   Alternative considered: add a new direct public launch command for plain roots. That would reopen the root-launch ambiguity that the scoped CLI change intentionally removed.

2. Rework the official-login smoke helper around a temporary project overlay.

   The helper should still source prompt material from `tests/fixtures/plain-agent-def/roles/server-api-smoke/system-prompt.md` and credential material from `tests/fixtures/auth-bundles/claude/official-login/`. It should materialize any vendor-login files into temp local state, register a project credential/specialist in a fresh temp project, launch with `project agents launch --specialist ... --headless`, then stop and clean up through `agents single --agent-id ...`.

   Alternative considered: keep using a temp copied direct-dir root and only swap cleanup commands. That cannot use the maintained public birth path because direct native-agent roots are no longer public launch sources.

3. Make direct brain build accept explicit preset paths and explicit no-skill presets.

   `internals native-agent brain build --preset` should accept three practical selector forms: bare preset name, absolute path, and an existing path relative to the invocation cwd. A preset with `skills: []` should mean "project no user fixture skills" rather than "missing input"; missing skill input should still fail when no preset or explicit skill selection provides a list.

   Alternative considered: require every smoke preset to bind a no-op skill. That would work around current validation but would make "no fixture skills" unrepresentable and would obscure tests for minimal launch material.

## Risks / Trade-offs

- Project-backed smoke setup is more verbose than the old direct launch helper -> Keep helper functions small and assert each setup phase so failures point at credential, specialist, launch, or cleanup setup.
- Allowing empty skill lists could hide accidental missing skills -> Only treat empty skills as valid when the selected preset explicitly contains `skills: []`; no-preset direct builds without `--skill` still fail.
- Supporting cwd-relative preset paths adds resolver ambiguity -> Prefer existing filesystem paths first, then fall back to native-root named preset resolution.
- Local auth material may be absent in ordinary checkouts -> Keep provider launch tests manual/local-only and cover command-shape/build behavior with hermetic unit or CLI tests.

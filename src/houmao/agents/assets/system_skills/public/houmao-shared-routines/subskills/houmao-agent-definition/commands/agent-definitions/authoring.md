# Agent Definition Authoring

## Purpose

Turn the user's freeform agent requirements into one portable, immutable Houmao agent-definition revision. Preserve the staged boundary:

```text
intent/src -> intent/derived -> materialization preview -> approved immutable revision
```

The source contract has one required file, `intent/src/agent-def-overview.md`. Put all supplied requirements there. When the author needs more source files, link to them from that overview and keep every reference inside `intent/src/`.

## Workflow

1. Resolve the authoring workspace and choose one maintained `houmao-mgr` launcher for the turn.
2. Initialize only when the workspace does not already exist:

   ```bash
   houmao-mgr project agent-definitions init-intent <workspace>
   ```

   Use `--overview-file <path>` only when the user supplied an existing overview. Do not replace an existing intent workspace.
3. Help the user complete `intent/src/agent-def-overview.md`. Record purpose, operating method, required skills and source directories, deploy-time parameters, runtime variables and consumers, named mindsets, optional private-workspace contract, and any linked freeform material. Do not impose a fixed source-file taxonomy.
4. Write one reviewed operator interpretation and one normalized `materialization.toml`, then record them with explicit skill sources:

   ```bash
   houmao-mgr project agent-definitions derive <workspace> \
     --interpretation-file <interpretation-markdown> \
     --materialization-file <materialization-toml> \
     --skill <skill-directory>
   ```

   The materialization file maps the role and memo source files under `intent/src` to revision-local destinations and declares definition, deployment, and instance contracts. Repeat `--skill` for every complete skill directory named by the overview, including an explicit external source path when the user's requirement names one. Role, memo, and supporting-file references must stay under `intent/src`. Skill directories are copied into derived materials and must be real confined trees without symbolic links, special files, or reserved system-skill names.
5. Inspect `intent/derived/interpretation.md`, `materialization.toml`, copied materials, and `validation.json`. Resolve every warning or missing contract field before approval.
6. Bind approval to the exact source and derived digests:

   ```bash
   houmao-mgr project agent-definitions approve <workspace> --approved-by <operator>
   ```

7. Preview before writing an immutable revision:

   ```bash
   houmao-mgr project agent-definitions materialize <workspace> --preview
   ```

8. After the user accepts the preview, materialize to the requested immutable revision root:

   ```bash
   houmao-mgr project agent-definitions materialize <workspace> --output <revision-root>
   ```

9. Validate the resulting exact revision:

   ```bash
   houmao-mgr project agent-definitions validate <revision-root>
   ```

If the request does not map cleanly to these phases, use the native planning tool to build a step-by-step plan from this workflow, the revision contracts, the actor gate, and the user request, then execute the plan.

## Contracts

- Source intent remains user-owned freeform material. Derived files are the operator agent's explicit interpretation.
- A revision contains `definition.toml`, `deploy-contract.toml`, `instance-contract.toml`, immutable assets, and provenance. Its digest covers semantic contents, not a wall-clock timestamp.
- Deploy inputs use exact typed markers. Runtime-variable markers are separate and resolve at launch snapshot time.
- A skill that consumes a live runtime value must contain and use `houmao-mgr agents self instance-state variables get <key>`.
- A mindset-required skill must run `houmao-mgr agents self instance-state mindsets snapshot --skill <skill>` before substantive work and stop when the snapshot fails.
- Reusable definition material must not contain credentials, tokens, secret defaults, machine-local paths, or unresolved external dependencies.

## Guardrails

- DO NOT synthesize source requirements that the user did not provide; record unresolved points in the derived interpretation.
- DO NOT approve stale derived material after any source or derived change.
- DO NOT write a revision before preview and approval.
- DO NOT edit a materialized revision in place. Revise the intent and create another immutable revision.
- DO NOT replace a user-authored skill with a summary. Copy its complete confined directory.

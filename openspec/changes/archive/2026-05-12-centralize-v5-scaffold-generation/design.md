## Context

The v5 loop skill currently repeats scaffold shape and starter-file guidance across `create-intention`, `execplan-fast-forward`, `execplan-step-by-step`, staged execplan pages, validation guidance, and developer reference docs. The repeated prose already covers the same directory trees and starter artifacts, but each route still tells the agent to synthesize the scaffold manually.

That approach is fragile for two reasons. First, changing the scaffold contract requires editing several instruction pages and can leave one route behind. Second, the skill has no authoritative packaged scaffold assets, so placeholder Markdown and starter TOML are reconstructed by the agent instead of copied from versioned templates.

The repo already packages skills as file bundles, so the natural fit is to move scaffold ownership into bundled resources inside `houmao-agent-loop-pairwise-v5` and make routed pages call that shared surface.

## Goals / Non-Goals

**Goals:**
- Centralize v5 scaffold creation behind one Python script that lives inside the v5 skill package.
- Version the starter Markdown and TOML content as packaged template assets instead of restating them in several prose pages.
- Cover all scaffold-producing routes: `init`, `execplan-fast-forward`, `execplan-step-by-step`, and final-doc generation.
- Keep the generated scaffold shape identical to the existing contract unless the proposal/spec explicitly changes it.
- Make step-by-step generation able to opt into `execplan/adrs/` while sharing the same generator and template set.

**Non-Goals:**
- Replace the later staged generation logic for process, contract, harness, skill, or agent-binding content that is genuinely derived from loop intent.
- Introduce a heavyweight templating dependency such as Jinja for local scaffold generation.
- Change the v5 package contract, directory layout, or runtime model beyond what is needed to centralize scaffold ownership.

## Decisions

### Use one stdlib Python scaffold generator under the v5 skill package

Create a script under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/scripts/` that owns scaffold materialization. Use Python stdlib only so the skill stays self-contained and does not add runtime dependencies.

The script should expose named scaffold profiles rather than one-off file writes embedded in prose:
- `intention-init`
- `execplan-shell`
- `execplan-stepwise-shell`
- `execplan-finalize-docs`

Each profile writes only the directories and starter files it owns. Stage-specific derived artifacts remain owned by their existing staged generation logic.

Alternative considered: keep shell creation inline in each page and only centralize the examples.
Rejected because it still leaves multiple execution paths synthesizing the same files independently.

### Store starter files as packaged assets, not inline prose templates

Put scaffold content under an asset/template subtree inside the v5 skill package, for example:

```text
houmao-agent-loop-pairwise-v5/
  scripts/
    scaffold.py
  assets/
    scaffolds/
      intention/
        README.md.tmpl
        loop-overview.md.tmpl
      execplan/
        manifest.toml.tmpl
        README.md.tmpl
        docs/
          artifact-index.md.tmpl
          operator-guide.md.tmpl
          runtime-model.md.tmpl
          validation.md.tmpl
        adrs/
          execplan-adr.md.tmpl
```

Markdown and TOML starter files are output assets, so `assets/` is the right ownership boundary. The top-level skill prose should point to the script and profile names, not restate file bodies.

Alternative considered: put templates in `references/`.
Rejected because scaffold templates are output resources, not reading material for the model.

### Use simple placeholder substitution with explicit input fields

The scaffold generator should substitute a small, explicit variable set:
- `loop_dir_name`
- `loop_slug`
- `generated_date`
- `plan_revision`
- `include_execplan_adrs`

Use a simple stdlib substitution mechanism such as `string.Template` or a tiny custom token replacer. The goal is deterministic generation, not freeform rendering logic.

Alternative considered: fully dynamic template logic in the script.
Rejected because it would move domain decisions back into code and make the scaffold harder to audit.

### Make routes share profiles instead of duplicating scaffold instructions

Refactor the routed pages so they invoke the shared scaffold surface conceptually:
- `create-intention` uses `intention-init`
- `execplan-fast-forward` uses `execplan-shell`
- `execplan-step-by-step` uses `execplan-stepwise-shell`
- `execplan-finalize` uses `execplan-finalize-docs`

The pages should still describe when to use each route and which inputs are required, but they should stop describing file-by-file starter creation where the generator already owns it.

Alternative considered: have `execplan-step-by-step` build on `execplan-fast-forward` and then mutate the scaffold ad hoc.
Rejected because the only scaffold difference is `execplan/adrs/`, which is clearer as an explicit profile flag.

### Keep stage-derived artifacts outside the initial shell generator

The generator should not create domain-derived process, contract, harness, skill, or agent-binding content that depends on loop intent. Those remain under:
- `execplan-specs-process`
- `execplan-specs-contract`
- `execplan-harness`
- `execplan-skills`
- `execplan-agent-bindings`

The generator may create empty directories or placeholder files that those stages later replace when the current contract requires a known starter artifact, but it must not invent derived semantics.

Alternative considered: generate full canonical placeholders for every stage-owned file.
Rejected because it would blur the boundary between shell scaffolding and actual staged generation.

## Risks / Trade-offs

- [Script and prose drift] -> Keep the script/profile names referenced directly in the routed pages and validation rules so any scaffold change has one authoritative implementation surface.
- [Too much logic in templates] -> Limit templates to starter structure and light placeholder substitution; keep intent-derived semantics in staged generators.
- [Filesystem differences for repeated runs] -> Make the script idempotent by default, with clear overwrite rules for starter files it owns.
- [Validation ambiguity] -> Update validation guidance so starter assets created by the scaffold generator remain distinguishable from later stage-owned generated artifacts.

## Migration Plan

1. Add the scaffold generator script and packaged scaffold templates to the v5 skill.
2. Update v5 authoring pages to reference the shared generator profiles instead of restating starter creation in prose.
3. Update the v5 capability spec and developer design docs to make the generator/templates the authoritative scaffold source.
4. Adjust validation guidance so the expected scaffolded files and directories align with the shared generator surface.
5. Verify the skill package with the existing skill validator and targeted repo checks.

Rollback is straightforward: remove the script/templates and restore the previous prose-based scaffold instructions. No runtime data migration is needed because the change only affects how new scaffold files are produced.

## Open Questions

- Whether the scaffold assets should live under `assets/scaffolds/` or a narrower `assets/templates/` path. The design works with either; `assets/scaffolds/` is more descriptive.
- Whether the generator should emit manifest seed content directly or create an empty manifest placeholder that `execplan-finalize` always replaces. The safer default is a minimal seed that `execplan-finalize` rewrites authoritatively.

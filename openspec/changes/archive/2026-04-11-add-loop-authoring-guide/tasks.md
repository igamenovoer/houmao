## 1. New Loop Authoring Guide Page

- [x] 1.1 Create `docs/getting-started/loop-authoring.md` with a skill-selection table comparing `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v2`, and `houmao-agent-loop-generic` by lifecycle verbs, prestart model, and targeted topology.
- [x] 1.2 Add a "Pairwise-v2: Routing Packets" section explaining what routing packets are, what `initialize` does, how the default `precomputed_routing_packets` strategy differs from `operator_preparation_wave`, and that `graph high packet-expectations` / `validate-packets` are the CLI helpers.
- [x] 1.3 Add a "Generic Loop Graphs" section introducing `houmao-agent-loop-generic`: what a generic loop graph is (typed pairwise + relay components), when to use it, and a pointer to the skill's SKILL.md.
- [x] 1.4 Add a "Graph Tooling" pointer section linking to `docs/reference/cli/internals.md` as the CLI reference for `graph high analyze`, `packet-expectations`, `validate-packets`, `slice`, and `render-mermaid`.
- [x] 1.5 Add a "Next Steps" or footer section linking to each skill's SKILL.md, `system-skills-overview.md`, and `internals.md`.

## 2. Update docs/index.md

- [x] 2.1 Add a link to `getting-started/loop-authoring.md` in the Getting Started section of `docs/index.md` with a description covering loop skill selection and the routing-packet model.

## 3. Update README

- [x] 3.1 Add a compact three-row skill-selection table or brief list to the README §4 "Agent Loop" section (before the pairwise walkthrough) that names all three loop skills with one-line descriptions and links to `docs/getting-started/loop-authoring.md`.
- [x] 3.2 Add an `internals graph` reference to the README CLI Entry Points section — as a note on the `houmao-mgr` row or a dedicated line — describing it as loop-plan graph analysis and packet validation tooling.

## 4. Sync Specs to Main

- [x] 4.1 Write `openspec/specs/docs-loop-authoring-guide/spec.md` from the delta spec.
- [x] 4.2 Merge the ADDED requirement from `specs/docs-getting-started/spec.md` into `openspec/specs/docs-getting-started/spec.md`.
- [x] 4.3 Merge the ADDED requirements from `specs/docs-readme-system-skills/spec.md` into `openspec/specs/docs-readme-system-skills/spec.md`.

## 5. Verification

- [x] 5.1 Run `pixi run openspec validate add-loop-authoring-guide --strict` and confirm no errors.
- [x] 5.2 Verify `docs/getting-started/loop-authoring.md` exists and covers all four spec requirements (selection table, routing-packet model, generic orientation, internals link).
- [x] 5.3 Verify `docs/index.md` has the loop-authoring link in Getting Started.
- [x] 5.4 Verify README §4 mentions all three loop skills and links to the guide; verify CLI Entry Points has an internals graph reference.

## 1. Terminology Inventory

- [x] 1.1 Build a current text inventory for `pairwise loop`, `pairwise-tree`, `pairwise edge-loop`, `generic graph`, `generic-graph`, `generic loop`, and existing pairwise-named skill identifiers under `src/houmao/agents/assets/system_skills/`.
- [x] 1.2 Classify each hit as canonical terminology to change, compatibility alias to keep, package identity to preserve, generated-machine value to alias, or unrelated use of tree/worktree terminology.
- [x] 1.3 Confirm no task requires renaming system-skill directories, frontmatter `name` fields, package handles, or explicit invocation names.

## 2. Pro Topology Terminology

- [x] 2.1 Revise `houmao-agent-loop-pro` entrypoint and `agents/openai.yaml` to prefer tree-loop and generic-loop terminology.
- [x] 2.2 Revise pro topology reference pages so `tree-loop` and `generic-loop` are preferred values and `pairwise-tree`, `pairwise-loop`, `pairwise`, `generic-graph`, and `generic graph` are documented aliases.
- [x] 2.3 Revise pro authoring pages so clarification and generation ask about tree loop versus generic loop before using lower-level alias terms.
- [x] 2.4 Revise pro contract, harness, generated-skill, agent-binding, and validation guidance to generate preferred topology values while accepting legacy aliases.
- [x] 2.5 Revise pro design/reference docs only where they describe current skill behavior, leaving historical examples or explicit compatibility notes intact.

## 3. Pairwise-Named Tree Loop Skills

- [x] 3.1 Revise `houmao-agent-loop-pairwise` user-facing text, metadata, templates, authoring pages, operating pages, and references to present tree loop terminology while preserving package and invocation names.
- [x] 3.2 Revise `houmao-agent-loop-pairwise-v2` user-facing text and metadata to present enriched tree loop terminology while preserving pairwise-named runtime paths and compatibility references.
- [x] 3.3 Revise `houmao-agent-loop-pairwise-v3` user-facing text and metadata to present workspace-aware tree loop terminology while preserving pairwise-named runtime paths and compatibility references.
- [x] 3.4 Revise `houmao-agent-loop-pairwise-v4` user-facing text and metadata to present template-driven workspace-aware tree loop terminology while preserving strict template and compatibility references.
- [x] 3.5 Revise `houmao-agent-loop-pairwise-v5` user-facing text and metadata to present tree loop terminology without adding extra v5 branding outside the skill identity.

## 4. Generic And Elemental Pattern Skills

- [x] 4.1 Revise `houmao-agent-loop-generic` to use generic loop as the canonical family name while keeping graph wording for graph artifacts, helper commands, and compatibility notes.
- [x] 4.2 Revise generic loop component prose so existing `pairwise` component types are explained as local-close or tree-loop component aliases rather than new canonical family names.
- [x] 4.3 Revise `houmao-adv-usage-pattern` to present the elemental two-agent protocol as a local-close edge loop and retain pairwise edge-loop as an alias.
- [x] 4.4 Revise `houmao-touring` to present tree loop and generic loop as the main advanced loop families while routing to existing pairwise-named skill handles.

## 5. OpenSpec And Documentation Alignment

- [x] 5.1 Update current OpenSpec specs listed in this change when implementation reveals missing terminology requirements or alias rules.
- [x] 5.2 Update user-facing documentation outside system skills only when it directly repeats current system-skill selection guidance and would otherwise contradict the renamed terminology.
- [x] 5.3 Leave completed historical change artifacts unchanged unless an implementation or validation surface treats them as current guidance.

## 6. Verification

- [x] 6.1 Run text checks to confirm current system-skill guidance prefers `tree loop`, `tree-loop`, `generic loop`, `generic-loop`, and `local-close edge loop` in canonical explanatory contexts.
- [x] 6.2 Run text checks to confirm `pairwise loop`, `pairwise-tree`, `generic graph`, `generic-graph`, and `pairwise edge-loop` remain only as aliases, package identities, filenames, existing machine values, or compatibility notes.
- [x] 6.3 Run text checks to confirm pairwise-named skill directories, frontmatter names, package handles, and explicit invocation names were not renamed.
- [x] 6.4 Run routed-page link checks for modified system-skill Markdown links and `Read First` references.
- [x] 6.5 Run `git diff --check`.
- [x] 6.6 Run `openspec status --change rename-pairwise-loop-to-tree-loop --json` or equivalent validation and confirm the change is apply-ready.

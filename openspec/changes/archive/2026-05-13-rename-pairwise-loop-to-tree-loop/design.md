## Context

Houmao has accumulated several related loop terms. Older specialized skills and specs use "pairwise loop" for composed local-close tree execution. The newer pro skill introduces topology modes named `pairwise-tree` and `generic-graph`. Advanced usage patterns also use "pairwise edge-loop" for the elemental two-agent driver/worker protocol.

The user-facing distinction we want is simpler:

| Canonical term | Preferred machine value | Compatibility aliases | Meaning |
| --- | --- | --- | --- |
| Tree loop | `tree-loop` | `pairwise loop`, `pairwise-tree`, `pairwise-only`, `pairwise` where already emitted | Tree or forest of local-close handoffs; normal results return to immediate upstream. |
| Generic loop | `generic-loop` | `generic graph`, `generic-graph` | Directed graph loop; may include non-tree routes or cycles when context, dedupe, termination, and result routing are explicit. |
| Local-close edge loop | unchanged where package paths require compatibility | `pairwise edge-loop` | Elemental two-agent driver/worker protocol that a tree loop or generic loop may compose. |

Existing skill package names such as `houmao-agent-loop-pairwise-v5` are installed handles and should not be renamed by this change.

## Goals / Non-Goals

**Goals:**

- Make "tree loop" the canonical user-facing name for local-close tree or forest loop execution.
- Make "generic loop" the canonical user-facing name for directed graph loop execution.
- Preserve existing pairwise-named skill package names and aliases.
- Teach `houmao-agent-loop-pro` to generate `tree-loop` and `generic-loop` as preferred topology mode values while accepting legacy values.
- Update system-skill guidance so invoked agents ask clear tree-versus-generic questions.
- Keep old terminology visible only where it helps alias compatibility, package identity, or historical references.

**Non-Goals:**

- Do not rename system-skill asset directories, frontmatter `name` fields, or explicit invocation names.
- Do not change runtime behavior, mailbox behavior, gateway behavior, workspace behavior, or generated harness mechanics.
- Do not change existing generated loop directories outside repository skill assets.
- Do not remove support for `pairwise loop`, `pairwise-tree`, or `generic-graph` in existing generated material.

## Decisions

### Decision: Rename concepts, not installed skill identities

Keep existing package names and activation names such as `houmao-agent-loop-pairwise`, `houmao-agent-loop-pairwise-v5`, and older versioned pairwise skills. Present them as tree-loop skills whose legacy invocation names contain "pairwise".

Alternative considered: rename directories and skill names to `houmao-agent-loop-tree`. That would be a breaking installed-skill identity migration and would need catalog, install, docs, and user-workflow compatibility work. It is unnecessary for the terminology cleanup.

### Decision: Prefer `tree-loop` and `generic-loop` as generated topology mode values

`houmao-agent-loop-pro` should prefer `tree-loop` and `generic-loop` in newly generated process specs, topology contracts, manifests, validation notes, and examples. Validation and update guidance should accept aliases:

- `tree-loop`: aliases `pairwise-tree`, `pairwise-loop`, and `pairwise` when encountered in older generated material.
- `generic-loop`: aliases `generic-graph` and `generic graph`.

Alternative considered: keep machine values as `pairwise-tree` and `generic-graph` but change prose only. That leaves skill-invoked agents asking the wrong high-level question and keeps the confusing old term in the generated contract surface.

### Decision: Use "local-close edge loop" for elemental two-agent behavior

The advanced-usage elemental protocol should be described as a local-close edge loop. The old phrase "pairwise edge-loop" remains an alias because filenames and existing references use it.

Alternative considered: rename the pattern file. That creates link churn and possible installed-skill reference breakage without changing the protocol.

### Decision: Update broad system-skill guidance, not every historical OpenSpec sentence

Implementation should update current system-skill assets and their active behavior guidance. Specs should capture new requirements and alias compatibility. Historical completed change artifacts may remain historical unless a validation check treats them as current skill guidance.

Alternative considered: globally replace every occurrence of "pairwise" in `openspec/changes/` and old proposal artifacts. That would create noisy historical churn and could obscure what earlier changes actually proposed.

## Risks / Trade-offs

- Terminology drift across old and new skills -> Add explicit alias sections and verification checks for canonical wording in current skill assets.
- Agents may over-replace `pairwise` where it names an existing package -> Require package names, frontmatter names, filenames, and explicit skill invocations to remain unchanged.
- Generated validators may reject older `pairwise-tree` or `generic-graph` execplans -> Require alias acceptance in pro validation and update guidance.
- "Tree" may be confused with Git worktrees or file trees -> Use `tree loop` in prose and `tree-loop` in generated topology values, not bare `tree`.
- Local-close edge protocol may become hard to find -> Keep pairwise aliases and pattern filenames as compatibility handles.

## Migration Plan

1. Update `houmao-agent-loop-pro` topology references, authoring routes, harness guidance, validation guidance, and metadata to prefer `tree-loop` / `generic-loop`.
2. Update pairwise-named loop skills to describe themselves as tree-loop skills with pairwise aliases, while keeping their package and activation names.
3. Update `houmao-agent-loop-generic` to prefer generic-loop wording while preserving typed component fields and legacy pairwise component labels where contracts already use them.
4. Update advanced-usage and touring skill guidance to present tree loop, generic loop, and local-close edge loop as the main user-facing terms.
5. Run text checks for stale canonical terminology and for accidental package-name rewrites.
6. Roll back by reverting text changes; no runtime data migration is needed.

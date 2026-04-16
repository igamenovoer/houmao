## Context

The tracked `llm-wiki-skill` submodule contains an all-in-one skill for creating and maintaining a persistent Markdown knowledge base. Its current root schema file is named `CLAUDE.md`, and that name appears in the skill entrypoint, scaffold generator, reference guides, and viewer deploy guidance.

The skill is agent-neutral: it can be used by Codex, Claude, or other LLM agents. Keeping a Claude-specific root filename in the public contract creates avoidable confusion and makes generated wiki roots look provider-specific.

## Goals / Non-Goals

**Goals:**
- Make `README.md` the only documented and generated wiki root schema file.
- Preserve the existing schema content and operating role: scope, naming conventions, current articles, open questions, research gaps, audit posture, and LLM-facing notes.
- Remove all `CLAUDE.md` mentions from the all-in-one skill deliverable.
- Keep the change small and textual except for the scaffold filename and output messages.

**Non-Goals:**
- No legacy `CLAUDE.md` fallback lookup.
- No migration helper for existing wiki roots.
- No changes to wiki article layout, audit file format, lint checks, viewer rendering, or Obsidian plugin behavior unless they directly mention the schema filename.

## Decisions

- Use `README.md` as the root schema filename because it is provider-neutral and already idiomatic for root-level project context.
- Treat this as a clean breaking rename, not a compatibility layer. The skill is experimental and the user explicitly requested no `CLAUDE.md` support or wording.
- Update prose and generated scaffold artifacts together so documentation and behavior do not diverge.
- Keep the reference guide path `references/schema-guide.md`; only its title and content need to change because the guide still describes the same schema concept.

## Risks / Trade-offs

- Existing wiki roots that contain only `CLAUDE.md` will not match the new documented contract → Accept as an intentional breaking change; users can rename the file manually.
- `README.md` can be mistaken for a reader-facing introduction rather than an LLM operating contract → Mitigate by consistently describing it as the wiki root schema and operating contract.
- Submodule changes must be made inside `extern/tracked/llm-wiki-skill` and then recorded in the parent repository as a new submodule commit pointer → Verify both submodule and parent status before commit.

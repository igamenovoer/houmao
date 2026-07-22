## Why

The current actor-pack implementation composes protected skill trees at installation time, while its checked-in public entrypoints refer to nested files that do not exist in their own directories. That makes the source skills incomplete for copy-paste installation and `npx skills`, and the compaction lacks a strict contract that preserves the behavior of the original pre-compaction skills.

## What Changes

- **BREAKING**: Replace runtime skill composition with six complete, host-discoverable directories under `system_skills/public/`: `houmao-admin-welcome`, `houmao-admin-entrypoint`, `houmao-agent-entrypoint`, `houmao-shared-routines`, `houmao-agent-loop-pro`, and `houmao-agent-loop-lite`.
- Make `houmao-shared-routines` a public advanced-user skill. It owns sixteen parent-scoped `subskills/<logical-id>/SKILL-MAIN.md` routines and supports direct invocation without an actor entrypoint, while preserving target validation and runtime authorization.
- Keep pro and lite agent-loop skills as standalone public skills because users often invoke them directly. Actor entrypoints and shared routines route loop work to these siblings instead of nesting or duplicating them.
- Turn both actor entrypoints into static mega routers. Each lists its supported route subcommands and relevant shared subskills, establishes the admin or verified-agent actor frame, then delegates ordinary work to the installed `houmao-shared-routines` sibling and loop work to the selected top-level loop skill. Neither entrypoint refers to a local `subskills/` tree.
- Preserve `houmao-admin-welcome` as the read-only, state-aware first-user tour modeled after Isomer's independent welcome skill. It keeps the maintained pre-compaction touring paths and hands executable work to `houmao-admin-entrypoint`.
- Preserve skill meaning against Git commit `8f377c468bc7f87ff40dbf40c0a68327616112bd`, the last skill tree before actor compaction. Structural changes may alter discovery, ownership, and actor routing, but SHALL preserve each skill's triggers, public operations and aliases, inputs, outputs, gates, blockers, evidence handoffs, side effects, stop conditions, and help behavior. The former `houmao-specialist-mgr` wrapper remains a compatibility route alias to agent-definition rather than a standalone skill.
- Rewrite every standalone skill, parent-scoped subskill, and executable command page to the current Imsight skill-handling format: role-canonical entrypoint names, a concise numbered `## Workflow` near the top, the correct collection-of-routines or complex-procedure subcommand layout, explicit `When to Route Here` guidance, standard invocation notation where used, and concise `DO NOT` guardrails. Discovery metadata SHALL preserve manual versus implicit activation intent.
- **BREAKING**: Replace the v3 protected-mount manifest and composer with a static-collection manifest. Installation stages byte-identical copies or direct symlinks of complete source directories and never generates Markdown, renders placeholders, filters routines, or mounts one skill into another.
- Update pack ownership so `admin` installs welcome, admin entrypoint, shared routines, pro loop, and lite loop; `agent` installs agent entrypoint, shared routines, pro loop, and lite loop; and installing both deduplicates the three shared top-level dependencies without unsafe uninstall behavior.
- Make the public source root usable with copy-paste and Skills CLI installation. Exact-`SKILL.md` discovery SHALL expose exactly the six standalone skills, while nested `SKILL-MAIN.md` files remain parent-scoped.
- Keep generated mailbox and notifier prompts on `houmao-agent-entrypoint`, but treat the managed route as installed only when both the agent entrypoint and shared-routines sibling are present; otherwise retain the API fallback.
- Supersede the runtime-composition decisions in `refactor-system-skills-by-actor` and `adopt-protected-skill-main-entrypoints`; retain their actor distinction and scanner-safe child entrypoints where those decisions remain compatible with this static design.

## Capabilities

### New Capabilities

- `houmao-system-skill-static-collection`: Defines the six static standalone skill roots, the sixteen shared parent-scoped routines, byte-preserving distribution, Skills CLI discovery, and the ban on runtime composition.
- `houmao-system-skill-sibling-routing`: Defines admin, managed-agent, direct-shared, and direct-loop actor postures plus delegation between standalone sibling skills.
- `houmao-system-skill-semantic-preservation`: Defines the pre-compaction Git baseline and Imsight-format conformance without changing operational meaning.

### Modified Capabilities

- `houmao-system-skill-installation`: Install complete static skill directories, model shared pack dependencies, and remove protected-tree composition.
- `houmao-system-skill-flat-layout`: Use six flat standalone public roots while keeping only shared routines parent-scoped beneath `houmao-shared-routines`.
- `houmao-system-skill-families`: Keep admin and agent packs but give them overlapping static top-level dependencies.
- `houmao-mgr-system-skills-cli`: Report and manage static pack members and shared ownership rather than composed protected mounts.
- `houmao-system-skill-help-operation`: Preserve read-only help across the six public skills and all migrated shared routines.
- `agent-mailbox-system-skills`: Require the agent entrypoint and shared-routines sibling before generated prompts use the skill route.
- `houmao-touring-skill`: Preserve the complete touring behavior under `houmao-admin-welcome` and its executable handoff.
- `houmao-create-specialist-skill`: Preserve the specialist compatibility meaning as an admin/shared route alias to agent-definition.
- `docs-system-skills-overview-guide`: Document the six public roots, direct advanced routes, actor routing, and static installation.
- `docs-readme-system-skills`: Present copy-paste, `npx skills`, pack installation, and the complete public inventory.
- `docs-cli-reference`: Describe static pack membership, shared dependency ownership, lifecycle behavior, and direct skill invocations.
- `managed-system-skill-test-coverage`: Replace composer-focused coverage with static identity, discovery, semantic-parity, actor-route, prompt-dependency, and receipt-ownership coverage.

## Impact

This change affects packaged assets under `src/houmao/agents/assets/system_skills/`, the manifest and schema, system-skill loading and lifecycle code, pack receipts and upgrades, CLI output, managed launch and join synchronization, generated mailbox prompts, documentation, package data, and tests. Existing v3 receipt-owned installations become drifted and require transactional upgrade. Runtime CLI authorization remains authoritative; public or parent-scoped placement controls discovery and routing, not security.

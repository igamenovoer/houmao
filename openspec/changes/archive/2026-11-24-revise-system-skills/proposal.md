# Proposal

## Why

Houmao’s shipped skills omit retained gateway access and versioned peer file edits, and their tmux screen instructions can inspect the wrong server. The skill catalog and frontmatter have drifted, while unit tests tie edits to exact instruction text and obsolete workflow fixtures.

## What Changes

- Add `agent-access` and `agent-files` as parent-scoped shared routines. Expose both through the admin and managed-agent entrypoints, with execution-owner, gateway administrator, and verified peer authority explained at the operation that needs it.
- Revise gateway, instance, definition, inspection, messaging, and mail guidance. Cover browser entry, native resource refresh, saved and one-shot tmux selection, socket-qualified pane access, explicit peer selectors, and conditional attachment permissions.
- Synchronize skill route tables, read-only help, manifest commands and aliases, and the installed inventory. Keep the six standalone roots and make the manifest the inventory of direct shared children.
- **BREAKING** Move `skill_invocation_notation` and the standalone release field `houmao_version` under YAML `metadata`. Update Houmao’s manifest, doctor, and source and distribution version checks to use the same format.
- Reduce unit coverage of skill assets to entrypoint, directory, and declared resource existence. Remove tests and fixtures that assert authored text or simulate instruction semantics. Retain tests of executable Houmao behavior, including pack projection, ownership, doctor results, CLI output, and generated prompts.

## Capabilities

### New Capabilities

- `houmao-agent-access-skill` covers retained target policy, live administrator changes, and independently signed peer requests.
- `houmao-agent-files-skill` covers authorized mount discovery, inspection, private drafts, saved candidates, publication, and reconciliation.

### Modified Capabilities

- `houmao-shared-routines-skill` defines the public shared sibling, child ownership, actor eligibility, and command inventory.
- `houmao-system-skill-static-collection` defines the current child inventory beneath the six public roots.
- `houmao-system-skill-sibling-routing` uses the declared child inventory and preserves the active actor frame.
- `houmao-parent-scoped-skill-entrypoints` specifies current sibling loading, role-canonical filenames, and nested notation metadata.
- `houmao-system-skill-protected-packaging` aligns route and package validation with static sibling installation.
- `houmao-system-skill-installation` projects the complete declared child inventory.
- `houmao-system-skill-families` places every declared child beneath the shared root.
- `houmao-system-skill-flat-layout` distinguishes shared children from public discovery roots.
- `houmao-system-skill-version-metadata` defines nested release metadata.
- `houmao-mgr-system-skills-cli` aligns catalog output and doctor checks with the current inventory and metadata.
- `houmao-system-skill-help-operation` keeps help as an authoring contract and replaces prose-level test mandates with review.
- `houmao-system-skill-semantic-preservation` keeps instruction semantics and format requirements subject to review.
- `managed-system-skill-test-coverage` defines structure-only skill asset tests and retains verification of executable code.
- `docs-readme-system-skills` aligns the README with the public inventory.
- `docs-system-skills-overview-guide` documents the shared child inventory and new routes.
- `houmao-agent-gateway-skill` covers owner deployment configuration, authorized requests, and private browser handoff.
- `houmao-manage-agent-instance-skill` covers one-shot tmux selection and routable native resource operations.
- `houmao-manage-agent-definition-skill` covers saved tmux server choices in project profiles.
- `houmao-agent-inspect-skill` uses managed observations and socket-qualified local pane access.
- `houmao-agent-messaging-skill` distinguishes selectors and transport overrides.
- `houmao-agent-email-comms-skill` distinguishes ordinary mail authority from permission to include an attachment.

## Impact

The change affects shipped `system_skills/public` assets, the manifest and schema, skill diagnostics, release validation, the system-skills docs, and focused unit tests. Gateway authorization, versioned files, launch, mailbox, and native refresh still use the existing manager and gateway interfaces. The implemented `return-mail-send-receipts` change keeps its independent receipt guidance and requirements.

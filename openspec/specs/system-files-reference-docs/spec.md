# system-files-reference-docs Specification

## Purpose
TBD - created by archiving change add-system-files-reference-docs. Update Purpose after archive.

## Requirements

### Requirement: System-files reference documentation is organized under a dedicated subtree
The repository SHALL publish a centralized system-files reference under `docs/reference/system-files/` with an `index.md` entrypoint instead of leaving the full Houmao filesystem story distributed only across subsystem pages.

That subtree SHALL be discoverable from the top-level reference navigation.

The system-files reference SHALL organize detailed filesystem documentation into topic pages rather than one undifferentiated catch-all page.

The centralized subtree SHALL become the primary operator-facing filesystem inventory for broader runtime and launcher reference pages, which may keep brief local artifact context but SHALL point readers to `docs/reference/system-files/` for the canonical cross-subsystem filesystem map.

At minimum, the subtree SHALL include coverage for:

- filesystem roots and ownership boundaries,
- runtime-managed agent and session files,
- CAO launcher and CAO-home related filesystem state,
- shared-registry files,
- operator filesystem-preparation guidance.

#### Scenario: System-files entrypoint is a navigational index
- **WHEN** a reader opens the system-files reference entrypoint
- **THEN** the repository presents `docs/reference/system-files/index.md`
- **AND THEN** that page explains the structure of the system-files subtree and links to the detailed pages

#### Scenario: Top-level reference navigation reaches the system-files subtree
- **WHEN** a reader browses the top-level reference index
- **THEN** the top-level reference index links to `docs/reference/system-files/`
- **AND THEN** the new subtree is discoverable without requiring the reader to infer the location from source code or subsystem docs

#### Scenario: Broader runtime and launcher pages link to the canonical filesystem inventory
- **WHEN** a reader opens a broader runtime or launcher reference page for behavior guidance
- **THEN** that page may keep concise local artifact context
- **AND THEN** it points to `docs/reference/system-files/` for the canonical cross-subsystem filesystem inventory instead of duplicating the full map inline

### Requirement: System-files reference documentation explains Houmao root resolution and ownership boundaries
The centralized system-files reference SHALL explain how Houmao resolves its important filesystem roots and how ownership differs across those roots.

At minimum, that coverage SHALL explain:

- the default roots for the Houmao runtime root and shared-registry root,
- workspace-local job-directory derivation for runtime-managed sessions,
- the CAO launcher runtime subtree and derived default CAO home,
- precedence between explicit path overrides, env-var overrides, and built-in defaults,
- the distinction between Houmao-owned artifacts, Houmao-selected roots with external-tool-owned contents, and workspace-local scratch.

The system-files reference SHALL explicitly state that mailbox filesystem state is out of scope for this subtree and SHALL direct readers to the mailbox reference for that separate subsystem.

#### Scenario: Root-resolution guidance covers defaults and override precedence
- **WHEN** an operator needs to understand where Houmao will place runtime, registry, launcher, or job-directory state
- **THEN** the system-files reference explains the default root locations and the precedence between explicit overrides, env-var overrides, and built-in defaults
- **AND THEN** the reader can tell which override surface applies to each root

#### Scenario: Ownership guidance distinguishes Houmao-owned files from external-tool-owned contents
- **WHEN** a reader needs to understand whether Houmao owns a file tree completely or only selects the root for another tool
- **THEN** the system-files reference explains the ownership distinction explicitly
- **AND THEN** the reader can tell that CAO state under the selected launcher home is not documented as a fully Houmao-owned internal file contract

#### Scenario: Mailbox is explicitly excluded from the system-files subtree
- **WHEN** a reader uses the system-files reference to understand Houmao filesystem state
- **THEN** the subtree explains that mailbox filesystem state is documented separately
- **AND THEN** it links the reader to the mailbox reference instead of duplicating mailbox layout details in this subtree

### Requirement: System-files reference documentation inventories important lifecycle artifacts with concrete filesystem representations
The centralized system-files reference SHALL document the important files and directories that Houmao creates or manages during build, launch, session, registry-publication, gateway-capability, and CAO-launcher lifecycles.

At minimum, that artifact inventory SHALL cover:

- generated homes under the runtime root,
- generated brain manifests under the runtime root,
- runtime-managed session roots and `manifest.json`,
- gateway files nested under a runtime-managed session root when gateway capability is published,
- shared-registry `live_agents/<agent-id>/record.json`,
- CAO launcher artifacts such as pid, log, ownership, and launcher-result files,
- the derived CAO `home/` root as a Houmao-selected path.

The detailed pages SHALL use concrete filesystem representations such as tree snippets, artifact tables, or equivalent structured inventories rather than relying on prose alone.

For each important artifact or path family, the docs SHALL explain its purpose, the component that creates it, and whether the path is a stable contract versus a current implementation detail.

#### Scenario: Reader can inspect a concrete runtime and launcher artifact map
- **WHEN** a reader needs to understand which files Houmao will create for one runtime-managed session or one launcher-managed CAO server
- **THEN** the system-files reference shows representative filesystem trees or artifact tables for those paths
- **AND THEN** the reader does not need to reconstruct the storage layout from source code alone

#### Scenario: Artifact inventory explains purpose and contract level
- **WHEN** a reader inspects one artifact such as `manifest.json`, `record.json`, `ownership.json`, or `launcher_result.json`
- **THEN** the system-files reference explains what that artifact is used for and what kind of stability claim the docs make about it
- **AND THEN** the reader can distinguish stable operator-facing artifacts from opaque or implementation-detail surfaces

### Requirement: System-files reference documentation provides operator filesystem-preparation guidance
The centralized system-files reference SHALL explain how operators can prepare filesystems for Houmao before running the system.

At minimum, that guidance SHALL cover:

- which roots or parent directories may reasonably be pre-created,
- which paths must remain writable,
- how path redirection or relocation interacts with the documented override surfaces,
- which workspace-local scratch paths are good candidates for ignore rules,
- which artifact families are safe to treat as cleanup candidates versus durable state.

That guidance SHALL be written as operator-facing preparation advice rather than as implementation-only notes.

#### Scenario: Operator can prepare writable and redirected storage safely
- **WHEN** an operator wants to pre-create directories, adjust permissions, or redirect Houmao roots to another filesystem
- **THEN** the system-files reference explains which roots may be redirected and which directories must remain writable
- **AND THEN** the operator can prepare the filesystem without inferring those constraints only from source code or scattered docs

#### Scenario: Operator can tell scratch from durable state
- **WHEN** an operator wants to decide which Houmao-created directories can be treated as scratch or cleanup candidates
- **THEN** the system-files reference explains the difference between workspace-local job directories, durable runtime state, shared-registry state, and launcher-selected external-tool state
- **AND THEN** the guidance makes clear that those artifact families do not have the same cleanup expectations

### Requirement: System-files reference documentation explains Stalwart mailbox secret lifecycle boundaries
The system-files reference documentation SHALL explain how runtime-managed filesystem artifacts represent Stalwart-backed mailbox bindings without persisting inline secrets.

At minimum, the system-files reference SHALL explain:

- that the session manifest persists a secret-free mailbox binding rather than inline Stalwart credentials,
- that persisted mailbox data identifies credential material through a durable reference such as `credential_ref`,
- where runtime-owned durable credential-related artifacts live relative to the runtime root and session root,
- where session-local materialized credential files may appear when direct or gateway-backed mailbox access needs them,
- which of those path families are durable operator-facing artifacts versus current implementation-detail or secret-bearing surfaces.

That explanation SHALL keep the broader mailbox semantics in the mailbox subtree while making the filesystem placement and contract level explicit in the system-files subtree.

#### Scenario: Reader can distinguish manifest persistence from secret-bearing files
- **WHEN** a reader opens the system-files reference to understand a Stalwart-backed session root
- **THEN** the docs explain that `manifest.json` keeps a secret-free mailbox binding and not inline credentials
- **AND THEN** the docs explain where the corresponding credential reference and any materialized secret files belong in the runtime-managed filesystem model

#### Scenario: Operator can tell durable state from cleanup-sensitive secret material
- **WHEN** an operator needs to understand which Stalwart-related runtime files are durable state and which are secret-bearing or session-local artifacts
- **THEN** the system-files docs identify the relevant path families and their contract level clearly
- **AND THEN** the operator is not left to infer cleanup or handling expectations solely from source code

# Explore Log: hybrid SQLite catalog design for Houmao config storage

**Date:** 2026-03-29
**Topic:** Refactor Houmao config storage from directory-encoded relationships toward a SQLite-backed catalog while deciding what should remain file-backed
**Mode:** `openspec-explore`

## Short Answer

Moving Houmao's configuration relationships out of directory structure and into SQLite is a good direction.

The strongest design is not "everything in SQLite", but:

- SQLite as the canonical semantic catalog
- files as the canonical storage for large text blobs and tree-shaped assets
- runtime models derived from the catalog rather than from directory conventions

In that design:

```text
user intent
   |
   v
easy CLI / project API
   |
   v
catalog service
   |
   +-- SQLite: identities, references, policies, relationships
   |
   +-- file content store: prompts, auth files, setup trees, skill trees
   |
   v
runtime/build materialization
   |
   v
launch plan / session manifest / runtime state
```

This keeps extension and relationship management in the DB, while preserving the practical benefits of files for large content and tool-facing assets.

## Problem Statement

The current stack has three layers:

1. user-facing layer
   - mainly `houmao-mgr project easy`
   - specialist / instance model
   - expresses operator intent
2. storage layer
   - `.houmao/agents/...`
   - `.houmao/easy/...`
   - filesystem tree plus config files
   - relationships are partly encoded by directory structure
3. implementation layer
   - Python dataclasses and pydantic models
   - runtime-oriented shapes
   - intended to isolate implementation from raw filesystem layout

The core tension is that the storage layer currently does too much semantic work.

Examples:

- role / preset / tool association is encoded by nesting under `roles/<role>/presets/<tool>/...`
- specialist metadata stores resolved paths rather than purely logical references
- builders and loaders still depend on discovering objects through filesystem layout

That works while the graph is simple, but it becomes awkward when:

- multiple objects share the same artifact
- one object references many others
- future features need tagging, inheritance, multiple variants, or richer policies
- rename and move operations must preserve semantic links

## Current Evidence

Relevant code inspected during the discussion:

- `src/houmao/project/easy.py`
- `src/houmao/project/overlay.py`
- `src/houmao/agents/definition_parser.py`
- `src/houmao/agents/brain_builder.py`
- `src/houmao/agents/realm_controller/loaders.py`
- `src/houmao/agents/realm_controller/models.py`
- `src/houmao/mailbox/managed.py`

Important observations:

- `SpecialistMetadata` persists path-bearing fields such as `system_prompt_path`, `preset_path`, and `auth_path`, which means storage concerns leak into the logical model.
- `load_role_package()` still assumes `roles/<role>/system-prompt.md`.
- `definition_parser.load_agent_catalog()` reconstructs the object graph from directory conventions.
- `LaunchPlan` is already a clean runtime-oriented model and should remain derived rather than becoming canonical persisted config.
- The mailbox subsystem already demonstrates that SQLite fits Houmao's operational style well for structured state.

## Option A: Everything In SQLite

### Idea

Move almost all persisted config into SQLite, including large text blobs and auth-file payloads.

### Shape

```text
.houmao/catalog.sqlite
```

Everything would be rows or blobs:

- specialists
- roles
- presets
- setups
- skills
- auth profiles
- prompts
- auth file contents
- maybe setup trees and skill trees

### Advantages

- one canonical persistence system
- relationships are explicit
- transactions are simple
- fewer filesystem conventions to maintain

### Problems

- large text and file-tree editing becomes less ergonomic
- external tools still often want files
- setup trees and skill trees fit poorly into plain relational storage
- auth blobs in DB raise security and export/backup concerns
- advanced manual inspection becomes harder
- a DB-only design makes SQLite schema a more rigid public API

### Assessment

Possible, but not the best fit for Houmao's actual asset mix.

## Option B: SQLite Catalog + File Content Store

### Idea

Put semantic relationships and policies into SQLite, but keep large text blobs and tree-shaped assets as files.

### Recommended shape

```text
.houmao/
  catalog.sqlite
  content/
    prompts/
    auth/
    setups/
    skills/
  runtime/
    homes/
    sessions/
```

Meaning:

- `catalog.sqlite` = what the project means
- `content/` = the payload artifacts the project contains
- `runtime/` = derived execution artifacts and live state

### What SQLite owns

- object identity
- naming
- references between objects
- composition
- ordering
- policy configuration
- revision metadata
- relationship integrity

### What files own

- system prompt markdown
- auth JSON/template files
- setup trees
- skill trees
- other large or structured payloads

### What remains derived

- launch plans
- built brain manifests
- session manifests
- env projections
- runtime home files

## Proposed Domain Model

The DB should unify by concept, not by copying today's Python runtime classes directly.

### Recommended conceptual entities

- `Specialist`
- `Role`
- `Preset`
- `SetupProfile`
- `SkillPackage`
- `AuthProfile`
- `MailboxPolicy`
- `ToolBinding`
- `ContentBlobRef`
- `ContentTreeRef`

### Not recommended as canonical stored config

- `LaunchPlan`
- resolved env vars
- runtime home paths
- working directories
- tmux/session details
- session manifest payloads

Those are runtime products, not project config.

## Example Catalog Schema

Illustrative rather than final:

```text
catalog_meta
  schema_version
  created_at
  updated_at

specialists
  id
  name
  role_id
  preset_id
  auth_profile_id
  default_mailbox_policy_id
  created_at
  updated_at

roles
  id
  name
  prompt_blob_id

presets
  id
  role_id
  tool
  setup_profile_id
  launch_policy_json
  mailbox_policy_id
  extra_json

preset_skills
  preset_id
  skill_id
  ordinal

setup_profiles
  id
  tool
  name
  tree_ref_id

skill_packages
  id
  name
  tree_ref_id

auth_profiles
  id
  name
  tool
  auth_kind
  primary_blob_id
  metadata_json

mailbox_policies
  id
  transport
  policy_json

file_blobs
  id
  storage_path
  sha256
  media_type
  size_bytes

file_trees
  id
  root_path
  kind
  digest
```

This gives the DB ownership of relationships, while files remain payload storage.

## Path References vs Blob IDs

Two sub-options came up.

### A. DB stores managed relative paths

Example:

- role points to `content/prompts/researcher.md`
- auth profile points to `content/auth/work.json`

Pros:

- simpler
- easy for humans to inspect
- easier migration from the current tree

Cons:

- paths remain semi-semantic
- renames still need careful handling

### B. DB stores stable blob/tree IDs

Example:

- role points to `prompt_blob_id`
- auth profile points to `primary_blob_id`
- setup and skill objects point to tree refs

Pros:

- stronger identity model
- path renames no longer matter
- better deduplication story

Cons:

- more machinery
- less obvious for manual inspection

### Recommendation

- use blob IDs for single-file artifacts
- use managed tree refs for skill/setup directories
- avoid arbitrary external paths as canonical config

This is a pragmatic middle path.

## Recommended Architecture

### Layered view

```text
1. Intent layer
   project easy specialist / instance

2. Catalog layer
   SQLite-backed semantic graph

3. Content layer
   file-backed blobs and trees

4. Runtime layer
   build/runtime/session models
```

### Service flow

```text
CLI / API
   |
   v
Catalog repository
   |
   +-- read/write semantic relationships in SQLite
   +-- resolve content refs to actual files/trees
   |
   v
Assembler / materializer
   |
   v
BuildRequest / BrainRecipe-like domain projection
   |
   v
runtime launch
```

The main rule:

- DB defines meaning
- files hold payload
- runtime consumes assembled semantics rather than filesystem topology

## Pros

### Compared to the current filesystem-first design

- explicit foreign-keyed relationships
- easier support for many-to-many and future richer graphs
- rename/move no longer depends on preserving nesting conventions
- simpler extension of config schema
- better transactional updates
- less accidental leakage of storage paths into logical concepts

### Compared to an all-SQLite design

- better ergonomics for editing prompts and auth files
- better fit for setup and skill directory trees
- simpler interop with external tools that expect files
- lower risk of large opaque DB blobs becoming hard to manage

## Cons

- two persistence mechanisms instead of one
- requires explicit integrity rules between DB refs and files
- needs orphan detection / garbage collection strategy
- direct SQL mutation by advanced users can still create dangling refs unless strongly constrained
- migration is non-trivial because builders/loaders currently rely on tree conventions

## Main Risks

### 1. Split brain between DB and legacy tree

If SQLite becomes canonical but the old tree still looks canonical, operators will get confused.

Recommendation:

- treat the DB as truth
- treat legacy tree layout as generated projection or compatibility import source only

### 2. Over-coupling DB schema to runtime classes

If the schema copies runtime dataclasses such as `LaunchPlan`, storage becomes brittle.

Recommendation:

- unify on domain nouns
- keep runtime execution models derived

### 3. Weak policy for file lifecycle

You must decide clearly:

- are prompts/auth files mutable in place?
- can two objects share one content blob?
- are setup/skill trees live references or imported managed trees?
- what happens when a referenced file disappears?

Without clear answers, the hybrid model becomes ambiguous.

### 4. Secrets handling

Storing raw auth payloads directly in the main catalog DB is risky.

Recommendation:

- keep auth payload files file-backed
- store only semantic refs and metadata in SQLite
- treat secret-bearing file storage as a separate concern from the semantic catalog

## Migration Strategy

Recommended staged migration:

1. introduce a repository interface above the current filesystem helpers
2. add a SQLite catalog backend as the new source of truth
3. keep file content storage and materialization
4. migrate builders/loaders to consume catalog/domain objects rather than directory traversal
5. optionally keep legacy projection directories only as compatibility outputs

This avoids a risky big-bang rewrite.

## Recommendation

Preferred direction:

- **Use SQLite as the canonical semantic catalog**
- **Keep large text blobs and file trees as files**
- **Stop using directory structure as the source of semantic relationships**
- **Keep runtime models derived rather than canonical**

The clearest target is:

```text
.houmao/catalog.sqlite   -> project meaning
.houmao/content/         -> project payload
.houmao/runtime/         -> derived execution state
```

That gives Houmao a cleaner long-term architecture than either:

- the current tree-first semantic encoding, or
- an everything-is-a-DB-blob design

## Good Next Questions

If this direction is taken, the next design work should answer:

1. Which current filesystem entities become catalog rows vs file refs?
2. What is the stable public SQL surface, if advanced users are expected to edit the DB directly?
3. Are skill/setup trees live references or imported managed content?
4. What compatibility projection, if any, remains under `.houmao/agents/`?
5. How should migration from current overlays work?

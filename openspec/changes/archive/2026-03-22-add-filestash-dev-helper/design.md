## Context

This repository already has one repo-owned local Docker stack under `dockers/email-system/`, so there is precedent for storing development-only service orchestration, helper scripts, documentation, and runtime state inside the repo rather than leaving developers to assemble ad hoc container commands on their hosts.

Filestash is a good functional fit for the first artifact-viewing helper because it can browse Markdown, images, videos, and plain-text outputs through one web UI. The important implementation constraints come from the upstream Filestash behavior:

- the upstream image includes a default config that does not expose the `local` backend by default,
- the `local` backend expects an admin password plus a filesystem path at connect time,
- the browser setup flow hashes the admin password before saving config,
- the `ADMIN_PASSWORD` startup env path writes directly into `auth.admin`, which is not suitable for a deterministic low-friction local helper when supplied as plaintext,
- the container runs as a non-root user and needs a writable `/app/data/state` mount,
- the connect page can auto-enter a middleware flow when there is exactly one configured middleware-backed connection.

Those details mean this change is not just “add a compose file.” The helper needs a repo-owned startup contract that prepares writable state correctly and seeds Filestash with a deterministic local-only configuration.

## Goals / Non-Goals

**Goals:**
- Provide a repo-owned Filestash helper under `dockers/dev-helpers/filestash/`.
- Let a developer browse this repository's files and generated artifacts through a local browser UI without manually configuring Filestash after startup.
- Keep the helper development-only, loopback-only, and low-friction.
- Make the helper deterministic to reset and debug from repository context.

**Non-Goals:**
- Defining the full future architecture for every dev helper the repo may add later.
- Turning Filestash into a production deployment or multi-user service.
- Supporting repository editing or write-through file management from the browser as part of this first helper.
- Solving live log streaming or log tailing beyond ordinary file browsing.

## Decisions

### Decision: Scope this change to one repo-owned Filestash helper, not a generalized helper framework

This change will create `dockers/dev-helpers/filestash/` as the first helper-specific subtree and will not attempt to define a cross-helper abstraction beyond the conventions needed for this service.

Why this approach:
- The user request is concrete: add the first Filestash helper.
- A premature generalized helper framework would add naming and structure debates before there is a second helper to validate those abstractions.
- The repo already tolerates helper-specific stack directories such as `dockers/email-system/`.

Alternatives considered:
- Define a broad multi-helper framework first.
  Rejected because it increases scope without improving the first Filestash outcome.

### Decision: Use the upstream `machines/filestash:latest` image as a documented prerequisite, embed it directly in the repo-owned compose stack, and keep normal startup pull-free

The helper will use the upstream published Filestash image embedded directly in the repo-owned compose stack. Normal repo-owned startup will treat that image as a host prerequisite rather than pulling during every bring-up.

Why this approach:
- It matches the existing local-stack convention used by `dockers/email-system/`, where normal startup uses host-local images rather than performing registry fetches.
- It keeps the helper startup deterministic and avoids hiding network activity inside `up.sh`.
- The repository can still document the explicit manual `docker pull` step when the image is not already present locally.

Alternatives considered:
- Always pull on startup.
  Rejected because it makes local bring-up slower, less deterministic, and less aligned with the repo's current Docker-stack workflow.
- Build Filestash from the source reference in `extern/orphan/filestash/`.
  Rejected for this first step because the helper goal is to use a readily available upstream image, not to adopt Filestash as a maintained in-repo build target.

### Decision: Mount the repository read-only at `/repo` and persist writable runtime state under a helper-owned `.data/` bind mount

The helper will bind-mount the repository root into the container as a read-only filesystem at `/repo`. Filestash runtime state will live under `dockers/dev-helpers/filestash/.data/` and will be bind-mounted to `/app/data/state`.

The repo-owned startup wrapper will prepare `.data/` with permissions that are writable by the non-root Filestash container user before starting the stack.

Why this approach:
- A read-only repo mount matches the primary user intent: view repository files and artifacts.
- Keeping mutable Filestash state under a helper-owned `.data/` path mirrors the existing local Docker stack convention and gives operators an obvious reset target.
- Preparing permissions in the startup wrapper avoids fragile first-boot failures caused by the container's non-root runtime user.

Alternatives considered:
- Use a named Docker volume for state.
  Rejected because repo-owned `.data/` is easier to inspect, document, and reset from repository context.
- Mount the repository read-write.
  Rejected because this helper is for artifact browsing, not browser-based repository mutation.

### Decision: Seed a repo-owned Filestash config into runtime state instead of relying on `ADMIN_PASSWORD`

The helper will keep an authoritative repo-owned seed config and copy it into `.data/config/config.json` before startup. That seed config will include the dev-only admin credential material and the connection/auth configuration needed for the repo browser flow.

The helper will not rely on Filestash's `ADMIN_PASSWORD` startup env path for first-time bootstrap.

Why this approach:
- The upstream browser setup flow hashes admin passwords before saving configuration, while the startup env path does not provide the same deterministic repo-owned result for a plaintext local password.
- A repo-owned seed config makes startup reproducible and avoids manual browser-side setup work.
- Copying the repo-owned config into runtime state before startup keeps the runtime config writable for Filestash internals while still letting the repo define the intended baseline.

Alternatives considered:
- Use `ADMIN_PASSWORD=admin` during startup.
  Rejected because the resulting config state is not suitable for the intended local login flow.
- Require each developer to complete Filestash admin setup manually in the browser.
  Rejected because it adds friction and makes the helper non-repeatable.
- Seed only on first boot and let runtime config drift later.
  Rejected because the helper should stay repo-owned and deterministic rather than depending on sticky UI mutations.

### Decision: Expose a single `Repo` entry path by mapping admin-password auth into the local backend with fixed `/repo`

The helper will use Filestash configuration to expose one repository browsing entry path instead of exposing the raw local-backend login form directly. The operator-facing flow will ask only for the dev helper's admin password and then land in the mounted repository root without requiring the user to type `/repo`.

Why this approach:
- It gives the “easy way to view all files in this repo” outcome the user asked for.
- It removes path-entry mistakes and hides unnecessary upstream Filestash setup complexity.
- With a single middleware-backed connection, the browser flow can enter the intended auth path directly instead of presenting a connection chooser.

Alternatives considered:
- Expose the upstream `local` backend login form directly and require the user to enter `/repo`.
  Rejected because it turns a fixed helper into a manual setup exercise.
- Create multiple predefined connections for different repo subtrees.
  Rejected because the first helper only needs one full-repository browsing path.

### Decision: Keep the helper local-only and explicitly development-scoped

The helper will bind to `127.0.0.1` on a non-privileged host port, use development-only low-friction credentials, and document itself as a local artifact-browsing convenience rather than a hardened file service.

Why this approach:
- The helper is intended to support one local developer workstation.
- Low-friction defaults are appropriate only when paired with loopback-only exposure and development-only documentation.

Alternatives considered:
- Expose the helper on all interfaces or add production-style hardening.
  Rejected because this would push the change into a different security and operational class than the user requested.

## Risks / Trade-offs

- [Upstream Filestash `latest` may drift] → Mitigation: document the upstream image as an explicit prerequisite and update the repo-owned compose file deliberately when the pinned upstream reference should change.
- [A fixed low-friction password is weak if the service is exposed broadly] → Mitigation: bind the helper to loopback only and document the helper as development-only.
- [Read-only repo mounts prevent browser-side edits or uploads] → Mitigation: accept this limitation because the helper is for viewing artifacts, not editing them.
- [Repo-owned config synchronization can overwrite local UI tweaks] → Mitigation: make the repo-owned config authoritative by design and document `.data/` reset behavior instead of treating UI tweaks as durable local configuration.
- [Filestash runtime state permissions can break first boot] → Mitigation: require the startup wrapper to create and permission the `.data/` subtree before running compose.

## Migration Plan

1. Add the Filestash helper subtree under `dockers/dev-helpers/filestash/` with compose, startup helpers, seed config, and docs.
2. Add or update ignore rules so helper runtime state under `.data/` is not tracked.
3. Document the upstream image prerequisite and the local startup, verify, and reset workflow.
4. Verify that the helper starts from repository context and lands the operator in the mounted repo browser flow.

Rollback is straightforward: remove the helper subtree and ignore-rule changes, then stop and delete the helper's local runtime state directory.

## Open Questions

- Whether later helpers under `dockers/dev-helpers/` should standardize on one shared wrapper convention after a second helper exists.
- Whether a later change should pin Filestash to a specific tag or digest once the initial helper workflow is stable.

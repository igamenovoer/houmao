## Context

The original proposal treated `project easy instance launch --env-set` as something the runtime should persist so later relaunch could replay it. That turns out to be the wrong ownership boundary.

There are actually two different kinds of env input:

1. one-off env attached to one concrete launch attempt or one live session
2. durable env that belongs to the reusable specialist and should survive relaunch because it is part of the specialist's launch semantics

If the runtime persists one-off instance-launch env in relaunch authority, the system quietly converts ephemeral operator input into durable specialist behavior. That is surprising and makes it harder to understand why a later relaunch still has env that was only meant for one run.

The cleaner split is:

- instance-launch extra env is one-off and live-session-only
- specialist-owned env records are durable and survive relaunch because they are part of the specialist launch config

That durable channel must stay separate from credential env. Credential env is still the auth-bundle-owned path for tool authentication or routing env. Specialist env records are a different class of data and should not be folded into `tools/<tool>/auth/<name>/env/vars.env`.

## Goals / Non-Goals

**Goals:**

- Add first-class one-off extra env to `project easy instance launch`.
- Add first-class persistent specialist-owned env records that survive relaunch.
- Keep persistent specialist env records separate from credential envs in both semantics and storage shape.
- Make relaunch behavior unsurprising:
  - specialist env survives
  - one-off instance-launch env does not
- Keep the compatibility projection honest so the projected preset still reflects the durable specialist launch semantics.

**Non-Goals:**

- Persisting one-off `instance launch --env-set` in session-manifest relaunch authority.
- Turning auth bundles into a catch-all storage path for non-credential launch env.
- Expanding the public low-level `houmao-mgr agents launch` CLI in the same change.
- Designing a broad mutable specialist-edit workflow beyond the env additions needed for this change.

## Decisions

### Decision: Split env input into durable specialist env and one-off instance env

The design will support two separate env channels:

- persistent specialist env records
- one-off `project easy instance launch --env-set`

They differ by persistence and ownership:

- specialist env records are reusable specialist config and survive relaunch
- one-off instance env belongs only to the currently started live session and is dropped by relaunch

Rationale:

- The user intent differs sharply between “always launch this specialist with X” and “launch this run with X once.”
- Relaunch should preserve reusable launch semantics, not accidental one-off operator input.

Alternative considered:

- Persist all instance-launch env in relaunch authority.
  Rejected because it silently upgrades one-off input into durable specialist behavior.

### Decision: Persistent env records live in specialist launch config as `launch.env_records`

Durable env records will be part of specialist launch config and represented in the projected preset under a dedicated `launch.env_records` section.

`launch.env_records` will be a mapping of env name to literal string value. This is distinct from:

- `launch.overrides`, which controls CLI args and typed tool params
- auth-bundle env files, which remain credential-owned input

Rationale:

- These values are launch semantics, so they belong with other launch-owned preset data.
- Keeping them in projected preset YAML lets the compatibility tree remain an honest view of durable specialist launch semantics.
- Using a dedicated section avoids smuggling them through auth bundles or `extra`.

Alternative considered:

- Store durable env only in the project catalog and inject it through a project-only side path.
  Rejected because it would make the compatibility projection lie about the effective durable launch semantics.

### Decision: Specialist env records are literal key/value records, not inherited bindings

Persistent specialist env records will use literal `NAME=value` semantics only. They will not support the inherited `NAME` form.

One-off instance launch `--env-set` may still use Docker-style `NAME=value` or `NAME`.

Rationale:

- Durable specialist config should not depend on whichever shell happens to invoke a later relaunch.
- Literal specialist records make relaunch deterministic.
- Inherited env is useful for ephemeral operator convenience, not for reusable specialist semantics.

Alternative considered:

- Support inherited specialist env records.
  Rejected because durable specialist semantics would still depend on ambient shell state.

### Decision: Specialist env records stay separate from credential env by validation and precedence

The system will treat credential env and specialist env records as separate channels.

Validation:

- specialist `--env-set` names must not collide with Houmao-owned reserved env names
- specialist `--env-set` names must not collide with the selected tool adapter's auth-env allowlist

Precedence:

1. calling process env
2. auth-bundle env allowlist overlay
3. specialist `launch.env_records`
4. one-off instance-launch env overlay
5. runtime-owned env publication

Rationale:

- This makes “do not mix them with credential envs” concrete instead of aspirational.
- Auth bundles remain the path for tool auth and auth-adjacent routing env.
- Specialist env records can still override normal inherited shell env without pretending to be credentials.

Alternative considered:

- Allow specialist env records to reuse auth-env names.
  Rejected because it creates two competing sources of truth for the same credential-owned env.

### Decision: One-off instance-launch env is applied to the live session only and is not persisted for relaunch

`project easy instance launch --env-set` will remain Docker-style:

- `NAME=value`
- `NAME`

At launch time:

- inherited names resolve from the invoking process environment
- the resolved values are added to the in-memory effective launch plan for the current live session

The runtime will not persist those one-off values in:

- specialist config
- built brain manifests
- session-manifest relaunch authority

As a result, later relaunch rebuild drops them automatically.

Rationale:

- This preserves the intended “one-off use” behavior.
- Headless follow-up turns in the same live session still see the env because they use the controller's live launch plan.
- Relaunch starts from durable inputs only.

Alternative considered:

- Make one-off env launch-only for the first provider process and not for later turns in the same live session.
  Rejected because that would make one-off env nearly useless for tmux-backed headless sessions that execute later turns through the live controller.

### Decision: `project easy specialist create` gets initial `--env-set` input, while richer CRUD can follow later

This change will add repeatable `--env-set NAME=value` to `project easy specialist create` and expose those records in specialist inspection.

A richer `specialist env set|remove|list` surface can follow later if needed, but it is not required to establish the semantic split in this change.

Rationale:

- The repo currently has no general specialist update command.
- Adding initial create-time support plus inspection is enough to define the durable config model.
- This keeps scope focused on the env-semantics correction.

Alternative considered:

- Introduce a full specialist env CRUD command family in the same change.
  Rejected because it broadens operator-surface work beyond the core semantic fix.

## Risks / Trade-offs

- [Risk] Create-time-only specialist env input may feel incomplete without later edit commands.
  → Mitigation: expose env records clearly in specialist get and treat richer CRUD as a follow-up if operator demand appears.

- [Risk] Operators may still put secrets into specialist env records even though that channel is meant for non-credential launch config.
  → Mitigation: document that credential-bearing env belongs in auth bundles, and reject names that collide with adapter auth-env allowlists.

- [Risk] Using projected preset YAML for durable env records expands preset schema.
  → Mitigation: keep the new shape narrow and launch-owned under `launch.env_records`.

## Migration Plan

- No migration is required for existing specialists or existing sessions.
- Existing specialists continue to work without `launch.env_records`.
- Existing `project easy instance launch` calls continue to work without `--env-set`.
- Relaunch behavior for existing sessions is unchanged.
- New specialists that opt into `launch.env_records` will survive relaunch because rebuild reads the durable specialist launch config.

## Open Questions

- Whether the project eventually wants a dedicated `project easy specialist env ...` CRUD surface remains open and can be deferred until after the semantic split is implemented.

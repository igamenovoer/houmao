# Feature Request: Move CAO Compatibility Behind `houmao-srv-ctrl cao ...`

## Status
Proposed

## Summary
Reshape `houmao-srv-ctrl` so CAO-compatible behavior lives under an explicit compatibility namespace:

- `houmao-srv-ctrl cao <cao-args>`

and reserve top-level `houmao-srv-ctrl <subcommand>` for Houmao-owned semantics.

The goal is to stop treating the current CAO CLI shape as the long-term public contract for `houmao-srv-ctrl`. CAO compatibility is useful for short-term migration, but the project direction is to become a Houmao-native framework rather than a permanently CAO-shaped wrapper.

## Why
Today `houmao-srv-ctrl` still looks like a CAO-style CLI even when behavior is already diverging.

That creates a strategic problem:

- users see a top-level command shape that implies long-term CAO parity,
- Houmao-native behavior has to hide inside CAO-shaped verbs and flags,
- new native concepts risk being forced into awkward CAO vocabulary,
- compatibility pressure leaks into CLI design even when the underlying lifecycle is no longer CAO-owned.

The recent native headless work makes this mismatch obvious:

- `houmao-srv-ctrl launch --headless` is no longer a CAO-delegated launch,
- it targets a Houmao-native server API,
- it resolves Houmao brain recipes and builds a native launch request,
- but it still appears under a top-level verb that looks like a CAO passthrough surface.

If Houmao is expected to grow beyond CAO rather than remain a thin migration wrapper forever, the CLI should make that boundary explicit now.

## Desired Command Boundary
The canonical separation should be:

- `houmao-srv-ctrl cao <cao-args>`:
  explicit CAO-compatibility namespace for delegated or compatibility-preserving operations
- `houmao-srv-ctrl <houmao-subcommand> ...`:
  Houmao-native command tree whose semantics are defined by Houmao, not by CAO

Examples of the intended distinction:

- `houmao-srv-ctrl cao launch ...`
- `houmao-srv-ctrl cao install ...`
- `houmao-srv-ctrl launch ...`
- `houmao-srv-ctrl install ...`
- `houmao-srv-ctrl agents ...`
- `houmao-srv-ctrl server ...`

The exact Houmao-native top-level tree can be designed later, but the compatibility boundary should be explicit and first-class.

## Requested Scope
1. Introduce a `cao` subcommand namespace that owns raw CAO-compatible passthrough behavior.
2. Redefine top-level `houmao-srv-ctrl` subcommands as Houmao-owned commands whose UX is allowed to diverge from CAO.
3. Treat top-level command names, flags, defaults, and output formats as Houmao contracts rather than inherited CAO contracts.
4. Make new native workflows land under Houmao-owned subcommands instead of extending the CAO-shaped top-level surface indefinitely.
5. Provide a migration path for users who currently invoke CAO-shaped top-level verbs directly through `houmao-srv-ctrl`.
6. Document clearly that CAO compatibility is transitional and scoped, not the long-term CLI architecture.

## Acceptance Criteria
1. A user can invoke raw CAO-compatible behavior through `houmao-srv-ctrl cao <cao-args>`.
2. Houmao-native commands no longer need to preserve CAO flag shape or CAO argument semantics by default.
3. New native features can introduce their own subcommands and request models without being constrained by CAO vocabulary.
4. Docs describe the CLI boundary explicitly:
   - `cao` namespace is compatibility-oriented
   - top-level namespace is Houmao-owned
5. Compatibility shims or deprecation messaging exist for important existing top-level CAO-shaped entrypoints.
6. Tests cover at least:
   - one delegated CAO passthrough under `houmao-srv-ctrl cao ...`
   - one Houmao-native command whose semantics intentionally differ from CAO

## Non-Goals
- No requirement to remove CAO compatibility immediately.
- No requirement to decide the full final Houmao CLI information architecture in the same change.
- No requirement to rename every current command in one step if a staged migration is cleaner.
- No requirement to remove the installed `cao` dependency in the short term.

## Suggested Migration Shape
One reasonable staged path is:

1. Add `houmao-srv-ctrl cao ...` as the explicit compatibility namespace.
2. Keep current top-level CAO-shaped commands temporarily as compatibility shims.
3. Introduce Houmao-native top-level commands and documentation as the preferred interface.
4. Move future native features only into the Houmao-owned surface.
5. Deprecate or narrow old top-level CAO-shaped shims after users have a documented migration path.

## Strategic Outcome
This change would clarify the intended product direction:

- CAO compatibility remains available where it helps migration,
- but it stops defining the outer shape of `houmao-srv-ctrl`,
- which lets Houmao evolve into its own framework instead of inheriting CAO’s CLI model indefinitely.

## Suggested Follow-Up
- Create an OpenSpec change for the `houmao-srv-ctrl` command-boundary redesign.
- Audit current `houmao-srv-ctrl` subcommands and classify each one as:
  - CAO compatibility
  - Houmao-native
  - temporary shim
- Decide which existing top-level commands should remain Houmao-native, which should move under `cao`, and which should become aliases during migration.
- Update migration and reference docs so users understand that `houmao-srv-ctrl` is no longer defined primarily as a CAO-shaped wrapper.

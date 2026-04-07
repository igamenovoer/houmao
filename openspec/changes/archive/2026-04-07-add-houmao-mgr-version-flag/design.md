## Context

`houmao-mgr` already has a single canonical packaged version source through `houmao.version.get_version()`, but the root Click command does not expose that information to operators. In practice, this makes it harder to diagnose stale host installs, because the first-level CLI surface cannot answer the simple question "which Houmao package is this binary running?".

The change is small and localized to the root CLI surface plus documentation and tests. It does not require any new dependency, data-model change, or migration.

## Goals / Non-Goals

**Goals:**

- Expose a standard root `houmao-mgr --version` option.
- Keep version reporting tied to the packaged version already resolved by Houmao.
- Make the behavior obvious in help output and documented in the CLI reference.
- Cover the behavior with root CLI tests.

**Non-Goals:**

- Adding version flags to every other Houmao executable in the same change.
- Introducing JSON or rich rendering semantics for `--version`.
- Changing package version resolution semantics beyond the existing helper.

## Decisions

### Decision: Root `houmao-mgr` owns the new option

The version flag should live on the root `houmao-mgr` command group rather than on a subcommand or separate diagnostic command. This matches common operator expectations and keeps stale-install diagnosis available before any other command resolution.

Alternative considered:

- Add a dedicated `houmao-mgr admin version` command. Rejected because it adds unnecessary command depth for a standard CLI primitive and does not help users who naturally try `--version`.

### Decision: Reuse the existing Houmao version helper

The CLI should source its displayed version from `houmao.version.get_version()` rather than introducing another direct `importlib.metadata` call in the command module. That keeps one package-version resolution path and preserves the current fallback behavior when package metadata is unavailable.

Alternative considered:

- Use Click's package-name-based version lookup directly in the root command. Rejected because the repo already has a canonical helper and duplicating lookup behavior would create avoidable drift.

### Decision: `--version` remains plain standard CLI output

`houmao-mgr --version` should print a plain version string and exit successfully without involving `--print-plain`, `--print-json`, or `--print-fancy`. The version option is a root-level command-discovery primitive rather than ordinary domain output, so standard CLI behavior is the better contract.

Alternative considered:

- Make `--version` honor the print-style output framework. Rejected because it adds complexity and ambiguity for low operator value.

## Risks / Trade-offs

- [Root option ordering interactions with existing output flags] → Mitigation: keep the behavior narrow and cover root help plus direct `--version` invocation in unit tests.
- [Future desire for version parity across all Houmao executables] → Mitigation: keep this change scoped to `houmao-mgr` and treat broader entrypoint parity as a follow-up change if needed.
- [Fallback version string may expose `0+unknown` in unusual environments] → Mitigation: reuse the existing helper intentionally so the CLI matches Houmao's current package-version contract.

## Migration Plan

No data migration is required.

Rollout is:

1. add the root option,
2. update CLI reference docs,
3. verify with unit tests,
4. publish and reinstall the packaged tool where needed.

Rollback is straightforward: remove the root version option wiring and the related docs/tests.

## Open Questions

None for this scoped change.

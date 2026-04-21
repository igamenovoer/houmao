## ADDED Requirements

### Requirement: Managed local fresh launch can rebuild current launch inputs onto a preserved home

When a local managed launch explicitly requests reused-home mode, the runtime SHALL resolve one compatible preserved managed home for the current managed identity from local lifecycle metadata before provider startup.

A preserved home SHALL be considered compatible only when all of the following are true:

- it belongs to the same managed identity selected for the current launch,
- it was recorded under the same local runtime root,
- it belongs to the same tool family as the current launch,
- its preserved home path still exists on disk.

When compatible reused-home launch succeeds, the runtime SHALL rebuild the current launch's Houmao-managed setup projection, auth projection, skill projection, system-skill installation, launch helper, and build manifest onto that preserved home instead of allocating a new home id.

The runtime SHALL preserve provider-owned or operator-owned files outside the paths that the rebuild explicitly rewrites.

A reused-home fresh launch SHALL create new live session authority for the new launch. It SHALL NOT treat the request as stopped-session revival or active relaunch.

When no compatible preserved home exists, the runtime SHALL fail explicitly and SHALL NOT silently fall back to allocating a brand-new home.

#### Scenario: Stopped predecessor home is rebuilt for a fresh launch
- **WHEN** stopped local managed agent `reviewer` preserves runtime home `/runtime/homes/codex-home-1`
- **AND WHEN** a new local managed launch resolves the same managed identity `reviewer`
- **AND WHEN** that launch explicitly requests reused-home mode
- **THEN** the runtime rebuilds current Houmao-managed launch material onto `/runtime/homes/codex-home-1`
- **AND THEN** the runtime does not allocate a new home id for that launch
- **AND THEN** the runtime creates fresh live session authority for the new launch

#### Scenario: Missing compatible preserved home fails without fresh-home fallback
- **WHEN** a local managed launch explicitly requests reused-home mode
- **AND WHEN** no compatible preserved home can be resolved for the selected managed identity
- **THEN** the runtime fails the launch clearly
- **AND THEN** it does not silently allocate a brand-new runtime home

### Requirement: Reused-home fresh launch remains non-destructive and relaunch-distinct

When reused-home launch is requested together with managed force takeover against a live predecessor, the runtime SHALL support only non-destructive `keep-stale` behavior for the preserved home.

The runtime SHALL reject any attempt to combine reused-home launch with destructive `clean` semantics because that would discard the preserved home contents the operator asked to keep.

Reused-home fresh launch SHALL NOT consume stored relaunch chat-session policy or provider-native chat continuation selectors automatically.

Provider-local history that remains in the preserved home MAY stay available to provider-native continuation surfaces after startup, but the runtime SHALL still treat startup as a fresh launch rather than a relaunch.

#### Scenario: Live predecessor stands down before keep-stale reused-home launch
- **WHEN** a fresh live predecessor already owns managed identity `reviewer`
- **AND WHEN** the replacement launch explicitly requests reused-home mode
- **AND WHEN** the replacement launch also requests force mode `keep-stale`
- **THEN** the runtime makes the predecessor stand down before replacement publication
- **AND THEN** the replacement launch rebuilds onto the preserved home instead of deleting it

#### Scenario: Reused-home launch rejects destructive clean mode
- **WHEN** a local managed launch explicitly requests reused-home mode
- **AND WHEN** that same launch also requests force mode `clean`
- **THEN** the runtime rejects the request before destructive cleanup begins
- **AND THEN** the preserved home contents remain untouched

#### Scenario: Reused-home launch preserves relaunch-only chat policy boundaries
- **WHEN** a local managed launch explicitly requests reused-home mode
- **AND WHEN** the selected launch profile stores relaunch chat-session mode `tool_last_or_new`
- **THEN** the runtime starts provider launch without automatically applying relaunch chat continuation arguments
- **AND THEN** preserved provider-local history remains available only through the preserved home's ordinary provider-native surfaces

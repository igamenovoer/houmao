## 1. Local Authority Health Model

- [x] 1.1 Add one shared tmux-authority probe for local tmux-backed managed sessions that distinguishes healthy authority, missing-primary degraded authority, and missing-session stale authority.
- [x] 1.2 Thread the derived local authority health result through the local managed-agent recovery path without adding new persisted shared lifecycle states.

## 2. Runtime Recovery Paths

- [x] 2.1 Update tmux-backed runtime stop behavior so degraded or stale active local authority can still preserve stopped-session continuity metadata when manifest-owned relaunch authority exists.
- [x] 2.2 Update tmux-backed relaunch behavior so an existing tmux session with missing primary surface rebuilds the contractual primary surface instead of failing immediately.
- [x] 2.3 Update stale-active relaunch handling so a missing tmux session can transition through stopped-session revival semantics when preserved relaunch metadata remains available.
- [x] 2.4 During `degraded_missing_primary` relaunch, kill any surviving auxiliary gateway window in the same tmux session before rebuilding the contractual primary surface, then reprovision the gateway through the existing post-startup gateway launch path.
- [x] 2.5 Implement the retire-without-continuity branch for `stale_missing_session` stop and the explicit-failure branch for `stale_missing_session` relaunch when preserved manifest-owned relaunch authority is no longer readable, so stop response messaging identifies retirement-without-continuity and relaunch error messaging points operators to fresh `agents launch`.

## 3. CLI And Cleanup Integration

- [x] 3.1 Update local managed-agent target resolution and registry-backed stop/relaunch dispatch so degraded or stale active records use the supported recovery branches instead of collapsing into a generic unusable-target error.
- [x] 3.2 Update `houmao-mgr agents cleanup session --purge-registry` so explicit cleanup can retire or purge broken local active authority when the tmux-authority probe shows no usable primary surface.
- [x] 3.3 Keep ordinary CLI failure rendering clean and contextual for commands that still fail after recovery was attempted, without leaking Python tracebacks.

## 4. Regression Coverage

- [x] 4.1 Add runtime and unit coverage for active local stop against gateway-only tmux remnants and against stale active records whose tmux session is already gone.
- [x] 4.2 Add relaunch coverage for degraded active recovery, stale-active revival, and the unchanged stopped-session revival path.
- [x] 4.3 Add cleanup coverage showing `agents cleanup session --purge-registry` can retire broken active local authority while conservative cleanup still blocks healthy live sessions.
- [x] 4.4 Add coverage for stale-active stop retirement without preserved manifest authority, stale-active relaunch failure when manifest authority is unavailable, and the gateway-window kill-then-rebuild step during degraded relaunch.

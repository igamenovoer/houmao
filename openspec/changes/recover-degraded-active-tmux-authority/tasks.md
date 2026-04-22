## 1. Local Authority Health Model

- [ ] 1.1 Add one shared tmux-authority probe for local tmux-backed managed sessions that distinguishes healthy authority, missing-primary degraded authority, and missing-session stale authority.
- [ ] 1.2 Thread the derived local authority health result through the local managed-agent recovery path without adding new persisted shared lifecycle states.

## 2. Runtime Recovery Paths

- [ ] 2.1 Update tmux-backed runtime stop behavior so degraded or stale active local authority can still preserve stopped-session continuity metadata when manifest-owned relaunch authority exists.
- [ ] 2.2 Update tmux-backed relaunch behavior so an existing tmux session with missing primary surface rebuilds the contractual primary surface instead of failing immediately.
- [ ] 2.3 Update stale-active relaunch handling so a missing tmux session can transition through stopped-session revival semantics when preserved relaunch metadata remains available.

## 3. CLI And Cleanup Integration

- [ ] 3.1 Update local managed-agent target resolution and registry-backed stop/relaunch dispatch so degraded or stale active records use the supported recovery branches instead of collapsing into a generic unusable-target error.
- [ ] 3.2 Update `houmao-mgr agents cleanup session --purge-registry` so explicit cleanup can retire or purge broken local active authority when the tmux-authority probe shows no usable primary surface.
- [ ] 3.3 Keep ordinary CLI failure rendering clean and contextual for commands that still fail after recovery was attempted, without leaking Python tracebacks.

## 4. Regression Coverage

- [ ] 4.1 Add runtime and unit coverage for active local stop against gateway-only tmux remnants and against stale active records whose tmux session is already gone.
- [ ] 4.2 Add relaunch coverage for degraded active recovery, stale-active revival, and the unchanged stopped-session revival path.
- [ ] 4.3 Add cleanup coverage showing `agents cleanup session --purge-registry` can retire broken active local authority while conservative cleanup still blocks healthy live sessions.

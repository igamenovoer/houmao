## 1. Runtime Reuse-Home Plumbing

- [x] 1.1 Add one runtime/home-resolution path that can recover a compatible preserved home for a managed identity from local live or stopped lifecycle metadata.
- [x] 1.2 Plumb explicit reused-home launch intent through the managed local launch pipeline so fresh launch can rebuild onto an existing home id without invoking relaunch or stopped-session revival.
- [x] 1.3 Reject incompatible preserved-home requests early, including missing preserved homes, runtime-root or tool mismatches, and any `--reuse-home` request combined with destructive `clean` behavior.

## 2. CLI Surfaces

- [x] 2.1 Add `--reuse-home` to `houmao-mgr agents launch` and wire it through both direct `--agents` and explicit `--launch-profile` flows.
- [x] 2.2 Add `--reuse-home` to `houmao-mgr project easy instance launch` and forward it through both specialist-backed and easy-profile-backed delegated launch flows.
- [x] 2.3 Make launch-time validation and operator-facing output clearly distinguish reuse-home fresh launch from relaunch, including the live-owner conflict and `--force clean` rejection cases.

## 3. Verification

- [x] 3.1 Add unit coverage for managed local launch that reuses a stopped preserved home and rebuilds current launch inputs onto the same home id.
- [x] 3.2 Add CLI coverage for `agents launch --reuse-home` and `project easy instance launch --reuse-home`, including missing-home failures and live-owner conflict behavior.
- [x] 3.3 Add regression coverage showing that reuse-home launch does not consume relaunch chat-session policy automatically and rejects `--reuse-home --force clean`.

## 4. Documentation

- [x] 4.1 Update launch lifecycle and run-phase documentation to explain the new reuse-home fresh-launch mode and how it differs from relaunch and stopped-session revival.
- [x] 4.2 Update launch-profile and easy-launch guidance to explain what reuse-home preserves, what it refreshes, and why destructive clean mode is incompatible with this feature.

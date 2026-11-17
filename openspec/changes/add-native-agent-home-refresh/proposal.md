# Proposal

## Why

Operators, external tools, and agents can update skills and MCP materials outside Houmao, and an agent body can apply those updates automatically. Houmao needs to expose the native home, observe whether those common resources are current, and request native refresh when needed, independently of installation and manifest-backed relaunch. This addresses [issue #82](https://github.com/igamenovoer/houmao/issues/82).

## What Changes

- Define `common-plugin` as skills and MCP, and `native-special-plugin` as agent-specific extensions outside those common forms. Standardize inspection and freshness reporting for common-plugin only. Users inspect native-special-plugin state through native facilities; this change adds no common API for that inventory or its freshness.
- Expose the authoritative native home of one active managed agent through scoped `home` commands and a typed read interface, without exposing credentials or guessing from the caller's operating-system home.
- Add scoped `refresh --check` and typed read-only observation of common-plugin capabilities, effective inventory, and per-resource `current`, `pending`, or `unknown` freshness. Report evidence, observation scope, native boundaries, and health separately; incomplete evidence cannot establish that everything is updated.
- Support native automatic refresh independently of Houmao triggers. A manual refresh first observes common-plugin state and becomes a verified no-op when that scope is already current. Otherwise use qualified automatic discovery or a native reload, then report what is confirmed and what remains pending or unknown.
- Permit native refresh to reload native-special-plugin content or other native configuration as its normal side effect. The operation need not apply atomically or affect common-plugin exclusively. Pending native-special-plugin changes do not invalidate current skills/MCP unless they impair those resources or native readiness.
- Refresh never restarts the harness, replaces the bound conversation, or falls back to relaunch. Report `restart_required` for common resources known to require restart, preserving any partial effects. Keep `relaunch` as the separate manifest-backed operation with its existing generation and conversation-selection rules; add no force-restart option.
- Keep refresh independent of launch-material construction. It does not resolve edited Houmao launch profiles, rebuild homes, install packages, regenerate system prompts, or restore externally edited files. Separate DSH launch-time materialization from ordinary ACP consumption so external edits survive later invocations.
- Make DSH headless discovery and Web refresh the primary implementation and acceptance targets. Investigate Kimi Code, Codex, and Claude Code on a best-effort basis and implement each verified path available through maintained control surfaces. Report their limitations per resource without blocking DSH acceptance. Pi remains postponed.
- Reuse gateway admission and native execution guards for Houmao-initiated live reload, while allowing agent-native watchers and automatic discovery to operate independently. Document and test external writers, automatic updates, no-op decisions, broad and partial native reload, no-restart enforcement, and failures without rollback claims.

## Capabilities

### New Capabilities

- `native-agent-home-refresh`: authoritative native-home inspection, common-plugin freshness observation, automatic/native refresh with permitted broader effects, and the boundary from manifest-backed relaunch.

### Modified Capabilities

- `houmao-mgr-agents-scope-cli`: expose `home`, `refresh --check`, and `refresh` in single/self scope with structured common-plugin state, no-op/partial outcomes, and no restart flags.
- `dsh-headless-control`: distinguish ACP protocol capabilities from common-plugin observation and next-invocation discovery without inventing an ACP reload request or regenerating native home material.
- `passive-server-gateway-proxy`: proxy native-home and common-plugin state reads and native refresh, preserving the owning gateway's evidence, boundaries, and outcomes.

## Impact

The implementation touches runtime/backend observation and refresh contracts, native-home resolution, DSH preparation and companions, gateway admission/models/client, scoped manager commands, passive-server proxy routes, and qualification tests. Existing control and fixture infrastructure supplies target identity, native maintenance, session continuity, and isolated tmux testing. The [native preflight evidence](../../../context/plans/native-agent-home-refresh/preflight.md) and [reusable probes](../../../scripts/qualification/native_refresh/README.md) guide version-specific qualification; they do not constitute completed implementation.

Planning artifacts belong under `openspec/changes/add-native-agent-home-refresh/`. Future implementation belongs under `src/houmao/` (`distro`), automated coverage under `tests/` (`CI`), and durable qualification tooling under `scripts/qualification/` (`utility`). Reference and workflow documentation will explain the native-home editing sequence and the distinction from relaunch.

This change adds no skill/MCP/harness installer API, Houmao-owned package catalog, generic filesystem watcher, or desired-revision database. It does not define a common native-special-plugin management/query API or extend Houmao gateway-plugin management. Native bodies retain their own automatic refresh behavior. Pi, execution ownership, remote authentication, and Python gateway-plugin hot replacement remain outside this change.

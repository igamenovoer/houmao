## Why

The Stalwart-backed mailbox transport and the gateway mailbox facade are now implemented, but the reference docs still make first-time readers piece the story together from filesystem-first pages, low-level contract docs, and scattered runtime references. That makes it too easy for operators to miss the intended path for a Stalwart-backed session and too hard for developers to see where Houmao ends, where the gateway takes over, and where Stalwart is the authority.

We need a focused documentation update now because the implementation has already crossed the line from "future transport" to current behavior. The repo should present one clear reader path for enabling a Stalwart-backed mailbox session, one clear explanation of the gateway `/v1/mail/*` facade, and one clear filesystem story for secret-free manifests versus runtime-owned credential material.

## What Changes

- Add an operator-facing mailbox guide for Stalwart-backed sessions that explains prerequisites, first-session bring-up, direct `mail` commands, and the optional gateway mailbox facade.
- Add a gateway operations page that explains the shared `/v1/mail/*` facade, adapter selection from `attach.json` and `manifest.json`, loopback-only exposure, and notifier behavior through the same mailbox abstraction.
- Update mailbox entry and internals pages so first-time readers encounter the filesystem-versus-Stalwart choice early instead of inferring it from contract pages.
- Update system-files docs so the runtime-owned secret lifecycle is explicit: manifests stay secret-free, durable runtime state keeps credential references and owned material, and session-local files hold materialized secrets when needed.
- Tighten cross-links between mailbox, gateway, and system-files docs so readers can move from quickstart to exact contracts without re-learning conflicting models.
- Keep exact payload shapes and protocol details in the existing contract pages while adding higher-level narrative and comparison structure around them.
- Clarify the current v1 story as implemented behavior rather than future-facing compatibility guidance.

## Capabilities

### New Capabilities

### Modified Capabilities
- `mailbox-reference-docs`: Extend mailbox reference requirements so the docs explicitly teach the Stalwart-backed operator path, transport comparison, gateway-versus-direct mailbox paths, and shared opaque mailbox references without assuming filesystem-first context.
- `agent-gateway-reference-docs`: Extend gateway reference requirements so the docs explicitly cover the mailbox facade, Stalwart-backed mailbox interaction, loopback-only mailbox route availability, and notifier behavior through the shared mailbox abstraction.
- `system-files-reference-docs`: Extend system-files reference requirements so the docs explicitly inventory Stalwart-related runtime artifacts, including secret-free manifest persistence, durable credential references, and session-local materialized credential files.

## Impact

- Affected docs: `docs/reference/mailbox/**`, `docs/reference/gateway/**`, `docs/reference/system-files/**`, and the cross-links that point readers into those trees.
- Affected OpenSpec specs: `openspec/specs/mailbox-reference-docs/spec.md`, `openspec/specs/agent-gateway-reference-docs/spec.md`, and `openspec/specs/system-files-reference-docs/spec.md`.
- Source material reflected by the docs: mailbox runtime support, gateway mailbox adapters and service code, Stalwart transport code, runtime manifest persistence, and gateway/runtime contract tests.
- No runtime behavior, CLI contract, or protocol implementation change is intended in this change; the work is documentation structure and documentation contract coherence only.

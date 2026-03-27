## Context

The live bug investigation showed a three-way contract mismatch. The gateway publishes `AGENTSYS_AGENT_GATEWAY_*` bindings into tmux session env for attached sessions, but the provider process env snapshot does not inherit those updates. At the same time, the runtime-owned mailbox helper `pixi run python -m houmao.agents.mailbox_runtime_support resolve-live` returns mailbox bindings only, while the projected filesystem mailbox skill and gateway notifier prompt both tell the agent to use the shared `/v1/mail/*` facade and not scrape tmux state directly.

That means attached mailbox work currently depends on three partially overlapping channels:

- mailbox bindings from the runtime-owned mailbox helper,
- live gateway endpoint data from tmux session env,
- prompt wording to bridge the two.

The current notifier prompt hotfix inlines the exact base URL and unblocks the demo, but it does not repair the underlying contract split. A future prompt, mailbox command, or skill change could recreate the same failure mode.

## Goals / Non-Goals

**Goals:**
- Give attached mailbox work one runtime-owned discovery path for both mailbox bindings and the live gateway mail-facade endpoint.
- Preserve the existing stable attachability and live gateway env contracts while hiding raw tmux mechanics behind runtime-owned helpers.
- Ensure notifier prompts and projected mailbox skills stay actionable even when the provider process env lacks `AGENTSYS_AGENT_GATEWAY_HOST` and `AGENTSYS_AGENT_GATEWAY_PORT`.
- Fail closed when the gateway is not attached, the live binding is stale, or the gateway is unhealthy.
- Add regression coverage for the exact real-session mismatch that triggered the bug.

**Non-Goals:**
- Changing the `/v1/mail/*` HTTP routes or the mailbox transport semantics themselves.
- Replacing tmux-session env as the runtime's underlying live gateway publication surface.
- Making provider process env snapshots the authoritative live gateway source.
- Broadly redesigning non-mail gateway discovery flows beyond the runtime-owned contract needed for attached mailbox work.

## Decisions

### Extend the existing mailbox live resolver instead of adding a second attached-mail discovery helper

The runtime already points agents at `pixi run python -m houmao.agents.mailbox_runtime_support resolve-live` for attached mailbox work. This change will extend that helper with an optional top-level `gateway` payload for the current session when a live attached gateway is available and valid.

That `gateway` payload should include at minimum:

- `host`
- `port`
- `base_url`
- `protocol_version`
- `state_path`
- a source indicator showing that the live binding came from the runtime-owned live discovery path rather than from the provider process env snapshot

When no live gateway is attached or the live binding fails validation, the helper should report `gateway: null` instead of guessing a default localhost endpoint.

Alternative considered:
- Add a second helper just for gateway endpoint resolution. Rejected because it recreates the same split contract that caused the bug and forces prompts or skills to teach two runtime-owned helpers for one attached mailbox flow.

### Keep tmux session env as the live publication source, but validate and project it through manifest-backed authority

The gateway already publishes live bindings into tmux session env and the runtime already knows how to validate those bindings against manifest-backed session authority and gateway health. This change should reuse that existing authority path rather than duplicating live endpoint state inside provider process env or inventing a second persisted gateway record.

The runtime helper should resolve the owning tmux session from manifest-backed authority, read only the targeted `AGENTSYS_AGENT_GATEWAY_*` fields, validate the live binding, and surface a normalized payload for attached mailbox work.

Alternative considered:
- Copy live gateway host and port into the provider process env after attach. Rejected because it depends on backend-specific env mutation, does not repair the runtime-owned discovery contract, and would still leave prompts and skills with ambiguous authority rules.

### Make the resolver the primary source of truth for gateway-first mailbox prompts and skills

Projected mailbox system skills and runtime-owned mailbox prompts should treat the resolver output as the primary discovery surface for attached shared-mailbox work. The skill can still mention the `/v1/mail/*` routes directly, but it should tell the agent to obtain the current endpoint from the runtime-owned resolver output instead of searching env, tmux, docs, or localhost defaults.

Gateway notifier prompts should follow the same rule. They may continue to inline the exact `base_url` as bounded redundancy for one-turn work, but that inline value must come from the same runtime-owned discovery contract and must not be the only actionable endpoint-discovery path.

Alternative considered:
- Keep the prompt-level base URL injection as the only fix. Rejected because it leaves the mailbox skill and any future gateway-first mailbox prompt on an incomplete contract.

### Treat gateway unavailability as an explicit attached-mail state, not as a prompt-time improvisation

If a mailbox-enabled tmux-backed session has no live attached gateway, or if the live gateway binding is stale or unhealthy, the resolver should surface that fact explicitly. Gateway-first mailbox guidance can then fall back to direct transport-specific mailbox behavior when appropriate, but it should not implicitly guess another port or silently assume the gateway is reachable.

This keeps attached mailbox work fail-closed and makes prompt behavior easier to test.

Alternative considered:
- Let prompts tell the agent to discover the port ad hoc when the gateway is missing. Rejected because that reintroduces tmux scraping and environment inference as part of the supported contract.

## Risks / Trade-offs

- [Extending `resolve-live` changes its JSON shape] → Mitigation: make the new `gateway` field additive, document it explicitly, and update tests to tolerate the extended payload.
- [Live tmux env can be stale after gateway failure] → Mitigation: reuse existing runtime validation and health-probe behavior; return `gateway: null` when the binding cannot be trusted.
- [The mailbox helper becomes responsible for some gateway discovery data] → Mitigation: keep the scope narrow to attached shared-mailbox work and document that the helper exposes the mail-facade endpoint, not a general-purpose gateway client contract.
- [Prompt and skill text can drift from the runtime-owned resolver contract] → Mitigation: add tests that assert notifier prompts and projected mailbox guidance both reference the same runtime-owned discovery path.

## Migration Plan

1. Extend the runtime-owned `resolve-live` helper to project optional validated gateway endpoint data from manifest-backed session authority.
2. Update gateway notifier prompts and projected mailbox system-skill guidance to consume that resolver contract for attached `/v1/mail/*` work.
3. Update gateway and mailbox reference docs to describe the combined attached-mail discovery path.
4. Add unit and integration regression coverage for the live-session mismatch where tmux env has gateway bindings and provider process env does not.
5. Keep the current prompt-level base URL inline until the new resolver-backed tests pass, then treat the inline URL as optional redundancy rather than the sole fix.

Rollback is straightforward because this is a runtime-contract change with no durable data migration. Revert the helper, prompt, skill, and test changes together, and the system falls back to the current prompt-only workaround.

## Open Questions

- Should the notifier prompt continue inlining the exact `base_url` after the resolver exposes `gateway.base_url`, or should it rely solely on the helper output? Current recommendation: keep the inline URL as bounded redundancy, but make the resolver the normative contract.
- Should the longer-term home for this helper remain `mailbox_runtime_support`, or should attached-mail capability discovery later move into a more general runtime capability module? Current recommendation: keep the existing helper path for this fix to avoid introducing a second discovery surface in the same change.

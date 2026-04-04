## Context

Houmao already treats Gemini as a maintained unattended headless lane in project-easy flows, but the current `gemini_headless` launch path still starts Gemini as plain non-interactive `gemini -p` with no explicit approval or sandbox posture. Upstream Gemini CLI interprets that default headless posture as read-only and removes shell and write tools from the active registry, which breaks both direct managed prompting and gateway-driven mailbox wake-up flows.

The existing codebase already contains two strong signals for the target posture. First, the compatibility provider launches Gemini with `--yolo --sandbox false`. Second, the launch-policy framework already owns unattended startup behavior for other providers and can replace conflicting caller inputs before provider start. This change needs to bring runtime-owned Gemini headless launches onto the same explicit policy model while keeping the change version-gated and documented.

## Goals / Non-Goals

**Goals:**
- Make maintained `gemini_headless` unattended launches start with full built-in tool access and no interactive approval prompts.
- Ensure unattended Gemini launch policy owns the effective startup posture even when callers or copied setup baselines attempt to weaken it.
- Keep the solution inside the existing launch-policy architecture so raw launch helpers, runtime-managed launches, and project-easy flows converge on one Gemini unattended contract.
- Add verification that covers both direct managed prompting and gateway-driven message handling.

**Non-Goals:**
- Changing Gemini `as_is` behavior or broadening non-unattended launches to use full-permission defaults.
- Introducing a new Gemini-specific persistent config format when CLI launch arguments already express the intended posture.
- Redesigning demo workflows, mailbox semantics, or generic headless session management beyond the Gemini launch-policy fix.

## Decisions

### Use launch-policy-owned Gemini CLI flags as the primary unattended control surface

Runtime-owned Gemini unattended launch will explicitly apply `--approval-mode yolo` and `--sandbox false` on top of the existing headless `-p` flow. This matches the stated product goal of "all tools, max permissions, no ask" and aligns with Gemini's upstream policy model, where YOLO is the only maintained headless posture that allows shell and write tools without interactive approval.

Alternative considered: use `--approval-mode auto_edit` or `--allowed-tools`. `auto_edit` is insufficient because upstream Gemini still denies shell execution in headless mode. `--allowed-tools` and `tools.core` are also a poor primary control surface because they act as allowlists and are easy to misconfigure into a smaller tool registry than intended.

### Treat Gemini unattended startup surfaces as strategy-owned and canonical

The launch-policy layer will treat Gemini unattended approval and sandbox posture as owned startup surfaces, similar to how Codex and Claude already use strategy-owned startup state. That means runtime-managed Gemini unattended launches must replace or remove conflicting caller-supplied launch inputs rather than trusting callers to supply the correct low-level flags.

Alternative considered: append Gemini defaults only when the caller did not set them. That keeps more caller freedom, but it does not produce a stable maintained unattended contract and leaves the system vulnerable to the exact regression observed in the demo and managed runtime tests.

### Keep runtime-home config mutation minimal, but reserve ownership when Gemini settings would weaken the maintained posture

The current maintained Gemini setup does not need a strategy-owned `.gemini/settings.json` to achieve the target behavior, so the first implementation should prefer launch-arg ownership rather than broad provider-home file mutation. However, the runtime contract should still treat strategy-owned Gemini approval, sandbox, and tool-availability config keys as authoritative if a copied setup baseline or future maintained runtime-home config introduces them.

Alternative considered: always project a Houmao-owned Gemini settings file into the runtime home. That is more invasive, complicates merge/ownership rules, and is unnecessary while CLI flags fully encode the target startup posture.

### Prove the change with runtime-focused Gemini evidence

Verification should include launch-policy/unit coverage for the effective Gemini command line and at least one integration-style flow showing that a managed Gemini unattended session can both answer a direct prompt and process a gateway-notified email task using shell/file tools.

Alternative considered: rely only on launch-command unit tests. That would prove command shape but would not catch the original failure mode, where runtime launch succeeded but the active tool registry was still missing required tools during real work.

## Risks / Trade-offs

- [Broader unattended privileges] → Mitigation: apply the full-permission posture only when `operator_prompt_mode = unattended`; keep `as_is` and other non-unattended paths unchanged and document the explicit risk posture.
- [Upstream Gemini behavior may shift across CLI versions] → Mitigation: keep the change version-gated through the existing launch-policy registry and add tests that assert the intended Gemini startup surfaces.
- [Caller-supplied Gemini flags may be silently replaced] → Mitigation: keep this behavior limited to strategy-owned unattended surfaces and document that unattended launch policy is authoritative by design.
- [Future Gemini setup baselines may introduce restrictive settings files] → Mitigation: define strategy ownership for the relevant keys now, so runtime mutation can safely override only those keys if such a setup is later introduced.

## Migration Plan

No stored data migration is required. Implementation should update the maintained Gemini launch-policy strategy, any Gemini-specific launch-surface normalization, and the launch-policy reference docs, then add or update tests to verify the new behavior. Rollback is a code rollback of the Gemini unattended strategy and its associated tests if upstream CLI behavior changes unexpectedly.

## Open Questions

- Whether the first implementation should actively scrub conflicting Gemini `tools.allowed` or `tools.exclude` settings from copied runtime-home config, or whether documenting strategy ownership and keeping maintained setups free of those keys is sufficient for the initial change.

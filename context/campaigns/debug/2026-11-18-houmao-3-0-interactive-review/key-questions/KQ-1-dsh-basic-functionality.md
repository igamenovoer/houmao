# KQ-1: DSH Basic Functionality With Houmao

Date: 2026-11-18. Status: unresolved. Owner: [iteration 1](../iterations/2026-11-18-plan-1-dsh-basic-functionality.md). Evidence: pending execution.

Does Houmao `3.0.0rc1` prepare, launch, observe, control, resume, interrupt, account usage for, and stop DeepSeek Harness (`dsh` `>=0.2.2-rc.1`, release or `rc` builds) cleanly across both `dsh_acp` (headless) and `dsh_web` (interactive Web) under live human observation on the DeepSeek API (`cloud-api`) and self-hosted Qwen 3.8 (`self-hosted`) model lanes?

## Critical Propositions

### KQ-1.1: Operator Setup and Executable Resolution UX

A human operator creating a fresh disposable project overlay through `houmao-mgr` (configuring DSH credentials, `dsh-setup.yaml`, specialist, and launch profiles) receives clear, actionable validation and error guidance, including for the lower-bounded `>=0.2.2-rc.1` release/rc floor (accepting default `PATH` `0.2.2-rc.1` and `0.2.2-rc.3`, rejecting older or `alpha`/`dev` versions), the empty starter `models: []` catalog, and external credential file boundaries.

- **Test criteria**: Exercise fresh `houmao-mgr project init`, starter `dsh-setup.yaml` failure, unsupported synthetic `0.2.2-alpha.3` / `0.2.1` rejection, and valid `PATH` `dsh` configuration in Arm A0, recording exact stderr/stdout and human clarity feedback.

### KQ-1.2: Headless `dsh_acp` Lifecycle and Live Watchability

When launched via `houmao-mgr project agents launch --headless` on an isolated `-L` tmux server with an attached gateway, a human watching the tmux console and CLI outputs can observe literal role injection (`interpolate: false`), tool execution, exact continuation, scoped interruption, and clean stop without silent hangs or stale runtime locks.

- **Test criteria**: Complete frozen prompts P1 through P4 (greeting, file/shell tool oracle, exact resume, mid-turn interrupt) and `stop` under live tmux observation in Arms A1 and B1.

### KQ-1.3: Interactive `dsh_web` Lifecycle and Human/API Coexistence

When launched with `--no-headless` (`dsh_web`), a human can connect to the native Web UI, select and watch the exact managed session, submit browser prompts alongside `houmao-mgr` API prompts, verify `ready_only` admission refusal during an active turn, and perform scoped interruption and stop without losing conversation history.

- **Test criteria**: Exercise browser observation, human-versus-API turn alternation, busy `ready_only` refusal, interruption, and stop in Arms A2 and B2.

### KQ-1.4: Provider Parity (DeepSeek API Versus Self-Hosted Qwen 3.8) and Usage/Auth Observability

Both the DeepSeek API lane (`deepseek/messages` from `.env`) and the self-hosted Qwen 3.8 lane (`pi-ai/openai-completions`) complete basic turns, tool calls, resume, and `GET /v1/usage` ledger accounting cleanly, with any Qwen 3.8 protocol mismatch or `3.0.0rc1` gateway-auth/fixture discrepancy explicitly localized.

- **Test criteria**: Compare completion, tool-call handling, resume stability, and `GET /v1/usage` records against `session.v4.jsonl` across Arms A1/A2 (DeepSeek API), B1/B2 (Qwen 3.8), and optional fixture cross-check Arm C1.

## Answer

Unresolved. Planned for [iteration 1](../iterations/2026-11-18-plan-1-dsh-basic-functionality.md).

## Scope

This question covers basic DSH (`dsh_acp` and `dsh_web`) lifecycle, operator setup ergonomics, live human watchability, and basic usage/auth observability on both selected model lanes. Native home `refresh` edits (`#82`), cross-user `sudo`/`ssh` execution-owner routing (`#81`), `houmao-cccc` plugins (`#77`/`#78`), and Stalwart dual-mailbox workflows (`#79`/`#80`) are out of scope for Iteration 1 and belong to subsequent iterations.

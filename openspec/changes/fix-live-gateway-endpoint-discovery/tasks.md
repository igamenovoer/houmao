## 1. Runtime Discovery Contract

- [ ] 1.1 Extend `pixi run python -m houmao.agents.mailbox_runtime_support resolve-live` to return optional validated live gateway endpoint data for manifest-backed attached sessions.
- [ ] 1.2 Reuse existing gateway validation and health checks so stale tmux-published gateway bindings resolve as unavailable instead of guessed endpoints.
- [ ] 1.3 Document the resolver payload and attached-mail discovery contract in the gateway and mailbox reference docs.

## 2. Prompt And Skill Adoption

- [ ] 2.1 Update projected mailbox system-skill guidance to obtain attached `/v1/mail/*` endpoint data from the runtime-owned live resolver.
- [ ] 2.2 Update gateway notifier prompt generation to remain actionable through the same runtime-owned endpoint discovery contract.
- [ ] 2.3 Audit other runtime-owned gateway-first mailbox prompts or helpers for instructions that still imply tmux scraping, provider-env port discovery, or localhost default guessing.

## 3. Regression Coverage

- [ ] 3.1 Add unit coverage for the live-session mismatch where tmux session env has gateway bindings and the provider process env snapshot does not.
- [ ] 3.2 Add notifier-prompt coverage asserting the prompt exposes an actionable runtime-owned path to the exact live gateway endpoint.
- [ ] 3.3 Add integration or demo regression coverage proving attached shared-mailbox work does not depend on ad hoc gateway endpoint rediscovery.

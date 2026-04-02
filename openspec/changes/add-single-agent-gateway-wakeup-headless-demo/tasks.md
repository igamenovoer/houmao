## 1. Demo Pack Scaffold

- [x] 1.1 Add the new supported demo pack under `scripts/demo/single-agent-gateway-wakeup-headless/` with tracked inputs, runner, README, expected-report location, and pack-local output ignore policy.
- [x] 1.2 Add the corresponding `houmao.demo.single_agent_gateway_wakeup_headless` implementation package with dedicated driver, models, runtime, mailbox, and reporting modules.
- [x] 1.3 Register the new demo in `scripts/demo/README.md` while keeping `single-agent-mail-wakeup/` documented as the separate supported TUI demo.

## 2. Headless Runtime Workflow

- [x] 2.1 Implement project copy, overlay initialization, reusable specialist/auth/setup preservation, and fresh-run ephemeral-state reset for the new pack.
- [x] 2.2 Implement maintained headless lane configuration for Claude and Codex, including fixture-auth import and project-easy specialist reuse.
- [x] 2.3 Implement stepwise and automatic launch flow using `houmao-mgr project easy instance launch --headless`, persisted demo state, and demo-owned tmux session naming.
- [x] 2.4 Implement headless stepwise operator commands for `attach`, `watch-gateway`, `send`, `notifier status|on|off|set-interval`, and `stop`.
- [x] 2.5 Implement gateway attach in a separate watchable tmux window and persist the metadata needed to rediscover that window during follow-up commands.

## 3. Inspection And Verification

- [x] 3.1 Implement inspect/report collection for gateway status, notifier audit or queue evidence, actor mail state, project-mailbox structural evidence, and deterministic output-file evidence.
- [x] 3.2 Add headless managed-agent evidence collection based on managed-agent inspection surfaces and durable turn or last-turn artifacts without depending on TUI posture.
- [x] 3.3 Implement verify and sanitized-report generation for the new headless demo contract, including actor-scoped unread completion and structural mailbox corroboration.

## 4. Docs And Test Coverage

- [x] 4.1 Add unit coverage for the new headless demo parser, parameter models, auth-import shaping, headless launch shaping, and report contract.
- [x] 4.2 Add focused tests for tmux-session persistence, gateway-window rediscovery, and headless evidence collection behavior.
- [x] 4.3 Update the new demo README with prerequisites, maintained lanes, tmux session model, stepwise commands, verification rules, and Gemini scope limitations if it remains out of contract.
- [x] 4.4 Run the relevant `pixi run` unit test targets for the new demo pack and refresh any tracked expected report snapshot required by the new contract.

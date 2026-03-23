# Live Validation Matrix

Recorded on 2026-03-23 (UTC) against the CLIs installed in this workspace.

## Supported Installed Versions

| Tool | Probe command | Installed version | Supported unattended strategy | Recorded findings |
| --- | --- | --- | --- | --- |
| Codex | `codex --version` | `codex-cli 0.116.0` | `codex-unattended-0.116.x` | Fresh isolated homes succeeded with either `auth.json`, `OPENAI_API_KEY`, or a config-backed env-only provider using `requires_openai_auth = false` and `wire_api = "responses"`. Avoiding startup prompts required runtime-owned trust seeding, `approval_policy = "never"`, `sandbox_mode = "danger-full-access"`, `notice.hide_full_access_warning = true`, and migration state for `gpt-5.3-codex -> gpt-5.4`. |
| Claude Code | `claude --version` | `2.1.81` | `claude-unattended-2.1.81` | Fresh isolated homes succeeded without pre-made prompt-suppression files when runtime created or patched `settings.json` and `.claude.json`. Avoiding startup prompts required `skipDangerousModePermissionPrompt`, onboarding state, custom API-key approval memory, and workspace trust state under the resolved workdir. |

## Explicit Deferrals

| Tool | Status | Notes |
| --- | --- | --- |
| Gemini | deferred | No unattended launch-policy strategy is registered yet. `operator_prompt_mode = unattended` fails closed for Gemini until a versioned strategy is added. |

## Evidence Inputs Used During Implementation

- Local Codex source reference: `extern/orphan/codex/codex-rs/app-server/tests/suite/auth.rs`
- Installed Codex probe: `codex --version`
- Installed Claude probe: `claude --version`
- Local Claude runtime-state observations from `~/.claude.json` and `~/.claude/settings.json`


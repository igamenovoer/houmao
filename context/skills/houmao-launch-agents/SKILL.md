---
name: houmao-launch-agents
description: 'Manual invocation only; use only when the user explicitly requests `houmao-launch-agents` by exact name or asks to use this specific skill. Build and launch fixture-backed Claude Code or Codex agents from `tests/fixtures/agents` through one of two modes: `minimal launch`, which uses the repo builder scripts or modules plus manual `claude` or `codex` execution with no blueprints or roles, or `full launch`, which uses the Houmao pipeline with `build-brain`, `start-session`, prompts, CAO, and cleanup for runtime-managed tests.'
---

# Houmao Launch Agents

This skill has two launch modes. Pick the mode that matches the test boundary before launching anything.

## Mode Selection

- Use `minimal launch`, brain-only plus manual tool launch, when you want to validate brain construction, config projection, skill installation, credential projection, bootstrap behavior, or raw CLI behavior from a generated runtime home.
- Use `minimal launch` when the launched tool should run without Houmao runtime session management, and without blueprints or roles.
- Use `full launch` when you want runtime-managed behavior such as role injection, start or resume or stop lifecycle, `send-prompt`, mailbox flows, gateway flows, CAO integration, shadow parsing, or tracked demo packs.
- Read [references/command-cookbook.md](references/command-cookbook.md) for concrete commands for both modes.

## Named Prompt Options

Experienced users may steer this skill with `option-name=value` pairs inside the request. Default to the narrowest reasonable choices when the prompt does not specify them.

- `launch-mode=minimal-launch|full-launch` selects the overall mode.
- `tool=codex|claude` selects the tool lane.
- `build-source=explicit-inputs|recipe|blueprint` selects how the brain is chosen. `blueprint` is for `full-launch` only.
- `skills=skill-a,skill-b` sets the installed skills for `minimal-launch` when `build-source=explicit-inputs`.
- `brain-recipe=brains/brain-recipes/<tool>/<name>.yaml` selects a tracked brain recipe when `build-source=recipe`.
- `blueprint=blueprints/<name>.yaml` selects a tracked blueprint when `build-source=blueprint`.
- `config-profile=<name>` selects an existing config profile under `tests/fixtures/agents/brains/cli-configs/<tool>/`.
- `credential-profile=<name>` selects an existing local credential profile under `tests/fixtures/agents/brains/api-creds/<tool>/`.
- `workdir=<path>|repo-root|dummy-project:<fixture>` selects the working directory. Use `dummy-project:<fixture>` for a copied fixture workdir such as `dummy-project:mailbox-demo-python`.
- `runtime-root=<path>` selects the generated runtime root.
- `home-id=<name>` selects the generated brain home id.
- `agent-identity=<name>` selects the managed session identity for `full-launch`.
- `manual-launch-mode=launch-helper|direct-cli` selects how `minimal-launch` runs the tool after the brain is built.
- `managed-backend=codex_headless|claude_headless|cao_rest` selects the backend for `full-launch`.
- `prompt-file=<path>` or `prompt-text=<text>` supplies the first managed prompt for `full-launch` when the user wants an immediate turn after startup.
- `control-mode=send-prompt|send-keys` selects the control surface for `full-launch` follow-up actions.
- `cao-parsing-mode=shadow_only|cao_only` selects the CAO parsing posture when `managed-backend=cao_rest`.
- `mailbox-transport=none|filesystem|stalwart` selects the mailbox transport for `full-launch` when mailbox behavior is part of the test.
- `gateway-auto-attach=true|false` selects whether `full-launch` should attach the gateway immediately after startup.
- `demo-pack=none|skill-invocation-demo|cao-codex-session|cao-claude-session` selects whether to use a tracked managed wrapper instead of constructing the flow manually.

Treat these names as skill-level control hints, not as a promise that every option is always applicable. Reject incompatible combinations cleanly. Do not treat prompt configuration as permission to invent missing profiles, credentials, roles, or blueprints. Use only tracked fixtures and existing local credential directories unless the user explicitly asks to create new ones.

## Shared Preparation

1. Confirm credentials.

- Ensure the selected credential profile exists under `tests/fixtures/agents/brains/api-creds/<tool>/<profile>/`.
- If the local credential tree is missing, restore it from `tests/fixtures/agents/brains/api-creds.tar.gz.gpg` using the cookbook commands.
- Never edit or commit credential material.

2. Pick a workdir deliberately.

- Use a copied dummy project for narrow deterministic tests.
- Use the real repository checkout for repository-scale behavior.
- Initialize a fresh `.git` repo inside copied workdirs when the scenario should behave like an isolated project.

3. Keep generated paths explicit.

- Use an explicit `--runtime-root` such as `tmp/houmao-launch-agents/<run-id>/runtime`.
- Set `--home-id` explicitly so the generated home and manifest paths are stable.
- Treat the builder output `manifest_path` as authoritative if any older document disagrees.

## Minimal Launch

1. Build the brain with the lower-level builder, not the runtime controller.

- Prefer `pixi run python scripts/agents/build_brain_home.py ...` for CLI use.
- Use `from houmao.agents import BuildRequest, build_brain_home` when another repo module or script is orchestrating builds programmatically.
- Build from a recipe or from explicit `--tool`, `--skill`, `--config-profile`, and `--cred-profile` inputs.
- Do not use blueprints or roles in `minimal launch`.

2. Launch manually from the generated home.

- Prefer the generated `<runtime-root>/homes/<home-id>/launch.sh`; it exports the tool home selector and runs the shared Codex or Claude bootstrap before executing the real CLI.
- If you intentionally bypass `launch.sh`, first run the matching bootstrap module, then export `CODEX_HOME` or `CLAUDE_CONFIG_DIR`, then invoke `codex` or `claude` directly.
- In `minimal launch`, any extra instructions belong in your prompt text or CLI arguments; do not source behavior from `roles/` or `blueprints/`.

3. Keep the boundary clean.

- `Minimal launch` is for standalone brains and raw tool launches.
- Do not call `start-session`, `send-prompt`, or `stop-session` in this mode.
## Full Launch

1. Build with the runtime-managed surface.

- Use `pixi run python -m houmao.agents.realm_controller build-brain ...`.
- Prefer `--blueprint` with `--agent-def-dir tests/fixtures/agents`; the blueprint binds the correct recipe and role together.

2. Start the managed session.

- Use `start-session` with an explicit `--brain-manifest`, `--workdir`, and `--agent-identity`.
- Use `codex_headless` for normal local Codex sessions.
- Use `claude_headless` for normal local Claude sessions.
- Use `cao_rest` only when the test explicitly involves CAO, shadow parsing, gateway behavior, or a CAO-backed demo.

3. Drive and clean up through Houmao.

- Use `send-prompt` for normal turns.
- Use `send-keys` only for slash menus, trust prompts, or other low-level control input.
- End every live run with `stop-session`.

## Existing Demo Packs

These wrappers belong to `full launch` and already encode verification and cleanup:

- `scripts/demo/skill-invocation-demo-pack/run_demo.sh --tool codex|claude`
- `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh`

## Guardrails

- Do not use blueprints or roles in `minimal launch`.
- Do not use raw `claude` or `codex` launches in `full launch` when the point of the test is Houmao-managed lifecycle behavior.
- Do not assume tool-specific nested manifest directories; use the builder output.
- Do not reuse an `--agent-identity` that may still refer to a live session unless the task is explicitly resuming it.
- Do not commit `tests/fixtures/agents/brains/api-creds/**` or extracted secrets.

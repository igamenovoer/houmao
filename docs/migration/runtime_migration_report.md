# Runtime Migration Report

Date: 2026-03-05

## Scope Summary

This change completed copy-first extraction of the runtime subsystem from
`agent-system-dissect` into the tracked Houmao repository.

Copied runtime scope includes:

- Runtime source modules:
  - `src/agent_system_dissect/agents/realm_controller/**`
  - `src/agent_system_dissect/agents/brain_builder.py`
  - `src/agent_system_dissect/agents/__init__.py`
  - `src/agent_system_dissect/cao/**`
- Runtime launcher config:
  - `config/cao-server-launcher/local.toml`
- Runtime tests and fixtures:
  - `tests/unit/agents/**`
  - `tests/unit/cao/**`
  - `tests/fixtures/shadow_parser/**`
  - `tests/manual/manual_headless_tmux_smoke.py`
  - full `agents/` tree mirrored at `tests/fixtures/agents/**`
- Runtime scripts/demos:
  - `scripts/agents/**`
  - `scripts/demo/**`
  - `scripts/explore/interactive-pipeline-test/**`
- Runtime docs:
  - `docs/reference/agents_brains.md`
  - `docs/reference/realm_controller.md`
  - `docs/reference/cao_claude_shadow_parsing.md`
  - `docs/reference/cao_server_launcher.md`
  - `docs/reference/cao_shadow_parser_troubleshooting.md`
  - `docs/reference/cli.md`

## Runtime-Only OpenSpec Relocation Allowlist

Main specs copied to `openspec/specs/`:

- `agent-identity`
- `brain-launch-runtime`
- `brain-launch-runtime-pydantic-boundaries`
- `cao-claude-code-output-extraction`
- `cao-claude-demo-scripts`
- `cao-codex-output-extraction`
- `cao-loopback-no-proxy`
- `cao-rest-client-contract`
- `cao-server-launcher`
- `cao-server-launcher-demo-pack`
- `claude-cli-noninteractive-startup`
- `codex-target-profile`
- `component-agent-construction`
- `versioned-shadow-parser-stack`

Archived changes copied to `openspec/changes/archive/`:

- `2026-02-26-agents-brain-role-layout`
- `2026-02-28-agent-brain-launch-runtime`
- `2026-02-28-agent-brain-launch-runtime-claude-cli-contracts`
- `2026-02-28-agent-brain-launch-runtime-pydantic-models`
- `2026-02-28-fix-cao-claude-output-mode-last`
- `2026-03-02-agent-identity-tmux-manifest-path`
- `2026-03-02-cao-claude-demo-fs-interrupt`
- `2026-03-02-cao-resume-manifest-only`
- `2026-03-03-claude-code-model-selection`
- `2026-03-03-decouple-cao-shadow-parser-modes`
- `2026-03-04-codex-noninteractive-stalled-shadow-state`
- `2026-03-04-versioned-shadow-parser-superset`
- `2026-03-05-cao-loopback-no-proxy-default`
- `2026-03-05-cao-server-launcher`
- `2026-03-05-cao-server-launcher-demo-pack`
- `2026-03-05-fix-cao-bootstrap-window-shell-first-attach`
- `2026-03-05-unify-headless-tmux-backend`

## Parity And Validation Results

- Static checks:
  - `pixi run ruff check src tests docs scripts` -> pass
  - `pixi run mypy src` -> pass
- Runtime unit suites:
  - `pixi run python -m pytest tests/unit/agents tests/unit/cao` -> pass (`170 passed`)
- Parity preflight:
  - `scripts/parity/check_runtime_parity.sh` -> pass
  - `rg -n -- "^(from|import) agent_system_dissect" src tests scripts` -> no matches
- Demo workflows:
  - `scripts/demo/cao-server-launcher/run_demo.sh` -> pass
  - legacy CAO session smoke demos -> skipped (missing credentials), exit 0
  - `scripts/demo/gemini-headless-session/run_demo.sh` -> skipped (missing credentials), exit 0
- Packaging:
  - `pixi run python -m build --sdist --wheel` -> pass
  - `pixi run python -m twine check dist/*` -> pass
  - wheel smoke install/import/CLI checks in clean venv -> pass
  - wheel metadata requires only:
    - `pydantic>=2.12,<3`
    - `PyYAML>=6.0,<7`
  - no CAO package dependency declared in published artifact metadata
  - required runtime schemas are present in both wheel and sdist
  - excluded development trees (`tests/`, `scripts/`, `docs/`, `openspec/`, `config/`, `examples/`) are absent from artifacts
- Main workspace integration:
  - editable dependency wiring resolves `houmao` import from submodule path
  - `pixi run houmao-cli --help` -> pass
  - `pixi run houmao-cao-server --help` -> pass

## Residual Mismatches / Follow-Ups

- No behavior-level parity mismatches were found in automated checks.
- Credential-gated demo scenarios were validated as explicit skip paths due to missing local secrets; they are not functional regressions.
- Resume portability remains intentionally deferred in this phase: runtime resume still requires agent-definition directory access and role reload.
  - Known issue reference:
    `context/issues/known/issue-runtime-resume-still-coupled-to-agent-def-dir.md`

## Copy-First Retention Note

This migration is intentionally non-destructive. Source runtime files in
`agent-system-dissect` are retained during this phase for transition safety and
parity verification; canonical ownership is moved to `Houmao`.

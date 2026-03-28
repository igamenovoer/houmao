# How Do I Verify That A Tracked Installed Skill Actually Triggers In A Live Claude Or Codex Session?

Default agent-definition directory: `tests/fixtures/agents` (override with `AGENT_DEF_DIR=/path/to/agents`).

This demo pack answers one narrow maintainer question:

> "If Houmao projects a tracked skill into the runtime home, will a live Claude or Codex session invoke it from ordinary trigger wording without being told the skill package name or install path?"

Success means the selected live session writes the tracked probe marker file inside the copied dummy-project workdir:

- `.houmao-skill-invocation-demo/markers/workspace-probe.json`

The pack treats that marker side effect as the correctness boundary. Assistant reply text is supplemental only.

## Prerequisites Checklist

- [ ] `pixi` is installed.
- [ ] The repo environment is installed (`pixi install` once).
- [ ] `tmux` is installed and on `PATH`.
- [ ] The selected tool executable (`claude` or `codex`) is installed and on `PATH`.
- [ ] The selected credential profile referenced by `skill-invocation-demo-<tool>.yaml` is available.
- [ ] You are running from this repository checkout.

The supported live path for v1 is launcher-managed loopback CAO. The helper writes a demo-local launcher config under `<demo-output-dir>/cao/`, starts or reuses loopback CAO there, and records the matching profile-store path inside the demo state.

If `CAO_BASE_URL` points at a non-loopback or otherwise externally owned CAO instance, the pack exits `0` with `SKIP:` guidance instead of guessing ownership or shutdown responsibilities.

## Filesystem Layout

```text
<demo-output-dir>/
├── cao/                        # demo-local CAO launcher config and runtime state
├── control/                    # persisted state, prompt artifacts, inspection, and reports
├── inputs/                     # copied tracked prompt + parameter inputs
├── project/                    # copied dummy-project fixture initialized as a fresh git repo
└── runtime/                    # built brain outputs and session manifests
```

Important files under `control/`:

- `demo_state.json`
- `cao_start.json`
- `brain_build.json`
- `session_start.json`
- `prompt.events.jsonl`
- `prompt.json`
- `inspect.json`
- `report.json`
- `report.sanitized.json`
- `stop.json`

By default, the wrapper uses `tmp/demo/skill-invocation-demo-pack`. Override it with `--demo-output-dir <abs-or-rel-path>`. Relative paths resolve from the repository root.

## Selected Tool Lane

The same pack supports both tools through `--tool claude|codex`.

Examples:

```bash
scripts/demo/skill-invocation-demo-pack/run_demo.sh --tool codex
```

```bash
scripts/demo/skill-invocation-demo-pack/run_demo.sh --tool claude
```

Tracked tool lanes:

- Claude: `tests/fixtures/agents/blueprints/skill-invocation-demo-claude.yaml`
- Codex: `tests/fixtures/agents/blueprints/skill-invocation-demo-codex.yaml`

Each lane uses the lightweight `skill-invocation-demo` role plus the tracked `skill-invocation-probe` skill fixture. Recipes own the skill/config/credential inputs; blueprints only bind those recipes to the role.

## Automatic Workflow

Run the maintainer-style end-to-end flow for one selected tool:

```bash
scripts/demo/skill-invocation-demo-pack/run_demo.sh auto --tool codex
```

What it does:

1. Copies `tests/fixtures/dummy-projects/mailbox-demo-python` into `<demo-output-dir>/project` and initializes it as a fresh standalone git repo.
2. Starts or safely reuses launcher-managed loopback CAO under `<demo-output-dir>/cao/`.
3. Builds the selected `skill-invocation-demo` brain and starts a live `cao_rest` session in `shadow_only`.
4. Sends the tracked trigger prompt from [`inputs/trigger_prompt.md`](inputs/trigger_prompt.md).
5. Waits for the expected probe marker file to appear in the copied workdir.
6. Builds `report.json`, sanitizes it to `report.sanitized.json`, and compares that sanitized content to [`expected_report/report.json`](expected_report/report.json).
7. Stops the live session and demo-owned CAO.

## Stepwise Workflow

Start the live session and keep it running:

```bash
scripts/demo/skill-invocation-demo-pack/run_demo.sh start --tool codex
```

Inspect the persisted watch coordinates:

```bash
scripts/demo/skill-invocation-demo-pack/run_demo.sh inspect --tool codex
```

`inspect` writes `control/inspect.json` and reports the coordinates you need to attach or debug a slow run:

- session manifest path
- agent identity
- tmux session name
- CAO session name
- CAO terminal id
- tmux window name
- parsing mode
- current probe-marker status

Send the tracked trigger prompt:

```bash
scripts/demo/skill-invocation-demo-pack/run_demo.sh prompt --tool codex
```

The tracked prompt uses trigger wording only. It does not name the skill package and does not leak the skill install path.

Verify the marker/report contract:

```bash
scripts/demo/skill-invocation-demo-pack/run_demo.sh verify --tool codex
```

Stop the live session and demo-owned CAO:

```bash
scripts/demo/skill-invocation-demo-pack/run_demo.sh stop --tool codex
```

All stepwise commands reuse the same selected `--demo-output-dir`, so `start`, `inspect`, `prompt`, `verify`, and `stop` all act on the same copied project and the same persisted session metadata.

## Verification Boundary

The probe contract is intentionally deterministic.

Expected marker path:

- `.houmao-skill-invocation-demo/markers/workspace-probe.json`

Expected marker payload:

```json
{
  "schema_version": 1,
  "probe_id": "skill-invocation-demo",
  "marker_kind": "workspace_probe_handshake",
  "status": "ok"
}
```

The report captures:

- selected tool lane
- tracked prompt metadata
- persisted watch/session coordinates
- expected marker location
- observed marker payload
- verification pass/fail outcome

The committed snapshot compares sanitized content only, so timestamps, absolute paths, session ids, and tool-specific launch details are normalized before comparison.

## Snapshot Refresh

Refresh the tracked sanitized snapshot after an intentional contract change:

```bash
scripts/demo/skill-invocation-demo-pack/run_demo.sh verify --tool codex --snapshot-report
```

Or rerun the full automatic flow and refresh from that run:

```bash
scripts/demo/skill-invocation-demo-pack/run_demo.sh auto --tool codex --snapshot-report
```

## Reusable Probe Fixture

This pack is backed by a tracked reusable fixture family:

- Skill: [`tests/fixtures/agents/brains/skills/skill-invocation-probe/SKILL.md`](../../../tests/fixtures/agents/brains/skills/skill-invocation-probe/SKILL.md)
- Probe contract note: [`tests/fixtures/agents/brains/skills/skill-invocation-probe/references/contract.md`](../../../tests/fixtures/agents/brains/skills/skill-invocation-probe/references/contract.md)
- Role: [`tests/fixtures/agents/roles/skill-invocation-demo/system-prompt.md`](../../../tests/fixtures/agents/roles/skill-invocation-demo/system-prompt.md)

Use this fixture family when the question under test is whether an installed skill triggers cleanly from narrow prompt wording. Keep `mailbox-demo` for mailbox/runtime-contract flows and keep the GPU-oriented roles for repository-scale engineering behavior.

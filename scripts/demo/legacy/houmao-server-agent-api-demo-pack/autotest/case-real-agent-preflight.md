# Real-Agent Preflight

This guide validates the fail-fast contract for the demo pack before any owned `houmao-server` startup or lane provisioning begins.

## Goal

Prove that missing executables, missing credentials, missing pack-owned selector assets, or unsafe output-root reuse are surfaced as preflight blockers instead of partial live runs.

## Steps

1. Pick a fresh output root.

```bash
export DEMO_OUTPUT_DIR=/tmp/houmao-server-agent-api-preflight
rm -rf "$DEMO_OUTPUT_DIR"
```

2. Run the preflight case.

```bash
scripts/demo/houmao-server-agent-api-demo-pack/autotest/run_autotest.sh \
  --case real-agent-preflight \
  --demo-output-dir "$DEMO_OUTPUT_DIR"
```

Expected:

```text
The command exits 0 only when every required executable, credential input, and pack-owned asset is present.
```

3. Inspect the preflight artifact.

```bash
cat "$DEMO_OUTPUT_DIR/control/autotest/case-real-agent-preflight.preflight.json"
```

Look for:

- the `executables` map includes `tmux` and the selected providers
- `credential_env_var_names` is populated
- `missing` is empty

Representative output:

```json
{
  "missing": [],
  "ok": true
}
```

4. Inspect the phase log directory.

```bash
ls "$DEMO_OUTPUT_DIR/logs/autotest/real-agent-preflight"
```

Expected:

- `01-preflight.command.txt`
- `01-preflight.stdout.txt`
- `01-preflight.stderr.txt`

5. Validate the failure path intentionally.

Remove one real prerequisite, then rerun step 2. Examples:

- hide `tmux` from `PATH`
- remove the required API key from the selected credential profile
- point `--demo-output-dir` at a non-empty directory

Expected failure behavior:

- the command exits non-zero
- no lane workdirs or live server artifacts are created
- the failure is described directly in the preflight output

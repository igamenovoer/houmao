# Houmao Launch Agents Cookbook

## Shared Defaults

- Run from the repository root.
- Treat `tests/fixtures/plain-agent-def/` as the maintained secret-free direct-dir source tree.
- Treat `tests/fixtures/auth-bundles/` as the maintained local credential source tree.
- Use `tmp/houmao-launch-agents/<run-id>/...` for copied temp roots and generated artifacts.

## Restore Local Auth Bundles

Run this only if `tests/fixtures/auth-bundles/<tool>/<bundle>/` is missing or incomplete:

```bash
set -a
. ./.env
set +a

openssl enc -d -aes-256-cbc -pbkdf2 -salt \
  -pass env:AGENT_CREDENTIAL_COMPRESS_PASSWORD \
  -in tests/fixtures/auth-bundles/tools.tar.gz.enc \
| tar -C tests/fixtures/auth-bundles -xzf -
```

Keep extracted bundle contents local-only and do not commit them in plaintext.

## Prepare A Temporary Plain Direct-Dir Root

Use this when you need one explicit `--agent-def-dir` target for experiments or credential CRUD:

```bash
RUN_ID="plain-dir-$(date -u +%Y%m%dT%H%M%SZ)"
RUN_ROOT="tmp/houmao-launch-agents/$RUN_ID"
TEMP_AGENT_DEF="$RUN_ROOT/agent-def"

mkdir -p "$RUN_ROOT"
cp -R tests/fixtures/plain-agent-def "$TEMP_AGENT_DEF"
mkdir -p "$TEMP_AGENT_DEF/tools/claude/auth"
cp -R tests/fixtures/auth-bundles/claude/kimi-coding \
  "$TEMP_AGENT_DEF/tools/claude/auth/kimi-coding"
```

Swap tool and bundle names as needed.

## Maintained Minimal Demo

Claude:

```bash
scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider claude_code
```

Codex:

```bash
scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider codex
```

These maintained scripts create one generated overlay-local tree under `outputs/.../workdir/.houmao/`.

## Maintained Shared TUI Tracking Demo

Claude live watch:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool claude
```

Codex live watch:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool codex
```

Recorded validation:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-validate-corpus
```

## Direct-Dir Credential Commands

List Codex auth names from the maintained plain direct-dir lane:

```bash
pixi run houmao-mgr credentials codex list \
  --agent-def-dir tests/fixtures/plain-agent-def
```

Add one temp Claude auth directory under a copied temp root:

```bash
pixi run houmao-mgr credentials claude add \
  --agent-def-dir "$TEMP_AGENT_DEF" \
  --name breakglass \
  --api-key sk-test
```

## Maintained References

- `tests/fixtures/plain-agent-def/README.md`
- `tests/fixtures/auth-bundles/README.md`
- `scripts/demo/minimal-agent-launch/tut-agent-launch-minimal.md`
- `scripts/demo/shared-tui-tracking-demo-pack/README.md`

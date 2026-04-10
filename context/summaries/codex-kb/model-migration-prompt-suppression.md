# Codex Model Migration Prompt Suppression

## Question

How can Houmao or an operator prevent Codex TUI from stopping on the `Introducing GPT-5.4` migration chooser when launching an older configured model such as `gpt-5.2`?

## Short Answer

Codex does not appear to expose a dedicated `--skip-model-upgrade-prompt` flag for this case.

The supported suppression path is to pre-seed the migration acknowledgement map in Codex config:

```toml
[notice.model_migrations]
"gpt-5.2" = "gpt-5.4"
```

Important detail:

- the model key must be quoted in TOML because `gpt-5.2` contains dots
- an unquoted key failed config loading in the live probe

With that mapping present, Codex TUI skipped the migration modal and proceeded to the normal startup flow.

## Empirical Probe

Probe environment:

- workspace: `/data1/huangzhe/code/houmao`
- local Codex source checkout: `extern/orphan/codex`
- installed CLI: `codex-cli 0.118.0`
- temp Codex home: `/data1/huangzhe/code/houmao/tmp/codex-migration-check/home`
- auth fixture: `tests/fixtures/agents/tools/codex/auth/yunwu-openai/env/vars.env`
- base config fixture: `tests/fixtures/agents/tools/codex/setups/yunwu-openai/config.toml`

Live launch used:

```bash
env CODEX_HOME=/data1/huangzhe/code/houmao/tmp/codex-migration-check/home \
  codex --no-alt-screen -m gpt-5.2
```

Observed behavior:

1. With this config stanza present:

   ```toml
   [notice.model_migrations]
   "gpt-5.2" = "gpt-5.4"
   ```

   Codex did not show the `Introducing GPT-5.4` chooser.

2. The first screen was the normal directory trust prompt.

3. After accepting trust, Codex entered the regular chat UI and the footer still showed `gpt-5.2 high`.

4. No migration modal appeared before termination of the probe session.

## Config Parsing Gotcha

This failed:

```toml
[notice.model_migrations]
gpt-5.2 = "gpt-5.4"
```

The startup error was effectively:

```text
Error loading config.toml: invalid type: map, expected a string in notice.model_migrations.gpt-5
```

So any dotted model slug in `notice.model_migrations` should be quoted.

## What Codex Source Shows

Local upstream source indicates that:

- `gpt-5.2` and `gpt-5.2-codex` carry upgrade metadata to `gpt-5.4` in `extern/orphan/codex/codex-rs/models-manager/models.json`
- the TUI suppresses the prompt when `notice.model_migrations[current_model] == target_model` in `extern/orphan/codex/codex-rs/tui/src/app.rs`
- choosing either `Try new model` or `Use existing model` persists that acknowledgement mapping, so the map means "already acknowledged this migration pair"

This means the config entry is not a forced model switch. It is an acknowledgement that prevents the modal from being shown again for that old-model to new-model pair.

## Operational Rule

If Houmao intentionally launches Codex on an older model and wants unattended startup, it should write the matching acknowledgement entry into the generated Codex home before TUI launch.

Examples:

```toml
[notice.model_migrations]
"gpt-5.2" = "gpt-5.4"
"gpt-5.2-codex" = "gpt-5.4"
```

## Scope and Caveat

- This note experimentally verified the config-file suppression path for `gpt-5.2`.
- The same rule should apply to `gpt-5.2-codex` because the local source advertises the same upgrade target, but that specific pair was not separately launched in this probe.
- Codex may still stop on other first-run prompts such as directory trust; this note is specifically about the model migration chooser.

## Related Repo Context

- related resolved issue: `context/issues/resolved/issue-codex-model-migration-modal-blocks-interactive-demo-startup.md`
- probe home config: `/data1/huangzhe/code/houmao/tmp/codex-migration-check/home/config.toml`

## Source References

- `extern/orphan/codex/codex-rs/models-manager/models.json`
- `extern/orphan/codex/codex-rs/tui/src/app.rs`
- `extern/orphan/codex/codex-rs/tui/src/model_migration.rs`
- `extern/orphan/codex/codex-rs/utils/cli/src/config_override.rs`
- `tests/fixtures/agents/tools/codex/auth/yunwu-openai/env/vars.env`
- `tests/fixtures/agents/tools/codex/setups/yunwu-openai/config.toml`

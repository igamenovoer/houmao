# Claude Vendor Login Files

This page explains how Houmao handles Claude Code vendor login files, what CLI shape to use, and what to avoid when turning an existing Claude login into a Houmao auth bundle or easy specialist.

## The File Roles

For the maintained Claude vendor-login lane, treat these files as a set:

- `.credentials.json`: the actual vendor login credential store
- `.claude.json`: companion Claude global/runtime state

Houmao treats `.credentials.json` as opaque vendor state. Do not normalize it into a Houmao-specific format, do not rename it, and do not assume only one key inside it matters.

Houmao treats `.claude.json` as companion runtime state. When present, Houmao carries it with the vendor login lane. For local fixture or smoke-validation use, this file may be minimized to a valid JSON object such as `{}`.

Separate from those files:

- `claude_state.template.json` is optional reusable Houmao bootstrap state, not a Claude credential-providing method
- `settings.json` comes from the selected Claude setup bundle, not from the vendor login import

## Supported CLI Shape

Pass the Claude config root directory, not the individual files.

Low-level auth bundle import:

```bash
houmao-mgr project credentials claude add \
  --name official-login \
  --config-dir ~/.claude
```

Easy-specialist import:

```bash
houmao-mgr project easy specialist create \
  --name claude-reviewer \
  --tool claude \
  --system-prompt "You are a Claude-based code reviewer." \
  --claude-config-dir ~/.claude
```

In both cases, Houmao imports `.credentials.json` from that config root and also carries companion `.claude.json` when present.

Optional Claude settings such as `--base-url`, launch-owned `--model`, and launch-owned `--reasoning-level` can be layered on top of the vendor login lane. For Claude, Houmao currently interprets `--reasoning-level` as `1=low`, `2=medium`, `3=high`, and `4=max` only on models that support Claude `max`; higher values saturate to the highest maintained Claude preset. `--claude-model` remains a compatibility alias for `--model` on the easy-specialist surface only. `--claude-state-template-file` remains optional bootstrap state only.

## What Not To Do

Do not pass `.credentials.json` and `.claude.json` as separate create-command flags. The maintained CLI contract is directory-oriented through `--config-dir` or `--claude-config-dir`.

Do not treat `claude_state.template.json` as one of the ways to provide Claude credentials. It is only bootstrap/runtime seed state.

Do not import a standalone `.claude.json` without the maintained `.credentials.json` login-state file and expect that to count as a supported Claude credential lane.

Do not commit vendor login files into tracked repository content. Under `tests/fixtures/agents`, `tools/**/auth/**` remains local-only host state.

## Runtime Behavior

Houmao projects vendor login files into an isolated runtime-owned `CLAUDE_CONFIG_DIR`. It does not repurpose the launched repo's `.claude/` tree as the runtime Claude home.

When projected `.claude.json` is already present, Houmao does not require `claude_state.template.json` for unattended Claude startup. The runtime preserves projected `.credentials.json` and only mutates strategy-owned startup and trust keys in `.claude.json`.

For the maintained vendor-login lane, a minimized projected `.claude.json` such as `{}` is valid as long as Houmao can merge the strategy-owned onboarding, trust, and approval state it needs at launch time.

## Local Fixture Workflow

For local smoke validation, reserve this local-only fixture name:

```text
tests/fixtures/agents/tools/claude/auth/official-login/
  env/vars.env
  files/.credentials.json
  files/.claude.json
```

Use these rules:

- copy vendor `.credentials.json` unchanged into `files/.credentials.json`
- keep `files/.claude.json` present; for local validation `{}` is acceptable
- keep `env/vars.env` empty unless you intentionally want a local override
- do not add `claude_state.template.json` for this lane

The maintained local smoke workflow is:

```bash
pixi run python tests/manual/manual_claude_official_login_smoke.py \
  --source-config-dir ~/.claude
```

That script:

- provisions or refreshes the local-only `official-login` bundle
- launches `server-api-smoke` from a fresh workdir under `tmp/`
- sets `HOUMAO_AGENT_DEF_DIR` to `tests/fixtures/agents`
- forces an overlay-local `.houmao` inside the temp workdir
- runs the Claude launch headlessly with `--auth official-login --headless`
- stops and cleans up the managed session after validation

If you only want to refresh the local fixture without launching, run:

```bash
pixi run python tests/manual/manual_claude_official_login_smoke.py \
  --source-config-dir ~/.claude \
  --prepare-only
```

## Related Docs

- [Easy Specialists](../getting-started/easy-specialists.md)
- [houmao-mgr CLI](cli/houmao-mgr.md)
- [System Files: Operator Preparation](system-files/operator-preparation.md)

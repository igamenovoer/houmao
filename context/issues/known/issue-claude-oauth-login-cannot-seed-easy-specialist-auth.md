# Issue: Claude OAuth Login Cannot Seed Easy Specialist Auth

## Priority
P2 - A common healthy local Claude setup looks authenticated to the operator, but Houmao's higher-level specialist authoring path still cannot create or refresh a Claude specialist without extra manual credential export.

## Status
Open as of 2026-04-05.

## Summary

Current Houmao specialist authoring does not treat an existing local Claude Code OAuth login as sufficient input for `project easy specialist create --tool claude`, even when the local `claude` CLI is healthy and reports the user as logged in.

In the reproduced case, all of the following were true on the same machine:

- `claude auth status` reported `loggedIn: true`, `authMethod: "claude.ai"`, and a valid subscription-backed account.
- Claude's normal persisted login files existed under the home config root.
- Houmao's `auto credentials` path still could not create the specialist because it only accepts Claude auth in one of three importable forms: `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, or an existing reusable `claude_state.template.json`.

This creates a user-visible mismatch between "Claude is already logged in and usable" and "Houmao can actually create a reusable Claude specialist."

## Reproduction

1. Confirm that the local Claude CLI is authenticated:

```bash
claude auth status
```

Observed on this machine:

```json
{
  "loggedIn": true,
  "authMethod": "claude.ai",
  "apiProvider": "firstParty",
  "subscriptionType": "max"
}
```

2. Confirm that Claude's local persisted login state exists:

```bash
test -f "$HOME/.claude/.credentials.json" && echo present
test -f "$HOME/.claude.json" && echo present
```

3. Attempt to author a Claude specialist through the supported easy path using automatic credential discovery:

```text
name=gpu-coder (overwrite if exist), tool=claude, auto credentials
```

4. Observe that Houmao still cannot create the specialist from the current Claude login and instead requires one of:

- `--api-key`
- `--claude-auth-token`
- `--claude-state-template-file`

The default project auth bundle for the requested specialist also does not exist yet:

```bash
pixi run houmao-mgr project agents tools claude auth get --name gpu-coder-creds
```

Observed failure:

```text
Error: Auth bundle not found: /data1/huangzhe/code/houmao/.houmao/agents/tools/claude/auth/gpu-coder-creds
```

## Evidence

### 1. `project easy specialist create` does not have a first-party Claude OAuth input

The current easy specialist create surface supports Claude auth via:

- `--api-key`
- `--claude-auth-token`
- `--claude-state-template-file`

Source:

- `src/houmao/srv_ctrl/commands/project.py`
- `docs/reference/cli/houmao-mgr.md`

### 2. The current Houmao Claude auto-credential guidance explicitly rejects OAuth login state as importable

The Claude credential lookup reference currently says importable forms are only:

- `ANTHROPIC_API_KEY`
- `ANTHROPIC_AUTH_TOKEN`
- an existing reusable `claude_state.template.json`

It also explicitly classifies these as non-importable for specialist creation:

- OAuth login state in `.credentials.json` or `~/.claude.json`
- other runtime-only Claude auth state that cannot be mapped into the supported create-command flags

Source:

- `src/houmao/agents/assets/system_skills/houmao-create-specialist/references/claude-credential-lookup.md`

### 3. The local Claude login state is real, but it remains trapped in Claude-owned runtime files

On this machine, `~/.claude/.credentials.json` contains a `claudeAiOauth` object with OAuth tokens and refresh material, and `~/.claude.json` contains `oauthAccount` metadata. Houmao can detect that the user is logged in, but the current contract does not let it reuse that state for specialist creation.

### 4. The current workaround requires a separate export step outside the easy flow

The practical operator workaround is to run `claude setup-token` and then feed the resulting long-lived token into Houmao as `--claude-auth-token`, or to provide some other explicit supported auth input. That means the existing local Claude login is not enough on its own.

## Root Cause

This is not just a missing file lookup.

The current system boundary is:

1. Claude Code stores first-party OAuth login in Claude-owned runtime files.
2. Houmao easy specialist creation only knows how to persist reusable auth bundles from explicit env-like values or a reusable state template file.
3. Houmao's current auto-credential contract therefore treats healthy Claude OAuth login state as discoverable evidence of login, but not as importable credential material.

So the actual bug is a product/contract gap between:

- what operators reasonably mean by "Claude is already logged in"
- what Houmao currently accepts as reusable specialist auth inputs

## Why This Matters

This breaks the expected ergonomics of the supported higher-level authoring flow.

For a logged-in Claude user, `auto credentials` strongly implies that Houmao should be able to reuse the current working Claude authentication posture. Instead, the system rejects the most common local Claude state and forces the operator into a second manual export step that is not obvious from the starting posture.

That is especially confusing because the failure does not mean Claude auth is broken. It means Houmao cannot bridge from Claude's current auth representation into Houmao's reusable specialist representation.

## Current Workarounds

### Workaround A: Export a long-lived Claude token manually

Run:

```bash
claude setup-token
```

Then create or update the Houmao Claude auth bundle using the resulting token.

### Workaround B: Provide another explicitly supported input

Use one of:

- `--api-key`
- `--claude-auth-token`
- `--claude-state-template-file`

### Workaround C: Reuse an already-created Houmao auth bundle

If the target project already has the intended Claude auth bundle, easy specialist create can reuse it without rediscovering auth.

## Desired Direction

### 1. Define whether logged-in Claude OAuth should be a supported easy-auth source

If the intended operator contract is "auto credentials should reuse a normal local Claude login when possible," Houmao needs an explicit import bridge for that posture.

### 2. Add a supported bridge from Claude OAuth state to reusable specialist auth

Possible valid directions include:

- import a sanctioned Claude-auth-derived token or state artifact into the project auth bundle
- support a dedicated "reuse current Claude login" authoring path that materializes a valid bundle
- teach the system how to derive a reusable `claude_state.template.json` from a supported source, if that is safe and stable

### 3. If direct OAuth reuse is intentionally unsupported, make the failure contract explicit earlier

If Houmao will continue to reject Claude OAuth login state for specialist creation, the operator-facing flow should fail fast with a clear message such as:

```text
Claude is logged in, but Houmao cannot currently import Claude OAuth login directly.
Run `claude setup-token` or provide `--claude-auth-token`, `--api-key`, or `--claude-state-template-file`.
```

That would at least remove the current "it found login but still says no usable credentials" ambiguity.

## Suggested Follow-Up

1. Decide whether this should be solved in core Houmao auth-import logic, in the higher-level easy specialist workflow, or both.
2. Add an automated test that covers a Claude-first-party-login-shaped environment and verifies the intended operator contract.
3. Update the skill/reference/docs surface so "auto credentials" and "logged in Claude" describe the same supported reality.

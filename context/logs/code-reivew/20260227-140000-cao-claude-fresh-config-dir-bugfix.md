# Bugfix Report: CAO Claude Code Demo — Fresh CLAUDE_CONFIG_DIR Blocks Startup

**Date:** 2026-02-27
**Related issue:** `context/issues/known/issue-cao-claude-code-init-timeout.md`
**Supersedes:** `context/logs/code-reivew/20260227-120000-cao-claude-proxy-env-bugfix.md` (proxy hypothesis was secondary, not primary)

---

## 1. Problem

The historical CAO Claude Code session demo wrapper fails with:

```
Failed to create terminal: Claude Code initialization timed out after 30 seconds
```

CAO creates a tmux session, launches `claude --dangerously-skip-permissions` inside it, then polls `get_status()` waiting for the `❯` idle prompt. Claude Code never reaches the idle prompt because it enters an interactive first-run initialization flow that blocks in the non-interactive tmux window.

## 2. Root Cause

**The brain launch runtime sets `CLAUDE_CONFIG_DIR` to a fresh empty directory for session isolation. Claude Code v2.x interprets this as a first launch and enters interactive setup screens that cannot complete unattended.**

### How Claude Code resolves its global state file

From `cli.js` (v2.1.62):

```javascript
// Config directory
function HA() {
  return (process.env.CLAUDE_CONFIG_DIR ?? join(homedir(), ".claude")).normalize("NFC");
}

// Global state file (.claude.json)
kW = () => {
  if (existsSync(join(HA(), ".config.json")))
    return join(HA(), ".config.json");
  let A = `.claude${fileSuffix()}.json`;  // fileSuffix() returns "" in prod
  return join(process.env.CLAUDE_CONFIG_DIR || homedir(), A);
};
```

When `CLAUDE_CONFIG_DIR=/some/fresh/path`:
- Global state: `/some/fresh/path/.claude.json` (does not exist)
- Settings: `/some/fresh/path/settings.json` (does not exist)

When `CLAUDE_CONFIG_DIR` is unset:
- Global state: `$HOME/.claude.json` (exists, has `hasCompletedOnboarding: true`)
- Settings: `~/.claude/settings.json` (exists)

### Three blocking conditions with a fresh config dir

1. **Onboarding flow** (`showSetupScreens`):
   ```javascript
   let w = getGlobalConfig(); // reads .claude.json, defaults theme="dark"
   if (!w.theme || !w.hasCompletedOnboarding) {
     // Render Onboarding component — fetches feature flags from api.anthropic.com
   }
   ```
   With no `.claude.json`, `hasCompletedOnboarding` is absent (falsy). The Onboarding component contacts `api.anthropic.com` for Statsig feature flags **regardless of `ANTHROPIC_BASE_URL`**. On this machine, `api.anthropic.com` is unreachable → `ERR_BAD_REQUEST` → Claude Code exits.

2. **API key approval dialog**:
   ```javascript
   if (process.env.ANTHROPIC_API_KEY && !isMaxPlanUser()) {
     let truncated = truncateApiKey(process.env.ANTHROPIC_API_KEY); // last 20 chars
     if (getCustomApiKeyStatus(truncated) === "new") {
       // Render ApproveApiKey dialog — blocks waiting for user input
     }
   }
   ```
   With no `.claude.json`, the approved key list is empty → shows interactive dialog → blocks forever in tmux.

3. **Bypass-permissions confirmation**:
   ```javascript
   if (mode === "bypassPermissions" && !skipDangerousModePermissionPrompt()) {
     // Render BypassPermissionsModeDialog — blocks waiting for user input
   }
   ```
   Without `settings.json` containing `skipDangerousModePermissionPrompt: true` → shows dialog → blocks.

### Why the direct invocation test worked

The test in section 5 of the issue doc ran Claude Code without setting `CLAUDE_CONFIG_DIR`. Claude Code used the default `~/.claude/` config dir with the user's existing `$HOME/.claude.json` (which has `hasCompletedOnboarding: true` and the API key pre-approved).

### Why `claude-yunwu` also fails with a fresh config dir

Even though `claude-yunwu` uses `yunwu.ai` (directly reachable, no proxy needed), Claude Code's first-run onboarding contacts `api.anthropic.com` (hardcoded for feature flags), not the API base URL. So the relay doesn't help.

### Why the proxy hypothesis was wrong

The earlier fix (forwarding proxy env vars to the tmux session) was based on the observation that `api.anthropic.com` was unreachable. But the correct diagnosis is:

- `api.anthropic.com` is only contacted during **first-run initialization** (feature flag fetch)
- Normal API calls go to `ANTHROPIC_BASE_URL` (`yunwu.ai`), which is directly reachable
- The proxy fix doesn't help because the first-run init doesn't use `ANTHROPIC_BASE_URL`
- The correct fix is to skip the first-run init entirely by pre-seeding the config

## 3. Investigation Evidence

| Check | Result |
|-------|--------|
| Claude Code with default `~/.claude/` config | Works — reaches `❯` idle prompt |
| Claude Code with `CLAUDE_CONFIG_DIR=<fresh dir>` | Fails — `ERR_BAD_REQUEST` from `api.anthropic.com` |
| `claude-yunwu` with `CLAUDE_CONFIG_DIR=<fresh dir>` | Fails — same error (yunwu relay doesn't help first-run) |
| Fresh dir + `settings.json` + `.claude.json` with `firstStartTime` only | Fails — `hasCompletedOnboarding` still absent |
| `.claude.json` default config in source | `theme: "dark"` is a default — only `hasCompletedOnboarding` needs seeding |
| Claude Code `.claude.json` path resolution (from source) | `join(process.env.CLAUDE_CONFIG_DIR \|\| homedir(), ".claude.json")` |

## 4. Fix

### Primary: Pre-seed CLAUDE_CONFIG_DIR with minimum required state

**File:** `agents/brains/cli-configs/claude/default/settings.json` (NEW)

Added static settings file that gets copied into the fresh config dir during `build_brain_home()`:

```json
{
  "skipDangerousModePermissionPrompt": true
}
```

**File:** `src/agent_system_dissect/agents/brain_launch_runtime/backends/cao_rest.py`

Added `_seed_claude_home_config()` that writes `$CLAUDE_CONFIG_DIR/.claude.json` before the terminal is created:

```python
def _seed_claude_home_config(*, home_path: Path, env: dict[str, str]) -> None:
    claude_json_path = home_path / ".claude.json"
    if claude_json_path.exists():
        return

    state = {
        "hasCompletedOnboarding": True,
        "numStartups": 1,
    }

    api_key = env.get("ANTHROPIC_API_KEY", "")
    if api_key:
        suffix = api_key[-20:]  # Claude Code uses last 20 chars
        state["customApiKeyResponses"] = {
            "approved": [suffix],
            "rejected": [],
        }

    claude_json_path.write_text(json.dumps(state, indent=2) + "\n")
```

Called from `_start_terminal()` when `self._plan.tool == "claude"`.

### Secondary: Proxy/TLS env forwarding (retained from earlier fix)

`_forwarded_process_env()` still forwards proxy/TLS vars to the tmux session. This is a defensive measure for environments that require proxy access to reach the actual API endpoint. It was not the primary fix for this bug.

### Secondary: Error wrapping in REST client (retained)

`rest_client.py:_request_json()` catches `TimeoutError`/`OSError` and wraps in `CaoApiError`.

## 5. Test Impact

Added 3 new tests for `_seed_claude_home_config()`:
- `test_seed_claude_home_config_creates_claude_json` — verifies onboarding flag and API key suffix
- `test_seed_claude_home_config_skips_existing` — does not overwrite existing `.claude.json`
- `test_seed_claude_home_config_no_api_key` — works without API key (no `customApiKeyResponses`)

All 23 non-schema tests pass. The 2 pre-existing schema consistency test failures are unrelated.

## 6. Files Changed

| File | Change |
|------|--------|
| `agents/brains/cli-configs/claude/default/settings.json` | **NEW** — `skipDangerousModePermissionPrompt: true` |
| `src/agent_system_dissect/agents/brain_launch_runtime/backends/cao_rest.py` | Added `json` import, `_API_KEY_SUFFIX_LEN`, `_seed_claude_home_config()`, call from `_start_terminal()` for tool=claude |
| `tests/unit/agents/brain_launch_runtime/test_cao_client_and_profile.py` | Added 3 tests for config seeding |
| `context/issues/known/issue-cao-claude-code-init-timeout.md` | Updated root cause and resolution |

Files changed by the earlier proxy fix (retained):

| File | Change |
|------|--------|
| `src/agent_system_dissect/agents/brain_launch_runtime/backends/cao_rest.py` | `os` import, `_FORWARDED_ENV_NAMES`, `_forwarded_process_env()`, widened except clause |
| `src/agent_system_dissect/cao/rest_client.py` | `except (TimeoutError, OSError)` in `_request_json()` |
| `tests/unit/agents/brain_launch_runtime/test_cao_client_and_profile.py` | Env var assertion allows forwarded proxy vars |

## 7. Remaining Work

- **Verify end-to-end**: Re-run a maintained CAO interactive demo path to confirm the live Claude flow passes.
- **Headless backend**: The headless backend (`headless_base.py`) also sets `CLAUDE_CONFIG_DIR` to a fresh path. If it's used with Claude in non-pipe mode, the same issue would apply. Currently Claude headless uses `-p` (pipe mode) which likely skips setup screens, but this should be verified.
- **ANSI stripping**: The vendored fix in `claude_code.py` remains applied as a preventive measure.

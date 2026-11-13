# Claude Vendor Login Files

For contributors testing vendor-native login, use explicitly imported local state. Generic API cases use their selected key/base URL and require no vendor JSON. Native login does not inject DeepSeek routing.

## Discover and Import

```bash
pixi run python scripts/agents/test-fixtures/fixture.py discover-auth --client claude
pixi run python scripts/agents/test-fixtures/fixture.py import-auth --client claude --source /selected/claude-home --name work
```

Discovery checks the configured Claude home and standard local home, plus any explicitly supplied bounded search roots. It reads `.credentials.json` and supported companion `.claude.json` state. The default home's companion may live in its parent directory. Candidate output shows paths, filenames, auth kind, and importability without credential contents. It does not authenticate, refresh, or run helpers. Keychain-only, helper-only, malformed, and empty state remain explicit limitations.

Import requires an explicit source/candidate, preserves opaque file bytes, and leaves source files unchanged. It publishes a private bundle under `${XDG_DATA_HOME:-~/.local/share}/houmao/test-fixtures/auth/claude/NAME`; `--auth-root` overrides this outside the checkout. Replacing a name requires `--replace`. Never copy a full personal home or save native auth in tracked files.

## Prepare and Smoke

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prepare --client claude --auth-method native-login --auth-bundle work --mode headless --surface manager
pixi run python tests/manual/manual_claude_official_login_smoke.py --auth-bundle work
```

The smoke prepares a unique private external project, registers selected credentials and the smoke role through current project behavior, launches unattended headless, submits a short prompt, and stops the captured identity even on failure. The source home and reusable bundle remain unchanged. Real validation is optional and requires explicitly selected valid state; synthetic discovery/import/preparation coverage runs without personal login.

Read the [helper guide](../../scripts/agents/test-fixtures/README.md) for path overrides, supported auth shapes, and scoped follow-up. Claude state is tool-owned; preserve opaque fields rather than reconstructing a token document.

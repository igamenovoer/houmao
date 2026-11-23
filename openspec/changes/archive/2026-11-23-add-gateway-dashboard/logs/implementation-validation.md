# Implementation Validation

## Focused Regression and Packaging Checks

- 152 Pixi tests passed across gateway dashboard and entry, HTTP admission, interactive Web login, native Web observation and entry, DSH Web backend and client, passive-server observation, and the gateway Web entry command.
- Ruff lint and format checks passed for all seven changed Python files. Mypy passed for all five changed Python source files.
- The built wheel contains the dashboard renderer, HTML template, and DSH read-only probe.

## Live Browser Smoke

The maintained managed-agent fixture launched DSH 0.2.2-rc.5 and Kimi Code 2.7.2 in Web mode through the manager. Both runs selected the `self-hosted` case and `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1`. Each run used an isolated tmux socket with inherited tmux variables cleared. Each browser check used a fresh Playwright context in headless Chromium 156.0.8078.4.

| Agent and Roster | Result |
| --- | --- |
| DSH, empty | The owner-local dashboard returned HTTP 200 with `Cache-Control: no-store` and `Referrer-Policy: no-referrer`. The bare Web entry link returned HTTP 302. Chromium rendered the native DeepSeek Harness UI at the recorded origin. Selecting the managed session in the native sidebar marked that exact session as selected. The final URL contained no query or fragment. |
| Kimi Web, empty | The dashboard returned HTTP 200 with the expected headers. The bare Web entry link returned HTTP 302. Chromium opened the exact managed session with a visible composer and cleared the native authentication fragment. |
| Kimi Web, enrolled key | An unsigned browser opened the dashboard and followed the same link to the admin sign-in page. The generated terminal command used a temporary Ed25519 key to sign and submit proof. The original tab opened the exact managed session with a visible composer and a clean URL. |

The first DSH launch used the Bun executable symlink and failed before gateway startup because the native plugin could not resolve a DSH package. Preparing a fresh fixture with the resolved executable path fixed startup. A subsequent managed turn completed against the selected self-hosted model.

A fresh DSH fixture verified the dashboard's read-only native availability check. The same three `api-*.json` paths existed before and after opening the dashboard through curl and a clean browser context. The dashboard link still opened the native UI, where the exact managed session remained selectable.

The fixture stopped each launched agent. The gateway and native listeners closed, the isolated tmux servers exited, and the temporary signing key was removed.

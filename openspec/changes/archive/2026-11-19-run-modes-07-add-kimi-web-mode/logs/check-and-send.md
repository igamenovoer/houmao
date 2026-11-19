# Managed Kimi Web Verification

## Readiness and Native Identity

The user accepted the same check-and-send policy as managed TUI input. The revised proposal, design, spec, and tasks passed strict OpenSpec validation. The owner verifies the current host, listener, and session, checks native active and pending input, then sends one native POST. If the browser wins after that check, the managed request keeps the exact native queued receipt. The backend attributes settlement only to the original native prompt identity and reconciles a lost response without repeating the request.

Launch preflight selects installed Kimi Code `2.6.0`. The owner binds its private home and workspace and publishes the loopback origin and native session ID. Explicit browser opening uses a mode `0600` local bootstrap file. The fixture browser credential was private and the signed gateway, passive state, and usage output stayed token-free.

## Actual Model and Browser

Fixture `self-hosted-kimi-web-manager-d74753eee98a` launched the managed host and sent a signed prompt against `Qwen/Qwen3.8-27B-FP8`. The request completed on native turn `0` with 58 output tokens. Its scoped cleanup returned `stopped_owned_identity`.

Fixture `self-hosted-kimi-web-manager-fbdcc2860d36` launched the same installed binary and selected the same actual Qwen model. A loopback test proxy held the first browser request before forwarding it to the model so the concurrent gateway check was deterministic. The gateway refused the ordinary prompt with HTTP 409 while Chromium's native turn was active. The direct refusal never reached the provider. Gateway detach and reattach preserved the live host and conversation. Chromium displayed the browser answer and the signed gateway answer. The latter was attributed to native turn `2` in session `session_3ef2eae1-8abb-4d2b-ac57-5206bcee17e6`.

A direct manager prompt settled as native turn `3`. The signed passive API observed the same Web conversation and exact managed usage. Stop and explicit relaunch rotated the host incarnation and generation, then advanced the saved session to native turn `4`. Final fixture cleanup stopped only its owned identity.

The final live run used `self-hosted-kimi-web-manager-19575095b1ad` with native session `session_002128f3-4cbe-4eec-8f93-ead50cb2fb15`. It repeated the Chromium busy rejection, gateway reattachment, shared browser and gateway answers, and direct manager turn. Signed AG-UI emitted the exact assistant reply and `RUN_FINISHED` for native turn `4`. The signed passive API verified the same session and the exact usage row. Explicit relaunch created a new host incarnation and generation and continued at native turn `5`. Scoped cleanup returned `stopped_owned_identity`.

The initial private browser fixture restored roles from input assets. It now uses the compiled agent-definition directory recorded in the runtime manifest. A separate AG-UI run found that Kimi stores the outer native turn ordinal as an integer and the nested assistant event's ordinal as a string. Normalizing those exact ordinals restored the missing assistant text in the final live run.

An actual interrupt test on fixture `self-hosted-kimi-web-manager-1eb5b8070d0e` stopped native turn `0`, then completed a separate managed request on turn `1` without replacing the host. An earlier probe found that installed Kimi returns an error envelope for a native abort POST with an empty JSON body. The request now sends an explicit empty JSON object. The seven provider tests and the live abort passed after that correction.

## Regression Tests

The first parallel integration run passed 49 cases and hit tmux's Unix socket path-length limit in an existing fixture test. The same 50 cases passed with a shorter isolated pytest base directory. The main provider tests cover the post-check browser win, exact receipt publication, passive reads, known-busy refusal, lost response reconciliation, stale abort, and wrong-listener refusal without token transmission.

The backend batch passed seven cases. The gateway, Web observation, admission, passive, and AG-UI batch passed 218 cases with one skip. The broader launch/runtime/manifest/CLI batch passed 341 cases with 13 skips. The first full unit run exposed DSH fixture and Kimi launch-policy changes, which the focused reruns covered after fixes. Ruff, strict mypy, and the documentation build passed.

The full isolated Pixi unit suite passed 4,944 tests with 14 skips. After the live abort test correction, the focused provider batch, lint, and strict mypy passed again. The wheel and source distribution built during verification and passed Twine checks. Strict OpenSpec validation and `git diff --check` passed.

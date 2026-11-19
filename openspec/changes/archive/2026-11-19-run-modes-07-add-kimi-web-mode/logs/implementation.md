# Implementation and Verification

## Revised Readiness Policy

The user selected the same readiness policy as managed TUI input. The current OpenSpec change requires one final check and one native send. A browser can win after the check, and the gateway preserves the returned queued receipt. The earlier rejection of managed Web launches applied to the initial atomic admission requirement. [Current implementation and tests](check-and-send.md).

## Review After Change 06

The shared service supervisor protects a provider that receives input only through one private stdio connection. Kimi Web has independent native browser submission and control, so browser input must participate at the native commit boundary. Houmao's owner reservation alone cannot enforce that condition.

The local reference is Kimi source `67325c1`. The installed executable tested for this change is Kimi Code `2.6.0`. The KAP prompt handler resolves or activates the session, prepares input, modifies selected settings, and unconditionally calls `submit`. Its ready snapshot determines whether it waits for launch. The engine quiescence lease pauses scheduling and continues to accept queue entries. The native WebSocket interface observes prompt effects. The REST prompt listing itself can activate a cold session. The CLI exposes no native conditional submission switch or installed extension hook. [Prompt route](../../../../extern/orphan/kimi-code/packages/kap-server/src/routes/prompts.ts), [Web CLI](../../../../extern/orphan/kimi-code/apps/kimi-code/src/cli/sub/web/run.ts), [Native server options](../../../../extern/orphan/kimi-code/packages/kap-server/src/start.ts).

## Initial Launch Refusal

Managed Kimi launches with `--mode web` require native ready-only admission that coordinates with the browser before session activation, settings changes, file staging, or queue insertion. The resolver reports the missing capability before execution takeover or browser handoff. It lists Kimi `headless`, `service`, and `tui` as available selections.

The actual manager fixture `self-hosted-kimi-service-manager-6fd5400d7ac5` attempted `project agents launch --mode web --force keep-stale` against the same private live Kimi ACP agent. The command failed with the conditional admission diagnostic and published no additional runtime manifest or browser surface. The existing native PID `4108104`, saved owner generation, and service incarnation matched the original descriptor. A follow-up manager prompt completed on the existing Qwen service. Scoped cleanup stopped the captured owner.

The resolver, direct runtime, project launch, and fixture preflight batch passed 24 cases. [Launch selection verification](selection-verification.md).

## Stock Native Admission

On the installed Web binary, the authenticated stock prompt endpoint returned HTTP 200 and `queued` for a competing submission while the first Qwen call was held. It created a pending native request. When the held call finished, the queued prompt ran against the same Qwen model and the private native journal recorded both distinct completions. The stock HTTP and browser behavior prevents the immediate-delivery guarantee from applying to this build. [Installed native admission verification](native-admission.md).

Chromium submitted a real native browser prompt against the same selected Qwen model. A competing native REST submission queued while that browser turn was active. The native journal later recorded both distinct turns and their individual usage, and Chromium displayed the second answer. This verified the stock browser race on the installed binary. [Browser verification](browser.md).

## Initial Atomic Admission Requirement

The initial design required a conditional operation recognized by all native submitters. The proposed native boundary would validate the exact host and session, revocable dispatch permission, and an idle queue before effects. Those requirements blocked managed Web on the installed build until the user selected the TUI readiness policy.

The native instance descriptor and authenticated `meta` route generate separate server IDs. A future owner needs to establish each identifier against the verified process and listener. The native `--no-open` option still writes the bearer to its startup banner, which the qualification probes captured in private files.

## Final Workspace Verification

`pixi run test` passed 4,925 tests with 14 skips on an isolated tmux server. The initial run caught a fixture assertion in the wrong test during editing. The full rerun passed after the assertion returned to its original test.

Ruff, strict mypy for 518 source files, the documentation build, and `git diff --check` passed. All seven numbered changes passed strict OpenSpec artifact validation. The wheel and source distribution built successfully in a private build environment and passed Twine checks. The wheel contains the service owner, DSH companion, Kimi ACP and Codex app-server providers, and current manifest and locator schemas.

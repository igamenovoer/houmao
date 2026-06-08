## Context

Houmao already supports Kimi Code through the `kimi_headless` backend and launch-policy registry, but `local_interactive` currently only admits Claude Code, Codex, and Gemini as maintained TUI tools. The shared TUI tracking core is provider-neutral, but provider admission, process liveness, parser sidecar state, and signal profiles still need explicit Kimi support.

The local Kimi Code source under `extern/orphan/kimi-code` at `f09ec7bbb59af42805a93df2993301dbd317ff2d` shows that the TUI accepts normal input, bracketed paste, Enter submission, Escape cancellation, session resume options, and model selection through `--model`. The installed `/home/huangzhe/.kimi-code/bin/kimi` reports version `0.11.0`. A live tmux probe confirmed the process command name is `kimi-code`, prompt submission works through bracketed paste plus Enter, approval prompts are visible and parseable, and Kimi may run an update preflight before or during startup.

Kimi source inspection also tightens the launch contract. Current Kimi rejects non-prompt TUI resume startup when `--continue` or `--session` is combined with `--yolo`, `--auto`, or `--plan`, while `--model` remains valid and is applied after resume. Current Kimi consumes `--skills-dir` in prompt mode, not the TUI path. Kimi documents `KIMI_CODE_NO_AUTO_UPDATE` and legacy `KIMI_CLI_NO_AUTO_UPDATE` as full update-preflight disable switches.

The current server/gateway tracking path still exposes good operator state only when the tool is considered supported by process inspection and parser sidecar code. A shared detector alone would not be enough because unsupported-tool diagnostics would still hide readiness and approval-blocked state from operator-facing APIs.

## Goals / Non-Goals

**Goals:**

- Launch Kimi Code as a maintained `local_interactive` TUI provider.
- Preserve Kimi headless prompt-mode behavior as a separate backend.
- Track Kimi TUI readiness, active turns, completed turns, approval prompts, and supported process liveness from tmux snapshots.
- Reuse existing semantic prompt submission, raw control input, Escape interrupt, tmux primary surface, and gateway-owned tracking patterns.
- Support Kimi provider-native relaunch selectors for fresh, latest-chat, and exact-session modes.
- Apply launch-owned Kimi model selection to TUI startup with `--model <alias>`.
- Suppress Kimi update preflight for managed TUI launches with `KIMI_CODE_NO_AUTO_UPDATE=1`.
- Add focused fixture and live-probe coverage for parser and detector behavior.

**Non-Goals:**

- Do not replace the shared TUI tracking engine.
- Do not route Kimi TUI through the Claude/Codex shadow parser stack.
- Do not rename `kimi_headless` or change existing Kimi prompt-mode output parsing.
- Do not add pi-tui as a runtime dependency for Houmao.
- Do not project managed `--skills-dir` arguments into Kimi TUI launches until Kimi exposes a maintained TUI skills-dir mechanism.
- Do not make terminal recorder Kimi replay analysis part of the first implementation slice.

## Decisions

### Use a Kimi-specific visible-surface parser

Kimi shall get a parser adapter path that reads captured visible pane text and produces `HoumaoParsedSurface` directly. That parser should set supported availability, business state, input mode, UI context, dialog text, normalized text, and operator-blocking excerpts for approval prompts.

Alternative considered: add only a shared detector profile. That would reduce turn state internally, but server and gateway diagnostics would still classify Kimi as unsupported in parser-owned surfaces. Operator state would remain degraded.

Alternative considered: force Kimi into the existing Claude/Codex shadow parser stack. Kimi's pi-tui surface, prompt box, footer, and approval panels differ enough that a direct parser is simpler and less coupled.

### Add `kimi_code` as the tracker app id

The shared TUI profile registry shall map `tool="kimi"` to a TUI surface-family app id named `kimi_code`. This mirrors `codex_tui` and keeps backend names such as `kimi_headless` out of tracker profile identity.

The maintained Kimi profile should cover the source-backed `0.11.x` surface family with semver-compatible floor resolution where safe. Older or later Kimi surface families should only become maintained profiles when labeled corpus evidence exists for those versions. The detector must treat footer text such as `Kimi-k2.6 thinking` as model metadata rather than active-turn evidence.

### Extend `local_interactive` provider admission

Kimi shall be admitted through the existing `local_interactive` runtime path when the user prefers local interactive launch. Process inspection allowlists must include both `kimi-code` and `kimi` because the live process reports `kimi-code` even though the executable path is `kimi`.

Relaunch argument mapping shall be:

- `new`: no Kimi session args
- `tool_last_or_new`: `kimi --continue`
- `exact`: `kimi --session <session_id>`

The runtime shall not use bare `--session`, because Kimi treats that as an interactive session picker. When relaunch resumes a Kimi session through `--continue` or `--session <id>`, the implementation shall reject final launch arguments that also contain `--yolo`, `--auto`, or `--plan`. Silently removing those flags would change the operator's permission posture, so a clear launch error is safer. `--model <alias>` is allowed on resume and should remain part of launch-owned model projection.

Semantic prompt submission shall reuse the existing bracketed-paste and final-submit strategy. Interrupt shall continue using Escape as the primary cancellation key because Kimi source and live behavior show Escape cancels streaming or modal surfaces without triggering the double Ctrl+C exit path.

### Keep Kimi TUI launch policy conservative

Kimi headless has a maintained unattended prompt-mode strategy. Kimi TUI should initially be supported for interactive/as-is launch and explicit managed prompt control. If unattended TUI launch is requested, implementation should either add a separate raw-launch Kimi strategy after validating `--auto` or fail explicitly instead of borrowing the headless prompt-mode strategy.

Kimi's update preflight is a startup reproducibility risk. Managed Kimi TUI launches should set `KIMI_CODE_NO_AUTO_UPDATE=1` in the launched process environment, because current Kimi source documents that switch as disabling update checks, background installs, and prompts. The legacy `KIMI_CLI_NO_AUTO_UPDATE` alias can be tolerated when already supplied, but Houmao should project the current `KIMI_CODE_NO_AUTO_UPDATE` spelling.

Current Kimi source parses `--skills-dir` as a CLI option but passes it to the prompt-mode harness only. Local interactive Kimi launch should not add managed `--skills-dir` arguments or claim TUI skills-dir support. Existing Kimi headless skills behavior remains separate.

### Test from fixtures before depending on live recorder replay

Parser and detector tests shall use captured Kimi text fixtures for idle, active, completed, approval, and rejected-tool surfaces. A live smoke test can validate installed Kimi behavior when credentials are available, but unit tests must stay deterministic.

The terminal recorder currently exits too early in the observed Kimi probe and only exposes Claude/Codex analysis choices. Kimi recorder support can follow after the parser and detector have stable fixtures.

## Risks / Trade-offs

- Kimi surface drift between `0.11.x` and later versions -> keep Kimi patterns bounded to prompt, activity, approval, and current-turn regions, then add profile versions as drift appears.
- Kimi TUI resume rejects `--yolo`, `--auto`, and `--plan` when used with `--continue` or `--session` -> validate and fail clearly rather than starting a provider process that exits immediately.
- Footer `thinking` text could create false active states -> explicitly ignore footer model metadata and require current activity rows, tool panels, response growth, or temporal evidence.
- Auto-update may change behavior during startup -> project `KIMI_CODE_NO_AUTO_UPDATE=1` for managed launches and keep tests fixture-based.
- Kimi TUI skills-dir behavior is not source-backed -> keep managed skills-dir projection headless-only until upstream TUI support exists.
- Approval rejection looks failure-like but can end as a normal assistant response -> track approval-blocked state while the dialog is present and avoid publishing `known_failure` after rejection unless Kimi shows a bounded terminal failure surface.
- Adding Kimi to process allowlists without parser support would expose unsupported diagnostics -> ship process admission, parser support, and signal profile registration together.

## Migration Plan

No stored-data migration is required. Existing Kimi headless sessions and manifests remain valid. After implementation, new or relaunched Kimi TUI sessions can use `local_interactive`; existing unsupported Kimi TUI sessions may need relaunch or join to pick up the new process and profile metadata.

Rollback is straightforward: remove Kimi from local interactive admission and process allowlists, leaving `kimi_headless` behavior unchanged.

## Open Questions

- Should Kimi TUI unattended mode use `--auto`, `--yolo`, or remain unsupported until a separate launch-policy strategy is proven?
- Should terminal recorder add Kimi replay analysis in the same release train after parser fixtures land, or remain a follow-up capability?

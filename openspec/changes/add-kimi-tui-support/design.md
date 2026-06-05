## Context

Houmao already supports Kimi Code through the `kimi_headless` backend and launch-policy registry, but `local_interactive` currently only admits Claude Code, Codex, and Gemini as maintained TUI tools. The shared TUI tracking core is provider-neutral, but provider admission, process liveness, parser sidecar state, and signal profiles still need explicit Kimi support.

The local Kimi Code source under `extern/orphan/kimi-code` shows that the TUI accepts normal input, bracketed paste, Enter submission, Escape cancellation, session resume options, and model selection through `--model`. A live tmux probe against `/home/huangzhe/.kimi-code/bin/kimi` confirmed the process command name is `kimi-code`, prompt submission works through bracketed paste plus Enter, approval prompts are visible and parseable, and Kimi may run an update preflight before or during startup. The installed CLI updated from `0.10.1` to `0.11.0` during the probe.

The current server/gateway tracking path still exposes good operator state only when the tool is considered supported by process inspection and parser sidecar code. A shared detector alone would not be enough because unsupported-tool diagnostics would still hide readiness and approval-blocked state from operator-facing APIs.

## Goals / Non-Goals

**Goals:**

- Launch Kimi Code as a maintained `local_interactive` TUI provider.
- Preserve Kimi headless prompt-mode behavior as a separate backend.
- Track Kimi TUI readiness, active turns, completed turns, approval prompts, and supported process liveness from tmux snapshots.
- Reuse existing semantic prompt submission, raw control input, Escape interrupt, tmux primary surface, and gateway-owned tracking patterns.
- Support Kimi provider-native relaunch selectors for fresh, latest-chat, and exact-session modes.
- Apply launch-owned Kimi model selection to TUI startup with `--model <alias>`.
- Add focused fixture and live-probe coverage for parser and detector behavior.

**Non-Goals:**

- Do not replace the shared TUI tracking engine.
- Do not route Kimi TUI through the Claude/Codex shadow parser stack.
- Do not rename `kimi_headless` or change existing Kimi prompt-mode output parsing.
- Do not add pi-tui as a runtime dependency for Houmao.
- Do not make terminal recorder Kimi replay analysis part of the first implementation slice.

## Decisions

### Use a Kimi-specific visible-surface parser

Kimi shall get a parser adapter path that reads captured visible pane text and produces `HoumaoParsedSurface` directly. That parser should set supported availability, business state, input mode, UI context, dialog text, normalized text, and operator-blocking excerpts for approval prompts.

Alternative considered: add only a shared detector profile. That would reduce turn state internally, but server and gateway diagnostics would still classify Kimi as unsupported in parser-owned surfaces. Operator state would remain degraded.

Alternative considered: force Kimi into the existing Claude/Codex shadow parser stack. Kimi's pi-tui surface, prompt box, footer, and approval panels differ enough that a direct parser is simpler and less coupled.

### Add `kimi_code` as the tracker app id

The shared TUI profile registry shall map `tool="kimi"` to a TUI surface-family app id named `kimi_code`. This mirrors `codex_tui` and keeps backend names such as `kimi_headless` out of tracker profile identity.

The first maintained profiles should cover the observed `0.10.x` and `0.11.x` surface families with semver-compatible floor resolution where safe. The detector must treat footer text such as `Kimi-k2.6 thinking` as model metadata rather than active-turn evidence.

### Extend `local_interactive` provider admission

Kimi shall be admitted through the existing `local_interactive` runtime path when the user prefers local interactive launch. Process inspection allowlists must include both `kimi-code` and `kimi` because the live process reports `kimi-code` even though the executable path is `kimi`.

Relaunch argument mapping shall be:

- `new`: no Kimi session args
- `tool_last_or_new`: `kimi --continue`
- `exact`: `kimi --session <session_id>`

Semantic prompt submission shall reuse the existing bracketed-paste and final-submit strategy. Interrupt shall continue using Escape as the primary cancellation key because Kimi source and live behavior show Escape cancels streaming or modal surfaces without triggering the double Ctrl+C exit path.

### Keep Kimi TUI launch policy conservative

Kimi headless has a maintained unattended prompt-mode strategy. Kimi TUI should initially be supported for interactive/as-is launch and explicit managed prompt control. If unattended TUI launch is requested, implementation should either add a separate raw-launch Kimi strategy after validating `--auto` or fail explicitly instead of borrowing the headless prompt-mode strategy.

Kimi's update preflight is a startup reproducibility risk. The implementation should inspect and, if available, use a supported configuration or environment surface to suppress update prompts for managed launches. If no such surface is maintained, the implementation should report that risk in diagnostics and tests should avoid depending on a fixed patch version.

### Test from fixtures before depending on live recorder replay

Parser and detector tests shall use captured Kimi text fixtures for idle, active, completed, approval, and rejected-tool surfaces. A live smoke test can validate installed Kimi behavior when credentials are available, but unit tests must stay deterministic.

The terminal recorder currently exits too early in the observed Kimi probe and only exposes Claude/Codex analysis choices. Kimi recorder support can follow after the parser and detector have stable fixtures.

## Risks / Trade-offs

- Kimi surface drift between `0.10.x`, `0.11.x`, and later versions -> keep Kimi patterns bounded to prompt, activity, approval, and current-turn regions, then add profile versions as drift appears.
- Footer `thinking` text could create false active states -> explicitly ignore footer model metadata and require current activity rows, tool panels, response growth, or temporal evidence.
- Auto-update may change behavior during startup -> document and probe Kimi update controls before implementation, then keep tests fixture-based.
- Approval rejection looks failure-like but can end as a normal assistant response -> track approval-blocked state while the dialog is present and avoid publishing `known_failure` after rejection unless Kimi shows a bounded terminal failure surface.
- Adding Kimi to process allowlists without parser support would expose unsupported diagnostics -> ship process admission, parser support, and signal profile registration together.

## Migration Plan

No stored-data migration is required. Existing Kimi headless sessions and manifests remain valid. After implementation, new or relaunched Kimi TUI sessions can use `local_interactive`; existing unsupported Kimi TUI sessions may need relaunch or join to pick up the new process and profile metadata.

Rollback is straightforward: remove Kimi from local interactive admission and process allowlists, leaving `kimi_headless` behavior unchanged.

## Open Questions

- Which Kimi-owned config or environment surface, if any, disables update preflight for managed launches?
- Should Kimi TUI unattended mode use `--auto`, `--yolo`, or remain unsupported until a separate launch-policy strategy is proven?
- Should terminal recorder add Kimi replay analysis in the same release train after parser fixtures land, or remain a follow-up capability?

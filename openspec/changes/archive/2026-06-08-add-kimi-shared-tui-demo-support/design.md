## Context

The shared TUI tracking demo pack already supports two important workflows for Claude and Codex: a live watch dashboard driven by tmux pane evidence, and recorded capture / replay validation against human-authored public-state labels. Kimi Code now has a `kimi_code` shared tracker profile and source-backed signal contract from `capture-kimi-tui-signals`, but the demo pack still hard-codes Claude and Codex in its type aliases, CLI choices, config schema, launch assets, auth projection, process detection, and scenario set.

The broader `add-kimi-tui-support` change still owns full managed-agent `local_interactive` Kimi support. This change is deliberately narrower: make the standalone demo pack able to launch and inspect a real Kimi Code TUI session through the shared tracker so maintainers can manually verify readiness, active turns, approvals, interruption, footer metadata, and process diagnostics before wiring Kimi into server and gateway surfaces.

## Goals / Non-Goals

**Goals:**

- Add Kimi as a supported tool in the shared TUI tracking demo pack.
- Preserve the demo pack's standalone architecture: tmux observation, optional recorder capture, scenario driving, replay validation, and public-state comparison.
- Add Kimi demo-local launch assets and host-local auth alias materialization without committing Kimi secrets.
- Add Kimi version/process recognition for `kimi` and `kimi-code`.
- Add focused Kimi live and recorded scenarios for manual inspection of the existing `kimi_code` detector.
- Keep Kimi fixture validation and future corpus validation first-class once Kimi recordings are authored.

**Non-Goals:**

- Do not implement full managed-agent `local_interactive` Kimi support in this change.
- Do not add a Kimi official parser sidecar for `HoumaoParsedSurface`; that remains part of `add-kimi-tui-support`.
- Do not modify the `kimi_code` detector heuristics unless demo inspection exposes a concrete defect.
- Do not commit real Kimi credentials, OAuth tokens, or user-global Kimi state.
- Do not require a committed Kimi recorded corpus before live manual inspection works.

## Decisions

### Admit Kimi through the demo's existing tool catalog

The demo should extend the current `ToolName` catalog from `claude | codex` to `claude | codex | kimi` and let the existing workflow modules continue to dispatch by tool. This includes CLI choices, boundary models, config parsing, generated schema, run manifests, fixture manifests, sweep inference, and tests.

Alternative considered: add a separate Kimi-only demo command. That would duplicate live watch and recorded validation logic and make future tracker comparisons harder. The existing demo pack is already tool-parametric enough that Kimi should enter the same catalog.

### Reuse the existing tracker registry path

Recorded scenario execution already resolves the detector through `app_id_from_tool(tool=<tool>)`; for Kimi this resolves to `kimi_code`. The demo should continue using this path instead of importing Kimi detector classes directly.

Alternative considered: instantiate `KimiCodeSignalDetectorV0_11_X` directly in the demo. That would hide version-profile selection issues and bypass the same registry contract used by replay and live tracker sessions.

### Add Kimi demo-local launch assets from existing Kimi adapter patterns

The demo should add `inputs/agents/tools/kimi/adapter.yaml`, a default setup directory, and `interactive-watch-kimi-default.yaml`. The adapter should match the current Kimi brain-builder contract: `KIMI_CODE_HOME`, executable `kimi`, Kimi file mappings for `config.toml` and `credentials/kimi-code.json`, Kimi env allowlist, and home-relative `skills`.

Alternative considered: launch `/home/huangzhe/.kimi-code/bin/kimi` directly from the demo. That would make the checked-in demo host-specific. Operators may still override paths through auth bundles or recipe/config inputs, but the maintained assets should stay portable.

### Use a host-local Kimi auth bundle convention

The demo should expect a local Kimi auth fixture such as `tests/fixtures/auth-bundles/kimi/personal-a-default/`, with secret-bearing contents ignored by git. The generated run-local agent tree should materialize `tools/kimi/auth/default` to that source, the same way Claude and Codex use host-local fixture bundles. Documentation should explain how to populate the bundle from an existing Kimi Code home, usually by copying `config.toml`, `credentials/kimi-code.json`, and optional env values into the expected auth-bundle shape.

Alternative considered: symlink the demo directly to `$HOME/.kimi-code`. That is convenient for one host but too implicit for a maintained demo and makes the run harder to reproduce or inspect.

### Keep scenario control simple and Kimi-specific where needed

Kimi interruption should use Escape, consistent with the Kimi signal investigation and broader Kimi TUI design. Kimi process diagnostics should match both `kimi-code` and `kimi`. The first scenario wave should cover the states from the Kimi signal contract: ready/success, active interruption, approval rejection, footer thinking metadata, and TUI process loss.

Alternative considered: port all Claude/Codex complex scenarios immediately. That would slow down the first manual inspection loop. The first Kimi wave should answer whether the current detector behaves correctly on the highest-value Kimi surfaces before expanding into repeated-turn stress cases.

### Treat Kimi recorded corpus as future-authored evidence

The demo should support Kimi fixtures and `recorded-validate --tool kimi` immediately, but it should not require a committed Kimi corpus to complete the extension. Corpus-oriented commands should continue failing clearly when no fixture manifests exist.

Alternative considered: make this change also commit full Kimi fixtures. The prior Kimi capture artifacts live under exploratory `tmp/` paths and OpenSpec context; turning them into canonical fixtures needs a separate authoring and label-review pass.

## Risks / Trade-offs

- [Risk] Kimi startup update preflight can delay or alter visible startup state. -> Mitigation: keep live watch manual-first, document the risk, and avoid tests that depend on a fixed Kimi patch version.
- [Risk] Host-local Kimi auth bundles are absent on clean checkouts. -> Mitigation: fail before launch with a concrete missing-path error and document how to populate the bundle.
- [Risk] Kimi approval scenarios may be sensitive to shell permissions and working directory. -> Mitigation: keep scenario prompts narrow and allow scenario-specific waits/patterns rather than broad exact transcript checks.
- [Risk] Adding Kimi to the demo could be mistaken for full managed Kimi TUI support. -> Mitigation: keep docs explicit that this demo validates standalone tracker behavior only.
- [Risk] The current Kimi detector may not expose parser-facing sidecar fields in this demo. -> Mitigation: compare public tracked state in this change; parser sidecar coverage remains in the broader Kimi support change.

## Migration Plan

No stored data migration is required. Existing Claude and Codex demo runs, configs, and fixtures remain valid.

Implementation can land incrementally:

1. Extend the demo tool catalog, schema, and config to include Kimi.
2. Add Kimi launch assets and auth-bundle projection.
3. Add Kimi version/process detection and scenario control tables.
4. Add Kimi scenarios and docs for live manual inspection.
5. Extend tests for Kimi asset materialization, config parsing, CLI choices, and replay validation entry points.

Rollback removes Kimi from the demo catalog and leaves existing Claude/Codex demo behavior unchanged.

## Open Questions

- Should the maintained Kimi auth bundle default be `personal-a-default` or another fixture name that matches existing credential naming conventions?
- Should Kimi approval scenarios create their own temporary command target, or should they use a prompt that reliably asks Kimi to run a harmless shell command?

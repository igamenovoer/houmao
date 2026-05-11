## Context

Issue #60 reports that launch-profile `defaults.env` records, especially proxy variables such as `http_proxy` and `https_proxy`, are not visible to Codex when it starts as a local interactive TUI inside a Houmao-managed tmux session.

The intended path already spans several layers:

```text
project easy profile create --env-set
  -> project catalog launch profile env_payload
  -> project easy instance launch --profile
  -> BuildRequest.persistent_env_records
  -> brain manifest runtime.launch_contract.env_records
  -> LaunchPlan.env
  -> tmux session environment
  -> Codex TUI process
```

Existing tests cover pieces of that path, but not the user-facing sequence reported in the issue: create an easy profile with env records, launch a Codex TUI agent from that profile, and inspect the live tmux session/provider process for those env values.

## Goals / Non-Goals

**Goals:**

- Add HTT-ready regression coverage for the full easy-profile-backed Codex TUI env propagation path.
- Verify durable env records created through `project easy profile create --env-set NAME=value` are visible inside the launched tmux session.
- Keep the test deterministic and offline by using a fake Codex executable or controlled provider command instead of contacting OpenAI.
- Make failures localize the broken hop: profile storage, manifest/launch-plan composition, tmux environment publication, or provider process inheritance.

**Non-Goals:**

- Reworking launch-profile storage, CLI UX, or env precedence unless tests expose a real defect.
- Requiring live OpenAI connectivity or real Codex authentication for the regression.
- Testing credential-owned env such as `OPENAI_API_KEY`; this change targets non-secret launch-profile env records.
- Treating manual edits to projected `.houmao/agents/launch-profiles/<name>.yaml` as authoritative unless a separate change adds an import/edit contract.

## Decisions

### Decision: Test through the easy-profile public CLI path

The primary regression should create state with `houmao-mgr project easy profile create --env-set`, not by directly inserting catalog rows or writing projected YAML.

Rationale:
- The issue is operator-facing, so the test should start from the maintained operator surface.
- This verifies parsing, validation, catalog persistence, and profile-backed launch resolution together.

Alternative considered:
- Seed `LaunchProfileCatalogEntry` directly in a unit test. Rejected for the primary case because it skips the path that users actually exercise.

### Decision: Use a fake Codex executable for the provider process assertion

The test should put a fake `codex` executable earlier on `PATH`. That executable should capture selected env values to an output file and remain alive long enough for Houmao's local interactive readiness checks to observe a Codex-named process or controlled TUI surface.

Rationale:
- It proves the final provider process environment without requiring network access, real Codex auth, or actual model startup.
- It can assert exact env values such as `http_proxy=http://127.0.0.1:7990`, `https_proxy=http://127.0.0.1:7990`, and `FEATURE_FLAG_X=profile`.

Alternative considered:
- Launch the real Codex CLI and inspect `env | grep proxy` manually through tmux. Rejected for automated regression because it depends on live credentials, network, and upstream TUI behavior.

### Decision: Assert both tmux session env and provider-observed env when practical

The regression should prefer two observations:

1. `tmux show-environment -t <session>` contains the profile env records.
2. The fake Codex process records the same env values from its inherited process environment.

Rationale:
- If only tmux session env is correct, provider startup inheritance may still be broken.
- If only provider output is checked, failures can be harder to diagnose.

Alternative considered:
- Check only the brain manifest or launch plan. Rejected because #60 specifically reports the final tmux/Codex surface, not intermediate metadata.

### Decision: Keep the profile env values non-secret and proxy-shaped

The test values should include realistic lowercase proxy names plus one uppercase sentinel:

- `http_proxy=http://127.0.0.1:7990`
- `https_proxy=http://127.0.0.1:7990`
- `FEATURE_FLAG_X=profile-env`

Rationale:
- The proxy names match the reported failure.
- The uppercase sentinel helps distinguish general env propagation from lowercase-specific handling.

Alternative considered:
- Use auth or model env names. Rejected because credential-owned names have separate validation and precedence rules.

## Risks / Trade-offs

- [Risk] A fake Codex executable might not satisfy the same readiness checks as the real TUI. -> Mitigation: design the fake process to have `argv0`/command name `codex` and emit a simple stable prompt-like surface if the existing tracker needs visible readiness.
- [Risk] Tmux-based tests can be flaky on hosts without tmux. -> Mitigation: skip clearly when `tmux` is unavailable, matching existing tmux-backed runtime test posture.
- [Risk] The test may initially reveal that projected YAML edits are not authoritative. -> Mitigation: keep this change scoped to CLI-created profiles and document projected-YAML authority as out of scope.
- [Risk] Profile env could be present in tmux session env but lost during relaunch. -> Mitigation: first cover fresh launch for #60; relaunch coverage can be added if the implementation change touches relaunch behavior.

## Migration Plan

No data migration is required. This change adds regression tests and clarifies expected behavior around existing launch-profile env records.

Rollback is removing the tests/spec delta if the project intentionally changes launch-profile env semantics in a future design.

## Open Questions

None for the proposed test coverage. The implementation phase can choose the exact fake-Codex harness location based on nearby runtime test patterns.

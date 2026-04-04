## Context

Houmao already supports Gemini headless runtime construction, OAuth or API-key startup, exact `session_id` resume, and Gemini skill projection under `.agents/skills`. Those lower-level pieces were completed in the archived Gemini headless runtime change, but the maintained operator-facing stack still stops short of treating Gemini as a supported unattended lane.

Today the remaining gap is split across three layers:

- the launch-policy registry has no Gemini unattended strategy family, so `operator_prompt_mode: unattended` has no maintained Gemini path;
- `houmao-mgr project easy specialist create --tool gemini` still defaults to `launch.prompt_mode: as_is`;
- the supported `single-agent-gateway-wakeup-headless` demo and its spec intentionally exclude Gemini and only claim Claude and Codex.

The resulting inconsistency is that Houmao can run Gemini headless reliably in narrow runtime-oriented flows, but the maintained easy-specialist and demo workflows cannot honestly claim Gemini support yet.

## Goals / Non-Goals

**Goals:**

- Add a maintained Gemini unattended strategy family for the `gemini_headless` backend.
- Make Gemini part of the maintained `project easy` unattended path while keeping Gemini restricted to headless launch surfaces.
- Expand the supported `single-agent-gateway-wakeup-headless` demo from two maintained lanes to three.
- Reuse the already-implemented Gemini headless auth/runtime contract rather than introducing a second Gemini-specific startup path.
- Add regression coverage that proves the maintained operator contract, not just the low-level runtime behavior.

**Non-Goals:**

- Add Gemini TUI support or any non-headless Gemini `project easy` workflow.
- Redesign the generic launch-policy engine or registry schema.
- Introduce new Gemini auth families beyond the already-supported API-key and OAuth lanes.
- Rework the demo into a generic multi-pack abstraction shared with unrelated demos.
- Add new provider-wide UX beyond what is required to make Gemini a maintained unattended lane.

## Decisions

### 1. Treat Gemini unattended support as a positive maintained contract, not a demo-local exception

This change will make Gemini unattended startup a maintained platform capability first, then consume that capability from `project easy` and the demo pack.

Why:

- The demo already requires unattended launch posture as part of its maintained contract.
- Adding Gemini directly to the demo without a maintained upstream unattended contract would overstate platform support.
- The runtime, project-easy CLI, and demo docs can stay coherent only if they all depend on the same positive Gemini unattended contract.

Alternatives considered:

- Patch the demo to special-case Gemini while leaving the platform contract unchanged.
  Rejected because it would create a supported demo lane backed by unsupported platform posture.

### 2. Add a Gemini unattended registry strategy instead of inventing a separate project-easy-only startup path

Gemini will join the existing versioned launch-policy registry alongside Claude and Codex. The Gemini unattended strategy will remain runtime-owned, version-scoped, and evidence-backed like the other tools.

Implementation will start from the minimal hypothesis that Gemini unattended startup works on a fresh managed home with env and CLI-arg control alone. The implementation should only add `gemini.*` provider hooks or Gemini-owned startup file mutations if live testing shows that zero hooks and zero owned config/state paths are insufficient.

The Gemini registry lower bound will be pinned to the Gemini CLI version that is actually validated during implementation and recorded as live-probe evidence, rather than guessed in advance inside this design.

Why:

- The registry is already the canonical place where maintained unattended startup compatibility is declared.
- The fail-closed behavior for unsupported versions/backends already exists in the runtime and should remain the same for Gemini.
- Reusing the registry avoids splitting responsibility between runtime launch and `project easy` command-specific logic.

Alternatives considered:

- Teach `project easy specialist create` or `project easy instance launch` to inject Gemini-specific unattended behavior without registry coverage.
  Rejected because startup-prompt suppression belongs to runtime launch policy, not to one CLI surface.

### 3. Keep Gemini's unattended contract headless-only on the easy-specialist surface

`project easy specialist create --tool gemini` will adopt the maintained unattended default, but the corresponding instance launch surface will remain headless-only for Gemini. Operators will still need `project easy instance launch --headless` for Gemini specialists.

Why:

- That matches the current product boundary already enforced by the CLI.
- It avoids implying parser-backed Gemini TUI support that does not exist.
- It allows the easy-specialist default to align with the maintained headless launch posture without broadening Gemini into unsupported transports.

Alternatives considered:

- Keep Gemini at `as_is` by default to preserve the current CLI behavior.
  Rejected because the maintained easy path should follow the supported headless operator contract once Gemini unattended startup is supported.

### 4. Use the existing Gemini auth bundle families as the demo contract

The supported Gemini demo lane will rely on the already-maintained Gemini auth families:

- API key with optional `GOOGLE_GEMINI_BASE_URL`
- OAuth via `oauth_creds.json`

The canonical supported demo lane should use the existing OAuth-backed fixture at `tests/fixtures/agents/tools/gemini/auth/personal-a-default`, while the runtime importer should also accept the API-key lane at `tests/fixtures/agents/tools/gemini/auth/api-key-a-default` for completeness and manual variation.

Why:

- The prior Gemini runtime change already made those two auth families reliable for headless startup.
- Using the OAuth fixture in the supported demo validates the newly maintained unattended path instead of bypassing it with a simpler provider-only auth lane.
- Supporting both lanes in importer logic keeps the demo parameters consistent with the broader Gemini contract.

Alternatives considered:

- Limit the demo to API-key-only Gemini because it is operationally simpler.
  Rejected because it would under-exercise the newly maintained OAuth-backed unattended path.

### 5. Expand the existing demo pack rather than creating a Gemini-only variant

The supported `single-agent-gateway-wakeup-headless` pack will keep one shared output model and gain Gemini as a third maintained tool lane rather than splitting into a second Gemini-specific headless gateway demo.

Why:

- The pack is already parameterized by tool and persists the selected tool in shared demo state.
- The operator workflow and evidence model are the same; only the auth import and maintained lane set change.
- A separate Gemini pack would duplicate the same gateway, mailbox, and verification contract for minimal operator benefit.

Alternatives considered:

- Create a dedicated Gemini variant of the headless gateway demo.
  Rejected because the existing pack was already designed for multiple maintained lanes under one contract.

### 6. Tighten spec language where the repo currently carries stale Gemini exclusions

This change will replace the explicit “Gemini unsupported” wording in specs and maintained docs with positive maintained-lane language, but only where the new contract truly changes. The goal is to remove stale exclusions, not to broaden unrelated surfaces.

Primary maintained documentation targets are:

- `scripts/demo/single-agent-gateway-wakeup-headless/README.md`
- `scripts/demo/README.md`
- the project-easy operator docs under `docs/getting-started/` and `docs/reference/`

Why:

- The repo currently contains both newly implemented Gemini runtime support and older spec/doc language that still marks Gemini as intentionally excluded.
- That mismatch is now the main source of confusion.
- Spec-first cleanup keeps the implementation and user-facing docs aligned.

Alternatives considered:

- Change only code/tests now and defer spec/doc cleanup.
  Rejected because the user asked for an OpenSpec proposal and the existing mismatch is contractual, not merely editorial.

## Risks / Trade-offs

- [Gemini CLI unattended behavior may still be version-sensitive] → Add a version-scoped Gemini registry strategy with explicit evidence and keep fail-closed behavior for unknown versions.
- [Project-easy Gemini default changes could surprise operators who relied on `as_is`] → Preserve `--no-unattended` as the explicit opt-out and document that Gemini remains headless-only.
- [The demo may encode fixture assumptions too narrowly] → Keep importer logic aligned with the maintained Gemini auth families while using one canonical OAuth fixture in the supported lane.
- [Docs and specs may drift again across runtime, easy CLI, and demo surfaces] → Update all three spec capabilities in one change so the operator contract is defined once and reused consistently.
- [Gemini support might be interpreted as general interactive support] → Keep the spec and design explicit that the maintained Gemini path here is headless-only.

## Migration Plan

1. Add Gemini unattended strategy coverage to the launch-policy registry and adjust runtime/spec language from unsupported exclusion to positive maintained support.
2. Update `project easy specialist create` so Gemini follows the maintained unattended default on the headless lane while retaining `--no-unattended`.
3. Expand the `single-agent-gateway-wakeup-headless` demo parameters, runtime importer, docs, and tests to include Gemini.
4. Refresh maintained docs and verification coverage so Gemini is described as part of the supported lane set.

Rollback stays straightforward:

- revert the Gemini registry strategy and project-easy default change,
- restore the demo/spec lane set to Claude/Codex only,
- keep the lower-level Gemini headless runtime/auth support intact.

## Open Questions

None. The remaining ambiguity is implementation detail, not product direction: the repo already has enough lower-level Gemini runtime support to define the maintained unattended lane; this change is about lifting that support into the project-easy and demo contract.

## Context

The repository already defines the canonical preset-backed `agents/` source layout and the local `houmao-mgr agents launch` workflow, but the current runnable demo surface under `scripts/demo/` was archived. The only maintained examples today live indirectly in `tests/fixtures/agents/`, getting-started docs, and CLI behavior, which makes the minimum viable launch configuration harder to understand than it should be.

This change introduces one small supported tutorial demo under `scripts/demo/` rather than reviving the old demo-pack pattern. The demo must stay aligned with the canonical `skills/`, `roles/`, and `tools/` layout, remain secret-free in git, and work on this host by reusing local fixture auth bundles already maintained under `tests/fixtures/agents/tools/*/auth/`.

## Goals / Non-Goals

**Goals:**
- Provide one supported runnable example under `scripts/demo/` that demonstrates the minimum tracked files needed to launch an agent.
- Support both Claude and Codex from the same demo role so readers can compare provider-specific setup with the same logical role and workflow.
- Keep presets minimal and symmetric by using one demo-local auth alias name (`default`) while wiring that alias to provider-specific local fixture credentials at run time.
- Make the demo tutorial-shaped: tracked inputs, one runnable script, generated outputs, explicit verification, and short troubleshooting guidance.
- Restore `scripts/demo/README.md` as a supported demo index while preserving `scripts/demo/legacy/` as historical reference only.

**Non-Goals:**
- Recreate the archived multi-phase demo-pack/autotest surface.
- Introduce a new launcher API or new auth-discovery mechanism.
- Make the demo a generic credential broker for arbitrary local auth sources outside the fixture tree.
- Cover interactive tmux-attached TUI launches in this minimal demo.

## Decisions

### Decision: Use one provider-parameterized demo instead of separate Claude and Codex demos

The demo will use a shared role, `minimal-launch`, with two tracked presets:
- `roles/minimal-launch/presets/claude/default.yaml`
- `roles/minimal-launch/presets/codex/default.yaml`

This keeps the role prompt constant while isolating only the tool-specific differences in setup and auth projection.

Alternatives considered:
- Separate demo directories per provider: simpler scripting, but duplicates the main teaching material and obscures the fact that role and provider are separate axes.
- One preset only: does not satisfy the requirement to teach both Claude and Codex.

### Decision: Track only secret-free assets and create auth aliases at run time

The tracked demo tree will contain:
- `skills/` as an empty but present repository root,
- one shared role prompt,
- one Claude preset and one Codex preset,
- tracked tool adapters and secret-free setup bundles,
- tutorial inputs such as the prompt fixture.

The demo script will materialize a generated working tree under `scripts/demo/minimal-agent-launch/outputs/...` and create:
- `tools/claude/auth/default -> tests/fixtures/agents/tools/claude/auth/kimi-coding`
- `tools/codex/auth/default -> tests/fixtures/agents/tools/codex/auth/yunwu-openai`

The tracked presets can therefore stay symmetric with `auth: default` while the committed tree remains secret-free.

Alternatives considered:
- Commit symlinks directly inside the tracked demo tree: brittle on hosts where fixture auth has not been restored and makes the tracked surface host-dependent.
- Copy credential files into outputs: works, but duplicates local-only secrets and increases cleanup risk compared with symlinks.

### Decision: Keep the demo headless-first and script-driven

The runnable path will use `houmao-mgr agents launch --headless --yolo` followed by prompt, state inspection, and stop steps. This keeps the demo suitable for documentation-style execution, avoids attach behavior differences between interactive and non-interactive terminals, and focuses the teaching material on the agent-definition layout rather than tmux operator handoff.

Alternatives considered:
- Interactive TUI flow: demonstrates more of the operator surface, but stops being minimal once terminal attach and readiness posture become part of the tutorial.
- Build-only flow: teaches construction but not a full end-to-end launch and follow-up cycle.

### Decision: Make the demo tutorial-shaped instead of reviving a demo-pack contract

The new surface will follow the existing tutorial pattern:
- tutorial markdown with question, prerequisites, implementation idea, inputs/outputs, verification, and troubleshooting,
- a small runnable script,
- tracked `inputs/`,
- generated `outputs/`.

This keeps the supported demo understandable and narrow without reintroducing the old pack-owned orchestration model.

Alternatives considered:
- Reintroduce a `run_demo.sh start|inspect|verify|stop` pack interface: more flexible, but materially more complex than needed for the minimum launch tutorial.

## Risks / Trade-offs

- [Fixture auth bundles may be absent on some hosts] → The script should preflight the expected source auth directory and fail with a clear message explaining which fixture bundle is missing.
- [Headless-only coverage does not demonstrate interactive attach] → Keep this demo scoped to minimal configuration and link readers to other documentation for broader operator flows.
- [Provider-specific defaults may drift from the main fixture tree] → Reuse tracked adapters and secret-free setup structure directly from the canonical fixture layout and keep the tutorial explicit about which auth bundle names are being aliased.
- [Generated outputs may retain local symlinks after interrupted runs] → Keep all generated material under one demo-owned output root so cleanup remains straightforward.

## Migration Plan

1. Replace the archive-only top-level `scripts/demo/README.md` with a supported demo index that lists the new minimal demo and still labels `legacy/` as archived.
2. Add the new `scripts/demo/minimal-agent-launch/` tracked assets and runnable script.
3. Add getting-started documentation links that point readers from canonical docs to the runnable demo.
4. Verify both Claude and Codex lanes against the local fixture auth bundles available on this host.

## Open Questions

- No open technical questions are required for the proposal. The main remaining implementation work is choosing the exact generated output file names and command logging format.

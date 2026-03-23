## Context

The mailbox tutorial pack currently provisions `<demo-output-dir>/project` as a git worktree of the main repository and starts both sessions from that path. At the same time, the default sender and receiver blueprints point at the heavyweight `gpu-kernel-coder` role family. That fixture shape is reasonable for repo-scale engineering work, but it is a poor fit for mailbox and runtime-contract tests that only need one narrow prompt turn.

Two implementation details make this especially costly:

- The launched `working_directory` is the main behavioral lever. Codex resolves workspace trust from the nearest `.git` root above the working directory, so a main-repo worktree biases the tool toward scanning the full repository. `CLAUDE_CONFIG_DIR` and `CODEX_HOME` are still useful config homes, but they do not solve the repo-crawl problem on their own.
- The current tracked "direct live" integration lane uses owned fake `claude`, `codex`, and `cao-server` executables. That is useful deterministic coverage, but it is not the same as validating actual local Claude/Codex CLI behavior.

The mailbox hack-through issues reinforce the same picture. HT-01 showed that the launched workdir must remain inside the effective CAO home boundary. HT-03 and HT-04 showed the temptation to paper over slow or missing sentinel output with synthetic success. The design should instead fix the fixture shape, improve observability, and keep the direct mailbox contract strict.

## Goals / Non-Goals

**Goals:**

- Make a tiny dummy project the default launched workdir for narrow mailbox/demo sessions.
- Add lightweight mailbox-demo roles, brain recipes, and blueprints that bias Claude/Codex toward bounded mailbox behavior instead of broad repo exploration.
- Expose a pack-owned inspect/watch surface so maintainers can periodically check tmux, terminal logs, and tool state while slow real-agent turns are running.
- Separate deterministic automatic direct-path regression coverage from opt-in real-agent smoke coverage.
- Keep sentinel-delimited mailbox parsing strict and avoid synthetic result fallbacks.

**Non-Goals:**

- Remove repo-worktree coverage from every demo or test in the repository.
- Replace the existing tool-config home model with "dummy project as home dir" semantics everywhere.
- Guarantee that provider API latency disappears entirely once the fixture shape is improved.
- Reclassify broad engineering roles such as `gpu-kernel-coder` as incorrect for their intended workflows.
- Add generic plugin discovery for dummy projects or role families.

## Decisions

### Decision: Introduce a tracked dummy-project and mailbox-demo fixture family

The repository will add a dedicated fixture family for narrow runtime-agent tests:

- tracked dummy projects under `tests/fixtures/dummy-projects/`,
- lightweight mailbox-demo roles under `tests/fixtures/agents/roles/`,
- mailbox-demo Claude/Codex brain recipes under `tests/fixtures/agents/brain-recipes/`, and
- dedicated mailbox-demo blueprints under `tests/fixtures/agents/blueprints/`.

The first dummy project should be intentionally small and mailbox-oriented. The initial tracked starter manifest should be concrete and tiny, for example `pyproject.toml`, `README.md`, one small `src/mailbox_demo/` module pair, and one small `tests/test_*.py` file. The goal is to keep the workspace mailbox-ready without turning the fixture into another repo-scale sandbox.

The first role family should be explicitly narrow: no repo-wide discovery requirement, no CUDA/build/benchmark guidance, bounded reads, and short deterministic replies. Use role name `mailbox-demo`, recipes `claude/mailbox-demo-default.yaml` and `codex/mailbox-demo-default.yaml`, and blueprints `mailbox-demo-claude.yaml` and `mailbox-demo-codex.yaml` so the fixture family follows the existing naming pattern cleanly.

The implementation should promote the lightweight role/blueprint shape already prototyped inside `tests/integration/demo/test_mailbox_roundtrip_tutorial_pack_live.py` into tracked reusable fixtures instead of regenerating those definitions ad hoc inside tests.

**Alternatives considered**

- Keep the existing GPU roles and merely tighten the mailbox prompt: rejected because the role still pushes repo discovery and broad engineering work.
- Let each test synthesize ad hoc roles and blueprints: rejected because it duplicates fixture logic and hides the intended fixture contract.

### Decision: The tutorial pack will copy a dummy project into its demo-owned workdir and launch both sessions there

The mailbox tutorial pack should stop creating a git worktree of the main repository for `<demo-output-dir>/project`. Instead, it should copy a tracked dummy project fixture into that location and ensure the copied directory is used as a standalone git-backed workdir for the run.

The tracked fixture should remain source-only in the repository. After copying it into `<demo-output-dir>/project`, the tutorial pack should initialize the copied tree as a fresh standalone git repository with pinned author/committer identity and timestamps so the launched workdir remains git-backed and snapshot/report output stays reproducible.

The important contract is not "new config home"; it is "new launched workdir." The copied dummy project must be the path passed to `start-session --workdir`, and that path must remain inside the effective demo-owned CAO home boundary so the HT-01 ownership rule continues to pass.

Keeping the path under the selected demo output tree preserves the current pack-local layout while removing the main-repo trust and crawl pressure. The tool-specific config homes (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`) remain separate runtime configuration concerns.

**Alternatives considered**

- Point the session directly at the tracked fixture root: rejected because run-local edits would dirty tracked fixtures and make concurrent runs unsafe.
- Keep using a main-repo git worktree: rejected because it recreates the repo-crawl behavior the change is meant to remove.
- Change only the config home and keep the main-repo workdir: rejected because the workdir remains the source of trust and exploration behavior.

### Decision: Add a per-agent inspect command to the mailbox demo automation surface

The tutorial pack should grow a pack-local `inspect` command that can target `sender` or `receiver` and present the current watch coordinates for that session. This surface should mirror the CAO interactive demo terminology closely enough that the operator does not have to learn a second vocabulary.

The full inspect contract remains part of phase 2. Implementation should sequence the work inside Task 2.2: first persisted metadata and stable human/JSON rendering, then live CAO `tool_state`, then best-effort projected output tail.

For the selected agent, the inspect surface should expose at minimum:

- canonical agent identity,
- resolved tmux target and attach command,
- terminal identifier,
- resolved terminal log path and tail command,
- live `tool_state` when CAO lookup succeeds,
- the selected project workdir and runtime root, and
- best-effort projected output tail when explicitly requested.

The command should default to human-readable output and support `--json` for automation. If live CAO state or projected output tail cannot be resolved, `inspect` should still return persisted metadata and use `tool_state = unknown` plus an explicit note rather than failing outright.

This inspect surface is for periodic operator checks during slow turns. It is not a substitute for the runtime's own turn polling, and it should not introduce a synthetic mailbox success path.

**Alternatives considered**

- Tell maintainers to inspect state files and tmux sessions manually: rejected because the current pack does not expose those coordinates coherently.
- Add automatic tmux polling inside the test harness instead of an inspect command: rejected because that complicates the runtime path and does not help a maintainer understand what to attach to.

### Decision: Split deterministic automatic direct-path regression from opt-in real-agent smoke

The tracked automatic lane should be honest about what it validates. It may continue to use owned fake `claude`, `codex`, and `cao-server` stand-ins if doing so keeps the run deterministic, fast, and isolated, but it must still exercise the real tutorial-pack `start-session` and `mail` control path and the sentinel-delimited mailbox result contract.

Actual external CLI coverage should move into a separate opt-in smoke lane that uses the operator's local Claude/Codex tools and credentials. That smoke lane should reuse the same dummy-project and mailbox-demo blueprint defaults, and it should point the operator at the new inspect surface while slow turns are running.

The first real-agent smoke entrypoint should be a standalone manual script under `tests/manual/`. That preserves an unambiguous opt-in boundary and matches the existing manual smoke precedent in this repository.

This split keeps the deterministic lane meaningful without pretending it already covers real external agents.

**Alternatives considered**

- Force the tracked automatic lane to use actual local Claude/Codex CLIs: rejected because it makes the default regression suite environment-dependent and slow.
- Keep the current spec wording and rely on tribal knowledge that the test uses fakes: rejected because the spec should describe what the repository actually promises.

### Decision: Keep direct mailbox parsing strict and treat stall tuning as a bounded adjunct

The runtime should continue to require one valid sentinel-delimited mailbox result payload for each direct mail turn. The new fixture shape is the primary fix for HT-03 and HT-04, not synthetic `mail send` or `mail check` fallbacks.

If real-agent smoke still needs help with slow provider responses, mailbox-demo blueprints may carry bounded CAO shadow-stall overrides in a follow-up change after the dummy-project/lightweight-role baseline has been exercised. That tuning is secondary and must not relax the sentinel-delimited correctness boundary.

**Alternatives considered**

- Synthesize mailbox results when the sentinel block is missing: rejected because it hides the exact direct-path failure the pack is supposed to surface.
- Apply broad global stall-timeout increases first: rejected because the fixture mismatch is the root cause and should be addressed directly.

## Risks / Trade-offs

- [More tracked fixtures increase maintenance surface] -> Mitigation: start with one minimal mailbox-ready dummy project and one mailbox-demo role family, then expand only when another test class needs it.
- [Dummy projects can hide repo-scale discovery issues] -> Mitigation: keep repo-worktree coverage explicit and separate instead of making mailbox/runtime contract tests shoulder both concerns.
- [A new inspect surface adds persisted-state coupling] -> Mitigation: mirror the existing CAO interactive demo inspect contract and reuse the same terminology and best-effort behavior.
- [Real-agent smoke remains environment-dependent] -> Mitigation: make it an opt-in manual script under `tests/manual/`, fail clearly on missing prerequisites, and keep deterministic automatic coverage as the default tracked lane.
- [Smaller fixtures alone may not solve every provider stall] -> Mitigation: keep bounded per-blueprint shadow-stall tuning available as a follow-up adjustment without weakening mailbox result validation.

## Migration Plan

1. Add tracked dummy-project fixtures with a concrete tiny starter manifest, the `mailbox-demo` role family, matching recipes/blueprints, and fixture-selection guidance.
2. Switch the mailbox tutorial pack from main-repo worktree provisioning to copying the source-only dummy-project fixture and initializing a fresh git-backed workdir under the demo-owned output/home tree.
3. Update tutorial-pack defaults, especially `inputs/demo_parameters.json`, plus README and verification/snapshot expectations to describe the dummy-project and mailbox-demo blueprint contract.
4. Add the pack-local `inspect` command and persist the session metadata needed to resolve tmux/log/tool-state diagnostics for sender and receiver, implementing the full phase-2 surface in layers.
5. Update the tracked deterministic integration lane and scenario runner to use the new fixtures while continuing to exercise the direct runtime mail path without synthetic fallback.
6. Add the opt-in real-agent smoke manual script under `tests/manual/` and document how maintainers use `inspect` while waiting on slow live turns.

## Resolved Review Decisions

- The copied dummy-project fixture remains source-only in the repository, and the tutorial pack initializes a fresh pinned-metadata git repository after copy.
- The first real-agent smoke entrypoint lives as a standalone manual script under `tests/manual/`.
- The full `inspect` contract stays in phase 2, with implementation sequenced inside Task 2.2 rather than split into a new phase.
- Mailbox-demo CAO shadow-stall tuning stays deferred until a follow-up change informed by real-agent smoke observations.

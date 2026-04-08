# Issue: Real-Agent HTT Worktree Runs Mix Snapshot, Host Secrets, Tool State, And Workdir Contracts

> Obsolete as of 2026-04-08.
> Moved from `context/issues/known/` to `context/issues/obsolete/`.
> Retained for historical reference only.


## Status
Known as of 2026-03-18.

## Summary

Real-agent hack-through-testing runs in a disposable worktree are exposing a structural contract problem rather than one isolated bug.

The current run model behaves as if "the repo snapshot" is enough to reproduce a real-agent run. In practice, the path depends on four different root classes:

1. source snapshot
2. operator-local credentials and login state
3. tool-owned runtime state and home directories
4. launched project workdir

Those roots are documented separately in the repository, but the HTT and tutorial-pack flows still discover the boundaries only at runtime. That leads to repeated failures when the run is moved into a fresh worktree where ambient machine state is no longer accidentally visible.

This note intentionally inlines the relevant observed failure excerpts and does not reference `.agent-automation/`, because that tree is temporary and not part of the durable repository contract.

## What Failed

Observed failure sequence during a real-agent mailbox roundtrip HTT run:

### 1) Snapshot run could not see local credential profiles

Preflight failed with missing repo-relative credential files:

```text
sender: missing or unreadable prerequisite paths: .../tests/fixtures/agents/brains/api-creds/claude/personal-a-default/env/vars.env
receiver: missing or unreadable prerequisite paths: .../tests/fixtures/agents/brains/api-creds/codex/personal-a-default/env/vars.env
```

### 2) CAO start failed because project workdir was outside derived CAO home

After bridging credentials, session start failed with:

```text
Failed to start CAO session ... Working directory not allowed: .../demo-output/project ... outside home directory .../demo-output/cao/runtime/cao_servers/localhost-9889/home
```

### 3) Mailbox turn then failed on the live prompt/parse contract

After widening CAO home as a temporary workaround, the roundtrip advanced but failed with:

```text
Mailbox result parsing failed: expected exactly one sentinel-delimited payload.
```

The saved terminal tail showed the injected mailbox request plus a Claude-side installer/banner message, but not one clean machine-readable mailbox result block.

## Current Behavior

- The HTT snapshot helper creates a snapshot commit from `git add -A`, which does not include ignored local-only files. That is correct for a code snapshot, but it means repo-local credential profiles are not portable into the worktree by default.
- Credential profiles are currently documented as local-only and gitignored under `<agent-def-dir>/brains/api-creds/<tool>/<cred-profile>/...`.
- The mailbox tutorial pack writes a demo-local CAO launcher config with `home_dir = ""`, which derives CAO home under the demo runtime tree, while the copied dummy project workdir lives at `<demo-output-dir>/project`.
- Houmao's documented launcher contract says CAO `home_dir` is a state/profile-store anchor, not a required parent of repo workdirs, but older installed `cao-server` builds can still enforce the historical "workdir must be under home" rule.
- Mailbox shadow completion currently treats "a begin sentinel followed by a later end sentinel" as enough to declare completion, while exact parsing later requires exactly one valid sentinel-delimited payload. That leaves room for prompt echo or incidental text to satisfy one stage but fail the next.

## Root Cause

The underlying problem is implicit host-state coupling.

The real-agent run path currently mixes multiple filesystem and tool-state contracts that should be separate:

- repo-owned snapshot content
- operator-owned secrets and login material
- Houmao-owned runtime roots
- CAO-selected home/state roots
- launched project workdir

In the main checkout, those boundaries can be masked by existing local files, existing tool state, and already-working host setup. In a disposable worktree, the hidden assumptions become visible immediately.

The worktree is not the root cause. The worktree is removing accidental ambient context and exposing that the runnable contract is underspecified.

## Why This Matters

- Real-agent HTT becomes fragile and machine-specific.
- Failures appear late and in confusing order: missing credentials, then launcher/home policy mismatch, then live prompt/parse problems.
- Developers patch around each failure locally instead of working against one explicit portability model.
- The repository already has ownership and root-separation concepts, but the highest-friction real-agent path is not enforcing them as a first-class run contract.

## Desired Direction

Treat real-agent HTT as an explicit run-context assembly problem, not as a raw repo snapshot.

### 1) Make run roots first-class

The run plan should explicitly model:

- `source_root`
- `project_workdir`
- `runtime_root`
- `tool_state_root` / CAO home
- `external_prereqs`

No step should silently assume one of those roots can stand in for another.

### 2) Move real-agent prerequisites out of the repo snapshot contract

Real-agent credentials and tool login state should be declared as external prerequisites or mounted inputs, not assumed to live under a repo-relative gitignored tree inside the snapshot.

A snapshot worktree should be allowed to remain code-only.

### 3) Capability-probe external tools before live start

Preflight should detect important tool/runtime compatibility boundaries up front, including:

- whether the installed `cao-server` supports workdirs outside home
- whether expected launcher compatibility behavior is present
- whether the selected agent tool has known installer/login/prompt blockers

That should produce either an explicit fail-fast error or an intentional compatibility layout choice.

### 4) Make layout strategy explicit

The run planner should choose a named layout strategy such as:

- separated project workdir plus separate CAO home
- compatibility layout with project workdir nested under CAO home

That choice should be deliberate and capability-driven, not an incidental effect of derived defaults.

### 5) Tighten the mailbox control contract

~~Mailbox completion and final extraction should use the same exact contract, ideally over a post-submit delta or another stricter machine-readable surface, so prompt echo cannot satisfy completion while still failing final parse.~~

**Resolved (2026-03-18).** Issue-001 (prompt-echo false positive) and issue-007 (observer gated behind generic completion) together close this layer:
- Sentinel extraction now uses standalone-line matching shared between observer and parser (issue-001, fixed on `devel`).
- Mailbox observer now runs on every post-submit poll independent of generic shadow lifecycle (issue-007, fixed in HTT worktree, merge pending).

## Relevant Stable References

- `magic-context/skills/openspec-ext/openspec-ext-hack-through-test/scripts/create_snapshot_worktree.sh`
- `docs/reference/agents_brains.md`
- `tests/fixtures/agents/brains/api-creds/README.md`
- `docs/reference/system-files/roots-and-ownership.md`
- `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/tutorial_pack_helpers.py`
- `docs/reference/cao_server_launcher.md`
- `docs/reference/cao_shadow_parser_troubleshooting.md`
- `src/houmao/agents/realm_controller/backends/cao_rest.py`
- `src/houmao/agents/realm_controller/mail_commands.py`

## Suggested Follow-Up

- Introduce a durable "external prerequisites" contract for real-agent runs.
- Add a CAO compatibility probe and layout-selection step before live start.
- Decide whether repo-local `api-creds/` should remain a convenience for local development only rather than a dependency of portable HTT runs.
- ~~Harden the mailbox completion/extraction contract so downstream live-agent failures are not amplified by prompt echo.~~ → Resolved by issue-001 + issue-007.

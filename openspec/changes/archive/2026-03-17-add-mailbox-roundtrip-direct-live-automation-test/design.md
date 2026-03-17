## Context

The mailbox roundtrip tutorial pack currently has strong contract coverage for its wrapper behavior and sanitized report output, but its automatic success path can still be satisfied by a fake harness that never proves the live direct mail path works. Recent live investigation showed the difference clearly: a fresh demo root can start sessions, yet the automatic roundtrip still fails before canonical mail is delivered, and maintainers cannot inspect readable message Markdown under the repo-local mailbox afterward.

The user requirement is narrower and stricter than "make the demo less fake." The automatic test must prove that:

- two real agents were started for the tutorial pack;
- the mail operations were executed through the direct live-agent path, not through gateway transport commands and not through fake mailbox injection;
- the completed demo root contains two inspectable per-agent mailbox directories plus canonical Markdown messages that a maintainer can open and read.

The design therefore needs an automatic test workflow that owns its state, avoids ambient local collisions, and still exercises the real tutorial-pack code path. That workflow may be implemented as a dedicated live integration test, a scripted runner, or another multi-step automatic sequence over the demo directory; it does not need to collapse into a single command-line program.

## Goals / Non-Goals

**Goals:**

- Add automatic integration coverage that runs the mailbox roundtrip tutorial pack against a fresh demo output directory and a test-owned loopback CAO instance.
- Exercise the real direct mail execution path used by `realm_controller mail`, `run_demo.sh roundtrip`, or equivalent direct prompt submission through the resumed live session.
- Verify that a successful run leaves two per-agent mailbox directories under `<demo-output-dir>/shared-mailbox/mailboxes/` and canonical readable Markdown messages under `<demo-output-dir>/shared-mailbox/messages/`.
- Ensure the automatic test reads the resulting mailbox artifacts from disk and validates bodies, projections, and thread linkage.
- Isolate the automatic test from ambient local CAO and shared-registry state so it may stop and restart its own CAO safely.

**Non-Goals:**

- Keeping the existing fake-harness integration test as the only source of confidence for mailbox roundtrip behavior.
- Using gateway transport commands such as `attach-gateway`, `gateway-send-prompt`, or gateway queue assertions to satisfy the mailbox roundtrip requirement.
- Requiring the default automated test to depend on ambient developer state at `localhost:9889` or the default shared registry.
- Expanding the sanitized expected report into a raw mailbox content snapshot.

## Decisions

### 1. Add a separate live automatic workflow target for the tutorial pack

The new requirement should be satisfied by a separate live automatic workflow target, distinct from the current fake-tool scenario runner test. That target may be implemented as a dedicated live integration test, a scripted maintainer runner, or another owned multi-step sequence. The fake-harness suite remains useful for fast contract coverage, but it cannot satisfy the new requirement because it can fabricate successful mailbox mutations without proving that live agent startup and direct prompt execution actually work.

The live automation target should run the real pack commands against a fresh temp-root demo output directory and treat the resulting directory as the inspection target.

Alternatives considered:

- Replace the existing fake-harness suite entirely.
  Rejected because the fast hermetic contract test still provides useful narrow feedback.
- Keep only manual verification for the live path.
  Rejected because the explicit requirement is automatic coverage of the real code path.

### 2. The live test shall use the direct prompt mail path, not gateway transport commands

The test should drive `run_demo.sh start`, `run_demo.sh roundtrip`, `run_demo.sh verify`, and `run_demo.sh stop`, or an equivalent sequence built from direct `realm_controller mail ...` commands. The required behavior is the same direct live session path that `realm_controller mail` uses via `controller.send_prompt(...)`.

The automatic test should explicitly forbid relying on `attach-gateway`, `gateway-send-prompt`, or fake mailbox delivery helpers to satisfy the requirement. If the implementation requires gateway transport commands to make the roundtrip pass, that is a product gap to fix rather than acceptable test setup.

Alternatives considered:

- Allow gateway transport setup as part of the automatic test.
  Rejected because the user explicitly requires no gateway-involved mail operation path for this coverage.
- Continue using fake direct JSON results while adding more mailbox assertions.
  Rejected because it still does not prove the real direct path works.

### 3. The live test shall use owned isolated state

The test must isolate itself from ambient local runtime state. It should choose a fresh demo output directory, a non-default free loopback CAO port, and a dedicated shared-registry root. That gives the test freedom to stop or restart its own CAO instance without disrupting unrelated local work and avoids collisions from previously running agents that own the same logical identities.

The test-owned state should include at least:

- fresh `<demo-output-dir>`;
- test-owned `CAO_BASE_URL` on a picked free loopback port;
- test-owned launcher runtime/profile store under the demo root;
- explicit `AGENTSYS_GLOBAL_REGISTRY_DIR` scoped to the test root.

Alternatives considered:

- Reuse the default `http://localhost:9889` launcher target.
  Rejected because it collides with ambient local CAO state and weakens test ownership.
- Reuse the default shared registry.
  Rejected because authoritative agent-id collisions can make the result untrustworthy.

### 4. The assertions shall inspect both mailbox views and the canonical messages

The pass condition should not stop at "two files exist under `messages/`." The automatic test must inspect:

- the sender mailbox directory;
- the receiver mailbox directory;
- the canonical send message Markdown document;
- the canonical reply message Markdown document;
- the per-agent projections that point inbox/sent views at those canonical documents.

The test should read the message bodies from disk and compare them to the tracked `initial_message.md` and `reply_message.md` inputs. It should also validate thread linkage and reply-to-parent metadata from the canonical message documents.

Alternatives considered:

- Assert only that the shared mailbox index contains rows.
  Rejected because that does not satisfy the maintainer requirement to find and read the mail.
- Assert only on machine-readable demo step JSON.
  Rejected because that can succeed without inspectable mailbox artifacts.

### 5. Automatic coverage should remain deterministic by using test-owned live agent fixtures

The live suite should still avoid reliance on ambient vendor sessions or human-managed local terminals. The preferred path is to use test-owned agent definitions and tool/runtime fixtures that exercise the same real startup, resume, direct prompt, and mailbox code paths while keeping the agent turn behavior deterministic enough for CI.

This means "real code path" here refers to the demo wrapper, launcher ownership, brain build, session start, direct mail prompt execution, mailbox scripts, and on-disk artifact flow. It does not require the suite to depend on nondeterministic external vendor behavior if a deterministic test-owned live-agent fixture can cover the same product path.

Alternatives considered:

- Require the default automated test to use ambient Claude/Codex credentials and live model behavior.
  Rejected because it would be flaky, secret-dependent, and hard to run safely in routine automation.

## Risks / Trade-offs

- [Live direct-path testing is slower and more failure-prone than the fake harness] → Keep the existing fake suite for narrow contract coverage and scope the new suite to one owned end-to-end direct-path roundtrip.
- [Ambient local CAO or registry state can contaminate results] → Require a free loopback port, fresh demo output root, and isolated shared-registry root.
- [The current product path may not yet satisfy the no-gateway direct-mail requirement] → Treat missing readiness, sentinel failures, or other live-path gaps as product bugs surfaced by the new suite rather than papering them over in the test.
- [Readable mailbox assertions could become brittle if they key off unstable paths] → Assert mailbox layout, message bodies, projections, and thread linkage while tolerating nondeterministic IDs and timestamps through pattern-based checks.

## Migration Plan

No user-facing migration is required. Introduce the new live automatic workflow target alongside the existing fake-harness suite, then iterate on the demo/runtime implementation until the live path passes reliably. The fake-harness suite remains as a fast regression layer but no longer satisfies the stronger "real direct-path automatic test" requirement by itself.

## Open Questions

- Should the live suite use a dedicated test-owned agent-definition fixture distinct from `tests/fixtures/agents`, or should it extend the existing fixture tree with deterministic live-test recipes?
- Should the new live automatic workflow target be part of the default integration target, or should it live under a dedicated slower command that still runs in routine CI?

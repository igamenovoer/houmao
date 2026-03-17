## Context

The mailbox roundtrip tutorial pack currently treats one generated workspace path as the place for copied inputs, runtime artifacts, reports, mailbox state, and the agents' working directory. That kept the first version small, but it leaves the agents without a realistic project checkout and makes the filesystem layout harder to explain during interactive use.

This revision keeps the tutorial pack local to `scripts/demo/mailbox-roundtrip-tutorial-pack/` and preserves the same mailbox roundtrip flow, but it separates demo-owned output storage from the agents' actual working directory. The new wrapper surface is intentionally named `--demo-output-dir` instead of `--demo-workdir` because the selected path owns more than just the agent workdir: it also holds runtime artifacts, copied inputs, reports, and mailbox state.

Two existing repository patterns matter here:

- The interactive CAO demo already provisions a nested git worktree for demo isolation.
- Houmao already supports redirected local jobs storage through `AGENTSYS_LOCAL_JOBS_DIR`, while `start-session` itself only exposes `--workdir` as a first-class CLI surface today.

## Goals / Non-Goals

**Goals:**
- Give the mailbox tutorial pack one explicit demo-owned output root controlled by `--demo-output-dir`.
- Provision a nested `<demo-output-dir>/project` git worktree and use that path as the shared `--workdir` for both agents.
- Keep runtime root, mailbox root, copied inputs, captured JSON outputs, and reports under the selected demo output directory so operators can inspect one self-contained layout.
- Add a demo-owned `--jobs-dir` override that redirects both sessions' job-root base when desired, while preserving Houmao's default job-dir behavior when omitted.
- Update README and report contracts so the filesystem story stays explicit and testable.

**Non-Goals:**
- Add a new first-class `realm_controller start-session --jobs-dir` public CLI option in this change.
- Change mailbox protocol behavior, runtime `mail` command semantics, or CAO session-control semantics.
- Generalize the mailbox tutorial into a reusable multi-agent framework.
- Mirror uncommitted source-tree edits automatically into the provisioned git worktree.

## Decisions

### 1. The runner will use a stable demo-owned output directory and a nested `project/` worktree

`run_demo.sh` will accept `--demo-output-dir <path>`. When omitted, it will default to a repo-local directory under `tmp/demo/mailbox-roundtrip-tutorial-pack`. Inside that directory, the runner will provision or validate:

- `project/` as a git worktree of the main repository
- `runtime/` as the runtime root
- `shared-mailbox/` as the mailbox root
- `inputs/` for copied tracked demo inputs
- captured command outputs and reports at the demo-output-dir top level

Both agents will use `<demo-output-dir>/project` as their `--workdir`.

Why:
- This gives the agents a real repository checkout to inspect and modify.
- It keeps all demo artifacts discoverable under one operator-visible root.
- The name `--demo-output-dir` accurately reflects that the directory owns multiple artifact families, not just the working tree.

Alternatives considered:
- Keep one flat workspace directory and let agents work directly in it.
  Rejected because it mixes operator-facing project files with mailbox/runtime/report artifacts and leaves no dedicated project checkout.
- Name the option `--demo-workdir`.
  Rejected because the selected path is not the agent workdir; the actual agent workdir is the nested `project/` directory.

### 2. Relative path overrides will resolve against the repository root

When `--demo-output-dir` or `--jobs-dir` receives a relative path, the runner will resolve it from the repository root rather than from the caller's transient shell cwd.

Why:
- This is a repo-owned tutorial pack, and its default output path is already repo-local.
- Repo-root-relative resolution makes README examples reproducible even when the script is invoked from another directory.

Alternatives considered:
- Resolve relative paths from the caller's current shell directory.
  Rejected because it makes the same command produce different layouts depending on where the operator happens to stand.

### 3. `--jobs-dir` will be a demo-local wrapper option backed by `AGENTSYS_LOCAL_JOBS_DIR`

The runner will accept `--jobs-dir <path>` and, when provided, set `AGENTSYS_LOCAL_JOBS_DIR` for the `start-session` calls so both launched sessions derive per-session job directories from that caller-selected root. When `--jobs-dir` is omitted, the runner will not set the env var and Houmao will keep its default job-dir behavior under:

`<demo-output-dir>/project/.houmao/jobs/<session-id>/`

Why:
- The runtime already supports redirected local jobs storage through `AGENTSYS_LOCAL_JOBS_DIR`.
- This keeps the change scoped to the demo pack rather than broadening the public runtime CLI surface.
- Operators still get explicit control when they want scratch job output off the worktree.

Alternatives considered:
- Add `realm_controller start-session --jobs-dir` in the same change.
  Rejected because it expands the public runtime API surface beyond the demo-specific need being addressed here.

### 4. Worktree provisioning will reuse the interactive CAO demo pattern and fail clearly on invalid existing state

The runner will use `git worktree add --detach <demo-output-dir>/project HEAD` to provision the nested project checkout when absent. If `project/` already exists and is a valid git worktree, the runner may reuse it. If `project/` exists but is not a git worktree, the runner will fail clearly instead of mutating an unexpected directory.

Why:
- The repository already uses this pattern in the interactive CAO demo.
- Clear validation is safer than trying to "repair" a user directory that may contain unrelated files.

Alternatives considered:
- Always delete and recreate `project/`.
  Rejected because that is more destructive than needed for an interactive tutorial path.
- Clone the repository instead of using a worktree.
  Rejected because worktrees are cheaper and remain aligned with the current repository checkout.

### 5. README and report artifacts will describe the demo root, project worktree, mailbox root, and jobs-root behavior explicitly

The tutorial README, example commands, appendix tables, and sanitized-report helpers will be updated so they distinguish:

- demo output dir
- agent workdir (`project/`)
- mailbox root
- runtime root
- default and overridden job-dir placement

Why:
- The filesystem layout is now part of the operator-facing contract.
- Without these updates, the runner would again become harder to reason about than the README.

Alternatives considered:
- Leave layout details implicit in the runner implementation.
  Rejected because this tutorial pack exists to teach the operator workflow, not to hide it.

## Risks / Trade-offs

- [Stable default demo-output-dir can accumulate stale artifacts] -> Mitigation: validate the nested worktree explicitly, refresh copied inputs and generated outputs on each run, and fail clearly when an existing path is incompatible.
- [Git worktree contents reflect committed `HEAD`, not uncommitted local edits] -> Mitigation: document that behavior in the README so operators understand what "project/" contains.
- [Redirected jobs-root paths could confuse users if they expect worktree-local scratch output] -> Mitigation: document the default path and explain that `--jobs-dir` is an opt-in relocation mechanism.
- [The demo now spans more path families, which increases report-sanitization surface] -> Mitigation: extend the sanitizer and expected-report contract to mask demo-output-dir, project worktree, runtime-root, and relocated job-dir paths consistently.

## Migration Plan

This is a demo-pack revision only. The implementation will update the runner, README, helper scripts, and tests in one change. No runtime data migration is required. Existing manual invocations that rely on the old implicit workspace layout will need to adopt `--demo-output-dir` naming in the updated README examples.

## Open Questions

No blocking open questions. This proposal intentionally keeps `--jobs-dir` demo-local and keeps the new default centered on one repo-owned demo output directory with a nested `project/` worktree.

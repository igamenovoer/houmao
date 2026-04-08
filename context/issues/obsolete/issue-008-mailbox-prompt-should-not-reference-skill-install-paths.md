# Issue 008: Mailbox Prompt Should Not Reference Skill Install Paths

> Obsolete as of 2026-04-08.
> Moved from `context/issues/known/` to `context/issues/obsolete/`.
> Retained for historical reference only.


## Priority
P1 — Real-agent mailbox turns can drift into skill/path discovery instead of executing the mailbox operation.

## Status
Open as of 2026-03-18.

## Summary

The current mailbox runtime installs the bundled filesystem mailbox skill into the tool home, but the mailbox prompt still tells the agent to use a path-shaped skill reference:

```text
.system/mailbox/email-via-filesystem
```

That leaks an installation detail into the prompt contract.

For tool-driven skills, the runtime should install the skill into the correct tool-specific location and let the tool resolve it normally. The prompt should then either:

- invoke the installed skill by its tool-facing skill name, or
- just use triggering instructions that rely on the tool's automatic skill resolution.

The prompt should not require the model to reason about an internal install path or search for that path in the worktree.

## What Is Wrong Today

The current implementation mixes two different contracts:

1. Runtime contract:
   Houmao projects the mailbox skill into the tool home.
2. Prompt contract:
   Houmao tells the agent about a namespace/path-like reference as if that location is part of the turn contract.

That mismatch is visible in the current prompt builder:

- `src/houmao/agents/realm_controller/mail_commands.py` says:
  - "Use the runtime-owned filesystem mailbox skill `.system/mailbox/email-via-filesystem` for this mailbox operation."

At the same time, the launched tool process still runs in the session working directory rather than inside the tool home:

- headless backends launch with `cwd=self._plan.working_directory`
- Codex app-server launches with `cwd=str(self._plan.working_directory)`
- tmux sessions are created with `tmux new-session -c <working_directory>`

So the current prompt can cause the model to treat the path-like skill reference as something it should discover or validate from the repository cwd, even though the runtime actually installed the skill into the tool home.

## Evidence

### 1. The prompt currently embeds the path-like reference

- `src/houmao/agents/realm_controller/mail_commands.py`
- `tests/unit/agents/realm_controller/test_mail_commands.py`

The unit test explicitly asserts that the generated prompt contains `.system/mailbox/email-via-filesystem`.

### 2. The runtime projects the skill into the tool home

- `src/houmao/agents/mailbox_runtime_support.py`
- `src/houmao/agents/brain_builder.py`

The mailbox skill is copied into:

```text
<home>/skills/.system/mailbox/email-via-filesystem/
```

This is correct as an internal runtime detail, but it should not be part of the mailbox turn contract.

### 3. The tool runs with separate home and cwd

- Claude uses `CLAUDE_CONFIG_DIR`
- Codex uses `CODEX_HOME`
- both still execute with the session `working_directory` as cwd

That means "skill install root" and "agent cwd" are deliberately different concepts in the runtime.

### 4. Real-agent behavior already showed the failure mode

In the 2026-03-18 HTT rerun, the sender did not simply execute the mailbox operation. It spent the turn searching and reading files instead, then timed out:

```text
Mailbox command failed: Timed out waiting for shadow turn completion ...
Searching for 3 patterns, reading 3 files…
```

This behavior is consistent with a prompt that encourages environment and skill-path discovery instead of relying on an installed tool-native skill contract.

## Root Cause

Houmao currently models mailbox skills as copied files plus prompt prose, but it does not model tool-specific skill invocation semantics explicitly.

More concretely:

1. Both Claude and Codex adapters currently use the same projected `skills` destination in the runtime home.
2. The mailbox prompt uses one shared path-shaped reference string for both tools.
3. There is no tool-specific abstraction that says:
   - how a skill should be invoked once installed,
   - whether the prompt should mention only a skill name,
   - or whether the prompt should avoid naming the skill entirely and rely on trigger wording.

As a result, an internal install detail leaked into the operator-facing turn contract.

## Desired Direction

The mailbox runtime should separate these concerns cleanly.

### 1. Installation is runtime-owned

Houmao should continue to install bundled mailbox skills into the correct tool-specific runtime location.

The exact path is an internal implementation detail.

### 2. Invocation is tool-facing

Mailbox prompt generation should be tool-aware and choose one of these patterns:

- explicit skill invocation by tool-facing skill name, or
- no explicit skill mention at all, using a mailbox-operation prompt that the installed skill/tool stack handles automatically

It should not mention `.system/...` paths or any other install-root detail.

### 3. Prompts should describe the mailbox task, not the install layout

The mailbox prompt should focus on:

- the mailbox operation,
- the session-provided mailbox bindings,
- the result contract,
- and safety constraints such as "only mark read after success"

It should not teach the model where the skill package was projected on disk.

## Likely Touch Points

- `src/houmao/agents/realm_controller/mail_commands.py`
- `src/houmao/agents/mailbox_runtime_support.py`
- tool-adapter/runtime-home design for Claude and Codex
- mailbox runtime docs under `docs/reference/mailbox/`
- tests that currently assert prompt text contains `.system/mailbox/email-via-filesystem`

## Acceptance Criteria

1. Mailbox prompts no longer mention `.system/mailbox/email-via-filesystem` or any other skill install path.
2. The runtime still installs the bundled mailbox skill into the correct tool-specific runtime location.
3. Prompt generation becomes tool-aware where needed, instead of assuming one shared path-like reference works across tools.
4. Tests validate the intended prompt contract without asserting install-path leakage.
5. Mailbox docs describe the install location as an internal runtime detail rather than a prompt-visible contract.

## Verification Strategy

To verify that skills are actually invokable through the tool's normal skill mechanism, the repo should add a direct runtime experiment instead of only checking projected file placement.

The proposed check is:

1. Create one or more dummy bundled skills for the target tool.
2. Make each dummy skill perform one trivial visible side effect, such as writing a marker file into a designated output directory.
3. Install those dummy skills through the normal runtime-home projection path.
4. Start a real session for the target tool.
5. Prompt the agent using only task wording that should trigger the skill.
6. Do not mention the skill name.
7. Do not mention the skill install path.
8. Observe whether the expected output file appears.

That test would answer the real contract question:

- can the tool discover and invoke the installed skill automatically from prompt semantics,
- without path disclosure,
- and without requiring the model to browse the repo for the skill package.

This verification should be run separately for Claude and Codex because their tool-native skill resolution behavior may differ even if Houmao currently projects both into a similarly named `skills` subtree.

## Connections

- Separate from `issue-007-shadow-mail-result-observer-gated-by-generic-completion.md`
- Related to `enhance-mailbox-runtime-smoke-tests-use-minimal-sender-prompts.md`
- Related to `context/design/behaviour/how-skill-is-installed-into-agents.md`

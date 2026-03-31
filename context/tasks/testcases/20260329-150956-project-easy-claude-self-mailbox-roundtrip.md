# Test Case: Project Easy Claude Self Mailbox Roundtrip

**Timestamp:** 2026-03-29 15:09:56 UTC
**Case slug:** `project-easy-claude-self-mailbox-roundtrip`
**Primary workflow:** `houmao-mgr project easy` end-to-end TUI mailbox roundtrip
**Execution mode:** hack-through-testing

## Goal

Verify a clean-start project can create a Claude Code specialist, provision a filesystem mailbox, start the agent in TUI mode, have the agent register with its mailbox account, send an email to itself, and surface the received email for operator inspection.

## Scenario

1. Delete project-local `.houmao/` to guarantee a clean start.
2. Initialize a fresh project overlay.
3. Create a Claude Code specialist intended for TUI use.
4. Create a mailbox root.
5. Create or prepare a mailbox account for the agent.
6. Register the agent against that mailbox account.
7. Start the agent.
8. Ask the agent to send an email to itself through the filesystem mailbox.
9. Inspect the mailbox artifacts and show the delivered email.

## Concrete Steps To Drive

1. `rm -rf .houmao`
2. `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr project init`
3. `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr project easy specialist create ... --tool claude ...`
4. `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr project mailbox init`
5. Prepare an agent mailbox account under the project mailbox root.
6. Launch the Claude agent in TUI mode with mailbox wiring.
7. From the running agent, send a message addressed to the agent's own mailbox address.
8. Read the resulting mailbox message from disk or via mailbox CLI and present the contents.

## Expected Success Signals

- `.houmao/` is recreated from scratch and contains the project overlay.
- The Claude specialist is persisted and resolvable through `project easy specialist get`.
- The mailbox root is initialized successfully.
- The mailbox account exists and is bound to the launched agent.
- `project easy instance list/get` shows the mailbox payload for the running agent.
- A self-addressed email is delivered into the filesystem mailbox.
- The email body and key headers are visible to the operator at the end of the run.

## Expected Failure Signals

- Specialist creation fails because Claude auth/setup defaults are incomplete.
- Mailbox root initialization or account registration fails.
- TUI launch starts but the agent never registers with the mailbox account.
- The agent cannot send mail to itself or delivery does not appear in the mailbox.
- The email is delivered but cannot be inspected through available CLI/filesystem tools.

## Notes

- This case intentionally uses a clean project-local `.houmao/` start rather than a reused overlay.
- The target is a real end-to-end operator path, not a unit or smoke test.
- The mailbox transport should remain filesystem-based unless the run explicitly pivots for a discovered blocker.

## Latest Result

**Last run:** 2026-03-30 05:01:55 UTC
**Tested commit:** `330bfca80f330fc14d46521900fc50475fac87d2`
**Outcome:** passed

### Observed Success Path

1. Removed the project-local `.houmao/` overlay and re-ran `houmao-mgr project init`.
2. Imported the Claude fixture auth bundle into the fresh project overlay and created specialist `claude-self-050155`.
3. Initialized the project mailbox root and registered project address `claude-self-050155@agents.localhost`.
4. Launched a TUI instance for `claude-self-050155`.
5. Bound the running instance to the project mailbox account.
6. Sent a self-addressed message with `houmao-mgr agents mail send`.
7. Verified actor-scoped delivery with `houmao-mgr agents mail check` and confirmed structural message projection with `houmao-mgr project mailbox messages list/get`.
8. Stopped the temporary instance after verification.

### Delivery Evidence

- `houmao-mgr agents mail send` returned an authoritative result with `execution_path=manager_direct` and `status=verified`.
- Canonical message id: `msg-20260330T050646Z-de5702b2499e4e52a0e3aadd50cd67a6`
- Subject: `HTT self-mail 20260330-050155`
- Body: `Self mailbox roundtrip from claude-self-050155 at 2026-03-30T05:01:55Z.`
- The message was visible in both `inbox` and `sent` projections under the project mailbox root.

### Important Caveat

- The old `MailboxResultParseError` failure from the 2026-03-29 run did not reproduce on this commit.
- During the rerun, `houmao-mgr agents mailbox register --agent-name claude-self-050155` defaulted to the global mailbox root and `AGENTSYS-claude-self-050155@agents.localhost`.
- To keep this testcase on the project-local mailbox path, the successful rerun used explicit `--mailbox-root`, `--principal-id`, and `--address` overrides on the late mailbox registration step.

# Test Case: Project Easy Claude Gateway Mail Wakeup Output

**Timestamp:** 2026-03-30 05:41:19 UTC
**Case slug:** `project-easy-claude-gateway-mail-wakeup-output`
**Primary workflow:** `houmao-mgr project easy` end-to-end TUI mailbox wake-up through a live gateway
**Execution mode:** hack-through-testing

## Goal

Verify a clean-start project can create a Claude Code specialist for gateway-driven mailbox wake-up, provision a filesystem mailbox, start the agent in TUI mode, attach a live gateway with mail-notifier polling, inject one operator-originated mailbox message into the agent inbox, observe the gateway pick up the unread message and wake the agent, have the agent process the mail, create one visible artifact under the repo-root `tmp/` directory, and mark the source message read.

## Scenario

1. Delete project-local `.houmao/` to guarantee a clean start.
2. Create a repo-root output directory under `tmp/` that the agent can write into.
3. Initialize a fresh project overlay.
4. Create a Claude Code specialist with a mailbox-aware system prompt that explicitly tells the agent how to react to gateway-notified unread mail.
5. Create a project-local filesystem mailbox root.
6. Create or prepare the agent mailbox account under that project mailbox root.
7. Create or prepare one operator mailbox account that will act as the sender.
8. Start the Claude agent in TUI mode with filesystem mailbox wiring.
9. Rebind the running instance to the project mailbox identity if late registration defaults drift to the global mailbox root.
10. Attach a live gateway to the running agent and enable gateway mail-notifier polling.
11. Send one operator-originated mailbox message addressed to the agent through the filesystem mailbox delivery helper.
12. Watch the gateway detect the unread message and wake the agent.
13. Confirm the agent creates the requested file under `tmp/`.
14. Confirm the agent-marked mailbox state is read rather than unread.

## Concrete Steps To Drive

1. `rm -rf .houmao tmp/project-easy-gateway-mail-wakeup-output`
2. `mkdir -p tmp/project-easy-gateway-mail-wakeup-output`
3. Write `tmp/project-easy-gateway-mail-wakeup-output/system-prompt.md` with instructions equivalent to:
   - when gateway wake-up or unread mailbox work arrives, inspect the actionable unread message
   - follow the message instructions exactly if they request one file write under the repo-root `tmp/` directory
   - after the requested work succeeds, mark the processed source message read
   - do not fabricate success if the file write fails
4. `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr project init`
5. Import the Claude fixture auth bundle into the fresh project overlay:
   - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr project agents tools claude auth add --name kimi-coding ...`
6. Create the specialist with that prompt:
   - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr project easy specialist create --name claude-gateway-<run-id> --tool claude --credential kimi-coding --system-prompt-file tmp/project-easy-gateway-mail-wakeup-output/system-prompt.md`
7. `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr project mailbox init`
8. Register the agent mailbox address:
   - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr project mailbox register --address claude-gateway-<run-id>@agents.localhost --principal-id claude-gateway-<run-id>`
9. Register one operator sender address:
   - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr project mailbox register --address operator@agents.localhost --principal-id operator`
10. Launch the agent in TUI mode with the project mailbox root:
    - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr project easy instance launch --specialist claude-gateway-<run-id> --name claude-gateway-<run-id> --yolo --mail-transport filesystem --mail-root /data1/huangzhe/code/houmao/.houmao/mailbox`
11. Rebind the running instance explicitly to the project mailbox identity:
    - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr agents mailbox register --agent-name claude-gateway-<run-id> --mailbox-root /data1/huangzhe/code/houmao/.houmao/mailbox --principal-id claude-gateway-<run-id> --address claude-gateway-<run-id>@agents.localhost --mode force`
12. Attach the gateway and enable notifier polling:
    - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr agents gateway attach --foreground --agent-name claude-gateway-<run-id>`
    - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr agents gateway mail-notifier enable --interval-seconds 5 --agent-name claude-gateway-<run-id>`
13. Verify gateway readiness before delivery:
    - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr agents gateway status --agent-name claude-gateway-<run-id>`
    - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr agents gateway mail-notifier status --agent-name claude-gateway-<run-id>`
14. Write one inbound operator message body file at `tmp/project-easy-gateway-mail-wakeup-output/operator-body.md` that tells the agent to create:
    - `/data1/huangzhe/code/houmao/tmp/project-easy-gateway-mail-wakeup-output/processed-<run-id>.md`
    - The body should tell the agent to write a short deterministic payload that includes the mail subject or run id, then mark the source mail read.
15. Deliver that operator-originated message into the project mailbox root using one managed delivery helper flow. One concrete option is:
    - create one staged message document under `.houmao/mailbox/staging/`
    - create one JSON payload file with `staged_message_path`, `message_id`, `thread_id`, `created_at_utc`, sender `operator@agents.localhost`, recipient `claude-gateway-<run-id>@agents.localhost`, and the chosen subject
    - run:
      - `pixi run python .houmao/mailbox/rules/scripts/deliver_message.py --mailbox-root /data1/huangzhe/code/houmao/.houmao/mailbox --payload-file tmp/project-easy-gateway-mail-wakeup-output/delivery-payload.json`
16. Watch the gateway react after delivery:
    - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr agents gateway tui watch --agent-name claude-gateway-<run-id>`
    - Stop watching once the gateway shows a wake-up / active-execution transition or the requested output file appears.
17. Verify the artifact requested by the inbound mail now exists under:
    - `/data1/huangzhe/code/houmao/tmp/project-easy-gateway-mail-wakeup-output/processed-<run-id>.md`
18. Verify the mailbox state after processing:
    - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr agents mail check --agent-name claude-gateway-<run-id> --limit 10`
    - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr agents mail check --agent-name claude-gateway-<run-id> --unread-only --limit 10`
    - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr project mailbox messages list --address claude-gateway-<run-id>@agents.localhost`
    - `pixi run --manifest-path /data1/huangzhe/code/houmao houmao-mgr project mailbox messages get --address claude-gateway-<run-id>@agents.localhost --message-id <delivered-message-id>`

## Expected Success Signals

- `.houmao/` is recreated from scratch and contains the project overlay.
- The Claude specialist is persisted and resolvable through `project easy specialist get`.
- The project mailbox root is initialized successfully.
- Both the agent mailbox account and the operator sender mailbox account are active under the project mailbox root.
- `project easy instance get` shows the running agent bound to the project mailbox root and project mailbox address rather than the global mailbox root.
- `houmao-mgr agents gateway status` shows one live attached gateway for the running agent.
- `houmao-mgr agents gateway mail-notifier status` shows notifier polling enabled for that gateway.
- The operator-originated delivery succeeds and returns one canonical message id.
- Gateway watch/state output shows the gateway observed the unread message and the agent transitioned into processing work.
- The agent creates the requested file under `tmp/project-easy-gateway-mail-wakeup-output/`.
- `agents mail check --unread-only` returns zero actionable unread messages after the agent finishes.
- `project mailbox messages list/get` show the delivered message projected into the mailbox and marked read.

## Expected Failure Signals

- Specialist creation fails because Claude auth/setup defaults are incomplete.
- Mailbox root initialization or project mailbox registration fails.
- The late mailbox registration step drifts to the global mailbox root and is not corrected before gateway attach.
- Gateway attach fails or no live gateway is available.
- Mail-notifier enablement fails or never becomes active.
- The operator-originated filesystem mailbox delivery helper fails validation or delivery.
- The gateway remains idle after delivery and never wakes the agent.
- The agent reads the mail but does not create the requested output file under `tmp/`.
- The output file exists but its content does not match the instruction carried by the inbound mail.
- The source message remains unread after the agent appears to finish.

## Notes

- This case intentionally extends the clean-start project-easy mailbox roundtrip by adding one live gateway and one operator-originated inbound mail event after launch.
- Use a fresh `<run-id>` in the specialist name, mailbox address, subject, and output filename so artifacts from previous runs cannot be mistaken for the current run.
- The operator-originated mail should remain filesystem-backed for this case; do not pivot to Stalwart unless the run explicitly discovers a blocker that requires it.
- Use a repo-root output path under `tmp/` so the resulting artifact is easy to inspect manually after the run.
- Prefer checking mailbox read state through both `agents mail check` and `project mailbox messages list/get`; the testcase should treat `unread_count == 0` plus `read: true` for the delivered message as the mailbox-side completion signal.

## Latest Result

**Last run:** 2026-03-30 05:48:19 UTC
**Tested commit:** `330bfca80f330fc14d46521900fc50475fac87d2`
**Outcome:** partial

### Observed Success Path

1. Removed the project-local `.houmao/` overlay and the run-local `tmp/project-easy-gateway-mail-wakeup-output/` directory, then re-ran `houmao-mgr project init`.
2. Imported the Claude fixture auth bundle and created specialist `claude-gateway-054819`.
3. Initialized the project mailbox root and registered both `claude-gateway-054819@agents.localhost` and `operator@agents.localhost`.
4. Launched a TUI instance for `claude-gateway-054819` and rebound it explicitly to the project mailbox root and project mailbox identity.
5. Attached a live foreground gateway and enabled gateway mail-notifier polling.
6. Delivered one operator-originated mailbox message with subject `HTT gateway wakeup 054819` into the project mailbox root.
7. Observed the gateway notifier enqueue and complete one wake-up request for that unread mail.
8. Verified the agent created `/data1/huangzhe/code/houmao/tmp/project-easy-gateway-mail-wakeup-output/processed-054819.md` with content `gateway-mail-wakeup-output 054819`.
9. Verified `houmao-mgr agents mail check` reported the delivered message as `unread: false` and `unread_count: 0`.

### Delivery And Wake-Up Evidence

- Delivered message id: `msg-20260330T055257Z-720c3085a2a74db195cc31eb83d4cba3`
- Gateway pane evidence:
  - `2026-03-30T05:53:02+00:00 mail notifier enqueued request_id=gwreq-20260330-055302Z-d0b5464f unread_count=1`
  - `2026-03-30T05:53:02+00:00 completed gateway request request_id=gwreq-20260330-055302Z-d0b5464f`
- Final notifier status recorded `last_notification_at_utc: 2026-03-30T05:53:02+00:00`
- Final manager-owned mailbox check recorded:
  - `message_ref: filesystem:msg-20260330T055257Z-720c3085a2a74db195cc31eb83d4cba3`
  - `unread: false`
  - `unread_count: 0`

### Blocking Issue

- The testcase is only `partial` rather than `passed` because `houmao-mgr project mailbox messages list/get` still reported the same inbox message as `read: false`.
- Direct mailbox inspection showed the mailbox-local SQLite file at `.houmao/mailbox/mailboxes/claude-gateway-054819@agents.localhost/mailbox.sqlite` had `is_read = 1`, while the shared root `index.sqlite` had no `mailbox_state` row for that message.
- `src/houmao/srv_ctrl/commands/mailbox_support.py` currently reads read-state from the shared-root `mailbox_state` table, so project mailbox inspection surfaces stale unread state even though manager-owned mail check and mailbox-local state both show the message as read.

### Additional Caveat

- `houmao-mgr agents gateway mail-notifier enable` failed once immediately after `gateway attach` with `No live gateway is attached to the managed agent`, then succeeded on immediate retry once gateway status had stabilized.

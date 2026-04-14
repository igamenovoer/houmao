## Why

The mailbox workflow currently treats read/unread as both "seen" state and completion state. When an agent sends an acknowledgement before doing the real work, the message can be marked read and then stop triggering notifier wake-ups even though it has not been processed.

## What Changes

- **BREAKING**: Separate mailbox lifecycle concepts so `read` means body/metadata has been consumed, `answered` means the message has received a reply or acknowledgement, and `archive` means the message is processed and closed.
- Add an active `archive/` mailbox box per account and make archive a first-class message move target instead of a placeholder directory.
- Replace unread-only `check` and read-only state mutation assumptions with box-oriented list, peek, read, mark, move, and archive workflows.
- Keep `POST /v1/mail/archive` as a high-use shortcut over the general mailbox move workflow.
- Distinguish `peek` from `read` in both gateway API and CLI behavior: peeking returns message content without marking it read; reading returns content and marks it read.
- Automatically mark mailbox state at workflow boundaries: body reads mark `read`, replies and acknowledgement replies mark `answered`, and archive operations mark archive/closed state. Manual marking remains available for repair and operator-directed state changes.
- Update notifier behavior to wake on open inbox work instead of unread-only work, so read-but-unarchived and answered-but-unarchived messages remain eligible for reminders.
- Update projected skills and documentation so agents archive mail after successful processing rather than treating `mark-read` as completion.
- Do not add migration or compatibility shims for old mailbox state semantics; this system is still unstable and may break stored test mailbox state while the new model lands.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `agent-mailbox-protocol`: expand the shared mailbox state model and operation contract from unread/read handling to read, answered, box, move, peek, read, mark, and archive semantics.
- `agent-mailbox-fs-transport`: make `archive/` an active mailbox box and persist mailbox-local read, answered, and archived state while preserving immutable canonical message content.
- `agent-mailbox-stalwart-transport`: expand the Stalwart shared operation set to map read, answered, archive, box listing, and move behavior onto server-backed mail state through JMAP.
- `agent-gateway`: revise `/v1/mail/*` to expose box-oriented list, peek, read, mark, move, and archive operations, keeping `post`, `send`, and `reply` semantics transport-neutral where already supported.
- `agent-gateway-mail-notifier`: poll and prompt for open inbox work instead of unread-only work, and update the gateway endpoint list and round workflow wording.
- `agent-mailbox-system-skills`: change projected mailbox workflows from post-success mark-read to post-success archive, with peek/read and manual mark guidance.
- `houmao-agent-email-comms-skill`: update the ordinary mailbox skill action set and examples to cover list, peek, read, mark, move, and archive.
- `houmao-srv-ctrl-native-cli`: update the `houmao-mgr agents mail` command family to expose the revised mailbox lifecycle operations.
- `docs-cli-reference`: update CLI reference expectations for the revised `agents mail` subcommands and state semantics.
- `mailbox-reference-docs`: document the new lifecycle states, box model, open-work definition, and archive-as-completion workflow.
- `docs-gateway-mail-notifier-reference`: update notifier reference behavior from unread-set polling to open inbox work polling.

## Impact

- Runtime mailbox models and transport adapters under `src/houmao/mailbox/`.
- Gateway request/response models and route handlers under `src/houmao/agents/realm_controller/`.
- CLI implementation for `houmao-mgr agents mail` under `src/houmao/srv_ctrl/commands/agents/`.
- Gateway notifier polling, prompt template assets, and notifier tests.
- Runtime-owned mailbox skills under `src/houmao/agents/assets/system_skills/`.
- Unit and integration tests covering filesystem mailbox state, Stalwart adapter state mapping, gateway mailbox routes, notifier eligibility, and CLI command behavior.
- Reference documentation for mailbox, gateway, notifier, projected skills, and CLI surfaces.

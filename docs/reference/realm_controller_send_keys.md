# Raw Control Input (`send-keys`)

The current operator surface for raw control input is `houmao-mgr agents gateway send-keys`. It delivers exact key sequences through a live attached gateway to the managed agent's terminal without treating the input as a prompt turn.

Use this path for interactive TUI situations where prompt submission is the wrong abstraction: slash-command menus, partial typing, arrow-key navigation, `Escape`, or `Ctrl-*` input that must not automatically submit a turn.

The runtime routes this path through the `send_input_ex()` method on `RuntimeSessionController` and backend-specific session implementations. The gateway also exposes `POST /v1/control/send-keys` for raw input delivery via HTTP.

## When To Use `send-keys`

Use `houmao-mgr agents gateway send-keys` when you need to shape the live terminal state without asking the runtime to treat the input as a prompt turn.

Typical cases:

- open or navigate a slash-command menu
- type partial input without submitting it yet
- send `Escape` to leave a modal surface
- send arrow keys to move through a menu
- send `C-c`, `C-d`, or `C-z` to the live tool session

Use `houmao-mgr agents prompt` instead when you want normal prompt-turn behavior:

- wait for readiness before submission
- wait for completion after submission
- advance persisted prompt-turn state
- collect normal `SessionEvent` turn output

For `local_interactive` and `houmao_server_rest` backends, the distinction is explicit:

- `agents prompt` pastes the full prompt literally and submits it once at the end as one semantic provider turn
- `agents gateway send-keys` keeps exact raw key semantics, does not reinterpret literal text as prompt work, and never appends an implicit trailing `Enter`

## Scope And Output

- Supported backends include `local_interactive` and `houmao_server_rest`.
- Backends without raw control-input support return an explicit `action="control_input"` error result instead of trying to emulate prompt submission.
- The runtime routes this path through the `send_input_ex()` method on sessions.
- The CLI returns one JSON result and does not stream prompt-turn events.

Example result:

```json
{
  "action": "control_input",
  "detail": "Delivered control input to tmux target `@7`.",
  "status": "ok"
}
```

## CLI Contract

```bash
pixi run houmao-mgr agents gateway send-keys \
  --agent-name gpu \
  --sequence '/model<[Enter]><[Down]><[Enter]>'
```

Arguments:

- `--agent-name` or `--agent-id` identifies the target managed agent.
- `--sequence` is required and carries the mixed literal/control-key input string.
- `--escape-special-keys` is optional and disables special-key parsing for the full sequence.
- `--current-session` forces same-session resolution from inside the target tmux session.

## Sequence Grammar

`send-keys` accepts one sequence string composed of literal text plus exact special-key tokens written as `<[key-name]>`.

Rules:

- `key-name` is case-sensitive.
- Exact recognition requires the precise `<[key-name]>` form.
- Internal whitespace disables token recognition and leaves the substring literal.
- Marker-like text that does not match the exact form stays literal.
- `--escape-special-keys` sends the entire sequence literally, even if it contains token-like text.

Examples:

```text
/model<[Enter]><[Down]><[Enter]>
<[Escape]>
hello<[Left]><[Left]>!
```

Literal examples:

```bash
pixi run houmao-mgr agents gateway send-keys \
  --agent-name gpu \
  --sequence '/model<[Enter]>' \
  --escape-special-keys
```

The command above sends the literal characters `/model<[Enter]>` instead of generating an `Enter` keypress.

## Supported Exact Key Names

The runtime guarantees support for these exact key names:

- `Enter`
- `Escape`
- `Up`
- `Down`
- `Left`
- `Right`
- `Tab`
- `BSpace`
- `C-c`
- `C-d`
- `C-z`

Exact tokens outside the supported set fail explicitly. For example, `<[escape]>` is rejected because token matching is case-sensitive.

## Tmux-Documented Special Key Names

The local tmux 3.4 man page documents a broader key vocabulary than the subset currently guaranteed by `Houmao`.

Important distinction:

- tmux accepts more special key names than the runtime currently allows
- `Houmao` currently guarantees only the exact keys listed in the previous section
- treat the lists below as tmux reference material, not as a promise that every tmux key name is already accepted by runtime `send-keys`

### Modifier Prefixes

These prefixes can be combined with many keys:

- `C-`: Control, for example `C-c` or `C-a`
- `S-`: Shift, for example `S-Left`
- `M-`: Alt/Meta, for example `M-Left` or `M-a`

### Navigation Keys

- `Up`: move up
- `Down`: move down
- `Left`: move left
- `Right`: move right
- `Home`: move to the beginning or home position
- `End`: move to the end position
- `NPage`, `PageDown`, `PgDn`: Page Down aliases
- `PPage`, `PageUp`, `PgUp`: Page Up aliases

### Editing And Input Keys

- `BSpace`: Backspace
- `BTab`: back-tab, typically Shift+Tab
- `DC`: Delete
- `IC`: Insert
- `Enter`: Return/Enter
- `Escape`: Escape key
- `Tab`: Tab
- `Space`: Space bar

### Function Keys

- `F1` through `F12`: function keys

## Delivery Semantics

The runtime preserves the left-to-right sequence order and never appends an implicit trailing `Enter`.

Delivery rules:

- literal text segments are sent with `tmux send-keys -l`
- exact special-key tokens are sent with normal `tmux send-keys`
- submit behavior only happens when the caller explicitly includes `<[Enter]>`

That means these commands stay meaningfully different:

- `agents gateway send-keys --sequence '/model'`
  This types `/model` and stops.
- `agents gateway send-keys --sequence '/model<[Enter]>'`
  This types `/model` and then presses `Enter`.
- `agents prompt --prompt '/model<[Enter]>'`
  This submits the literal text `/model<[Enter]>` as one semantic prompt turn.

## Tmux Target Resolution

Callers continue to address sessions by `agent_identity`; they do not provide raw tmux targets.

The runtime resolves the live tmux destination like this:

1. resolve `--agent-identity` to the persisted session manifest and effective agent-definition root
2. read persisted backend state from that manifest
3. reuse the `tmux_window_name` when available
4. fall back to live terminal metadata when older manifests do not yet persist the window name
5. resolve the tmux window in the session and send the requested control input

This keeps older manifests usable without a schema-version bump.

## Failure Modes

`send-keys` returns explicit control-input errors for:

- unsupported backends
- empty sequences
- unsupported exact tokens such as `<[escape]>`
- tmux resolution failures
- tmux send failures
- terminal metadata failures during live fallback

## Low-Level Access

The underlying runtime module CLI still supports `send-keys` for advanced targeting or scripting:

```bash
pixi run python -m houmao.agents.realm_controller send-keys \
  --agent-identity AGENTSYS-gpu \
  --sequence '/model<[Enter]><[Down]><[Enter]>'
```

The raw module accepts `--agent-identity` (name or manifest path) and `--agent-def-dir` for explicit override. Use `houmao-mgr agents gateway send-keys` for standard operator work.

## Related Reference

- [houmao-mgr agents gateway](cli/agents-gateway.md)
- [Realm Controller](./realm_controller.md)

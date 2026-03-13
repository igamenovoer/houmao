# Realm Controller `send-keys`

`send-keys` is the raw control-input command for resumed `backend=cao_rest` runtime sessions. It exists for interactive TUI situations where `send-prompt` is the wrong abstraction, such as slash-command menus, partial typing, arrow-key navigation, `Escape`, or `Ctrl-*` input that must not automatically submit a turn.

## When To Use `send-keys`

Use `send-keys` when you need to shape the live terminal state without asking the runtime to treat the input as a prompt turn.

Typical cases:

- open or navigate a slash-command menu
- type partial input without submitting it yet
- send `Escape` to leave a modal surface
- send arrow keys to move through a menu
- send `C-c`, `C-d`, or `C-z` to the live tool session

Use `send-prompt` instead when you want normal prompt-turn behavior:

- wait for readiness before submission
- wait for completion after submission
- advance persisted prompt-turn state
- collect normal `SessionEvent` turn output

## Scope And Output

- Initial support is intentionally limited to resumed `backend=cao_rest` sessions.
- Non-CAO backends return an explicit `action="control_input"` error result instead of trying to emulate prompt submission.
- The runtime routes this path through the advanced backend method `send_input_ex()`.
- The CLI returns one JSON `SessionControlResult` object and does not stream prompt-turn events.

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
pixi run python -m houmao.agents.realm_controller send-keys \
  --agent-identity AGENTSYS-gpu \
  --sequence '/model<[Enter]><[Down]><[Enter]>'
```

Arguments:

- `--agent-identity` is required and accepts the same name-or-manifest-path values used by other runtime control commands.
- `--sequence` is required and carries the mixed literal/control-key input string.
- `--escape-special-keys` is optional and disables special-key parsing for the full sequence.
- `--agent-def-dir` remains an explicit override. For name-based tmux control, omitting it makes runtime recover the effective agent-definition root from the addressed session's `AGENTSYS_AGENT_DEF_DIR`. Manifest-path control still uses the ambient resolution rules documented in [Realm Controller](./realm_controller.md).

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
pixi run python -m houmao.agents.realm_controller send-keys \
  --agent-identity AGENTSYS-gpu \
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

That means these two commands are different:

- `--sequence '/model'`
  This types `/model` and stops.
- `--sequence '/model<[Enter]>'`
  This types `/model` and then presses `Enter`.

## Tmux Target Resolution

Callers continue to address sessions by `agent_identity`; they do not provide raw tmux targets.

For resumed CAO sessions the runtime resolves the live tmux destination like this:

1. resolve `--agent-identity` to the persisted session manifest and effective agent-definition root
2. read persisted CAO state from that manifest
3. reuse `cao.tmux_window_name` when available
4. fall back to live `GET /terminals/{id}` metadata when older manifests do not yet persist the window name
5. resolve the tmux window in the session and send the requested control input

This keeps older manifests usable without a schema-version bump.

## Failure Modes

`send-keys` returns explicit control-input errors for:

- unsupported backends
- empty sequences
- unsupported exact tokens such as `<[escape]>`
- tmux resolution failures
- tmux send failures
- CAO terminal metadata failures during live fallback

## Related Reference

- [Realm Controller](./realm_controller.md)

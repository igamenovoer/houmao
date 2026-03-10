# How to handle special keys and literal strings with tmux send-keys

When automating commands or interacting with terminal sessions via `tmux`, the `send-keys` command is used to simulate keypresses. By default, `tmux` interprets exact matches of specific strings as special keypresses instead of literal text.

## Representing Special Keys

Special keys and control combinations have designated names in `tmux`:
- **Escape key:** `Escape`
- **Arrow keys:** `Up`, `Down`, `Left`, `Right`
- **Control keys:** `C-c` (Ctrl+C), `C-d` (Ctrl+D), `C-m` (Equivalent to Enter)
- **Other common keys:** `Enter`, `Space`, `Tab`
- **Meta/Alt keys:** `M-Up`, `M-x`

Example of sending a mix of text and special keys:
```bash
# Types 'ls -la' and then presses the Enter key
tmux send-keys -t my_session "ls -la" Enter

# Sends a Ctrl+C interrupt
tmux send-keys -t my_session C-c
```

## Sending Literal Strings (Escaping Special Keys)

If you need to send the literal word "Escape", "Enter", or "Space" into the terminal without triggering the actual key press, you can use the `-l` (literal) flag. The `-l` flag disables key name lookup and processes everything as literal UTF-8 characters.

```bash
# Types out the letters "E-s-c-a-p-e" instead of pressing the escape key
tmux send-keys -t my_session -l "Escape"
```

## Mixing Literal Strings and Special Keys in a Single Command

Often, you need to send a mix of literal text (that might even contain special key names) alongside actual keypresses. There are two main ways to accomplish this cleanly in a single `tmux` invocation.

### Method 1: Chaining multiple `send-keys` commands

You can string multiple `tmux` commands together within a single execution using `\;`. This allows you to toggle the `-l` flag on and off for specific segments of your input.

```bash
# Sends the literal word "Escape", then a literal space and string, and finally presses the Enter key
tmux send-keys -t my_session -l "Escape" \; send-keys -t my_session " is a literal word" Enter
```

### Method 2: Splitting the string

`tmux` only evaluates an argument as a special key if it is an *exact, full-word match*. Furthermore, `tmux` concatenates multiple unrecognised arguments without adding spaces between them. You can easily bypass the special key lookup by simply splitting the "dangerous" word across two arguments.

```bash
# "Es" and "cape" are not special key names, so tmux sends them literally, forming "Escape"
tmux send-keys -t my_session "Es" "cape" " is the key!" Enter
```

## References
- [tmux(1) man page - send-keys](https://man7.org/linux/man-pages/man1/tmux.1.html#COMMANDS)

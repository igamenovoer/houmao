# Tasks

## 1. Managed Tmux Attachment

- [x] 1.1 Resolve the active gateway owner's saved tmux binding and verify the live managed session, native session ID, and server incarnation across TUI and supervised modes. Test missing and stale authority, inherited selectors for a different socket, and identity reuse after a tmux server restart.
- [x] 1.2 Add the fixed attach invocation and final native identity check, applying viewer flags and safe detach admission. Test a replacement between preflight and attach on an isolated socket, viewer geometry and focus preservation, and effective tmux options that would destroy or switch the session.
- [x] 1.3 Build the standard-library PTY adapter and bounded duplex stream. Test controlling-terminal I/O, Unicode and paste bytes, admin resize, rejection of crafted viewer input and resize, and stalled-browser backpressure.
- [x] 1.4 Tie PTY and attach-client cleanup to all exit paths. Test failure or disconnection during startup, child exit, gateway shutdown, and preservation of the live agent and a native client on the same isolated server.

## 2. Gateway Entry and Authorization

- [x] 2.1 Register the exact HTTP and WebSocket operations on the gateway listener and enforce the direct owner-local transport. Test valid same-origin entry and rejection of wrong hosts, cross-origin WebSockets, forwarded ingress, passive relays, and unclassified routes. Run existing native Web and plugin route regression tests.
- [x] 2.2 Register the anonymous `terminal.view` read effect and admin-exclusive `admin.terminal.interact` effect. Require current per-key administrator proof for interaction. Test anonymous view on open and keyed gateways, and open, scoped, default, self, and enrolled administrator interaction decisions, including a retained `agent-admin` default, without changing first-key enrollment.
- [x] 2.3 Implement terminal-specific SSHSIG login and bounded one-time connection grants for both modes. Test mode substitution, cross-purpose and wrong-listener tickets, replay, claim binding, expiry, candidate-key ordering, and rejection before any PTY allocation.
- [x] 2.4 Revalidate the exact authorization and session throughout the stream and document both terminal route families and anonymous viewing in the gateway reference. Test view continuity through roster changes, admin removal including the last admin, agent generation replacement, ticket secrecy, and absence of terminal bytes from general logs.

## 3. Bundled Viewer and Operator Entry Points

- [x] 3.1 Vendor the pinned browser runtime files and license notices in the package and document how to refresh them. Verify the resource files, checksums, and notices are present in both the wheel and source distribution.
- [x] 3.2 Implement the browser page with read-only and interactive modes, same-origin assets, resize and flow acknowledgments where allowed, and clear disconnect status. Test real browser rendering, typing, paste, resize, and server-enforced read-only behavior using an isolated tmux server.
- [x] 3.3 Add independent viewer and admin actions to the dashboard and document how to open the terminal through the owner-local gateway or a private TCP forward. Test dual-surface Web agents, open and keyed rosters, non-tmux agents, policy failure, and the side-effect-free public dashboard.
- [x] 3.4 Add the scoped `gateway terminal-entry` CLI with `--interact`, optional `--signer`, and URL, mode, and expiry output. Update help and manager reference. Test agent selectors, plain and JSON output, unauthorized interaction, and missing or replaced gateway without automatic attachment or another listener.

## 4. End-to-End Qualification

- [x] 4.1 Exercise the installed gateway through both dashboard and CLI with one existing listener. Cover an eligible Hermes TUI, a supervised agent with native Web entry, and an eligible headless or service console. Verify native mode and provider Web behavior through browser disconnect and gateway shutdown.
- [x] 4.2 Build a wheel directly and from the source distribution in a Python-only build environment. Exercise the installed browser terminal from each artifact with network access limited to the local gateway and no Node, Bun, or ttyd on the runtime path. Run the focused gateway and tmux suites, lint, typecheck, and strict OpenSpec validation.

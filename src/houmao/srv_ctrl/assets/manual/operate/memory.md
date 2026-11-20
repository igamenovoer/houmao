# Preserve Agent Context

Use a live agent's memo for standing instructions and current facts that should survive a session stop. Read it with `memory memo show`. Use `memory memo append` for an addition or `memory memo set` for an intended replacement. Use files under `pages/` for longer notes and link to them from the memo. Inspect with `memory tree` and retrieve a page with `memory read`.

For reusable launch-time notes, set a memo seed on the project profile. A launch from that profile applies the stored seed before the provider starts. Put task deliverables in the designated workdir or artifact location.

Verify a live update by rereading the memo or page for the same agent. Verify a seed in the selected profile and check the memo after launch. `houmao-mgr agents self memory --help` shows the current-session commands. [Managed Agent Memory](https://igamenovoer.github.io/houmao/getting-started/managed-memory-dirs/)

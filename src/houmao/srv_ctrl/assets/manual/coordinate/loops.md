# Choose and Start a Recurring Loop

Use a loop when workers should repeat a handoff with durable state and an explicit recovery path. For a single operator-run round, read `houmao-mgr manual coordinate team`.

- Choose **Lite** for Markdown contracts, direct SQLite state, and generated skills.
- Choose **Pro** for schema-rich topology, graph validation, and harness-backed execution.

Define the participants, trigger, handoff, completion rule, and recovery expectations. Follow the Loop Authoring Guide to prepare the workers and their workspaces, validate the plan, and launch the workers. Use the loop's generated controls to start it explicitly and check its status. Worker readiness confirms launch. The loop's status and durable records show whether a trigger reached the intended worker and was handled.

For a mailbox-driven loop, use the notifier to wake workers for bounded rounds. After each round the worker ends its turn so it can receive the next wakeup. See `houmao-mgr manual communicate wakeups` for mailbox handling and `houmao-mgr agents single --agent-id <id> gateway mail-notifier --help` for notifier syntax. [Loop Authoring Guide](https://igamenovoer.github.io/houmao/getting-started/loop-authoring/)

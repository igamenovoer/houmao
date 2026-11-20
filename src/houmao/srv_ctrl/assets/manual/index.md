# Houmao Operator Manual

Use this manual to choose a Houmao workflow and verify its result. The manager launches and controls workers through their supported native interfaces. Use each command's `--help` for its arguments and options.

## Common Requests

- Launch a reviewer for this repository. `houmao-mgr manual start first-agent`
- Find the workers and profiles I already have. `houmao-mgr manual start existing-project`
- Ask a worker to do something and check its result. `houmao-mgr manual operate turns`
- Leave a durable note for a worker. `houmao-mgr manual communicate mail`
- Have a builder and reviewer work together. `houmao-mgr manual coordinate team`

## Catalogs

- `houmao-mgr manual start` covers first use, existing projects, and selecting the right target.
- `houmao-mgr manual prepare` covers credentials, reusable definitions, and launch choices.
- `houmao-mgr manual operate` covers inspection, work submission, lifecycle, and memory.
- `houmao-mgr manual communicate` covers mail, mailbox bindings, gateways, and wakeups.
- `houmao-mgr manual coordinate` covers operator-directed teams, workspaces, and recurring loops.

## 1. Native CLI reminder commands

- [x] 1.1 Add `agents gateway reminders` command registration, shared selector plumbing, and local managed-agent execution paths for `list`, `get`, `create`, `set`, and `remove`.
- [x] 1.2 Implement `create` and `set` argument parsing for prompt vs `send_keys` reminders, one-off vs repeat timing, and mutually exclusive ranking modes (`--ranking`, `--before-all`, `--after-all`).
- [x] 1.3 Implement live ranking resolution and CLI-side patch behavior so convenience placement flags compute concrete numeric rankings and `set` preserves unspecified reminder fields before issuing the gateway `PUT`.
- [x] 1.4 Add plain and fancy reminder renderers for list/get/create/set/remove results while preserving `--print-json` passthrough payloads.

## 2. Pair-managed reminder proxy support

- [x] 2.1 Add passive-server app routes and service handlers for managed-agent gateway reminder list/create/get/update/delete operations.
- [x] 2.2 Add passive-server client and pair-client reminder methods, then route `--pair-port` reminder commands through those proxy endpoints with existing gateway-style error handling.

## 3. Skill and reference updates

- [x] 3.1 Update the packaged `houmao-agent-gateway` skill router and reminder guidance so it teaches the native reminder CLI and managed-agent proxy surfaces before raw `/v1/reminders` HTTP.
- [x] 3.2 Update the CLI and gateway reference docs to document the reminder subcommands, selector rules, numeric ranking behavior, and `--before-all` / `--after-all` convenience placement.

## 4. Regression coverage and verification

- [x] 4.1 Add or update CLI tests for reminder command parsing, ranking resolution, patch-like `set` behavior, and human-readable reminder rendering.
- [x] 4.2 Add or update passive-server and pair-client tests for reminder proxy routes, success payloads, and no-gateway / ambiguous-target failures.
- [x] 4.3 Run focused verification for the new reminder CLI surface and proxy support, including the relevant `pixi run pytest` coverage and lint checks for touched files.

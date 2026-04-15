# What Project Context Changes

Use this reference when the question is what other `houmao-mgr` subcommands do differently once a project overlay exists.

## Project-Aware Defaults

When a project overlay is selected, Houmao resolves project-local defaults from that overlay for these roots:

- agent-definition tree
- runtime root
- managed-agent memory root
- mailbox root
- easy root

## Command Families Affected

- `houmao-mgr brains build` uses the project-aware agent-definition tree and overlay-local runtime roots unless an explicit override wins.
- `houmao-mgr agents launch` uses the selected project as the source for preset or launch-profile resolution and overlay-local runtime, managed-agent memory, and mailbox defaults.
- `houmao-mgr agents join`, `houmao-mgr agents list`, and `houmao-mgr agents state` use project-aware maintained roots when they need shared runtime state.
- `houmao-mgr mailbox ...` uses the project-local mailbox root by default when an explicit mailbox-root override is absent.
- `houmao-mgr server start` uses the project-local runtime root by default.
- `houmao-mgr admin cleanup runtime ...` targets the project-local runtime root by default.

## Important Distinction

- Project existence changes default resolution for these other command families.
- It does not mean every `project ...` command bootstraps missing state automatically.
- When the selected overlay does not exist yet, some stateful project-aware flows will bootstrap it, while non-creating inspection flows report or fail against the missing overlay instead.

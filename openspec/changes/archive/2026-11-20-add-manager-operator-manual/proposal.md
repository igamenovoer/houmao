# Proposal

## Why

An agent with only `houmao-mgr` can look up command syntax, but it lacks the workflow guidance the Houmao entrypoint skills supply. Package that guidance with the manager so agents can identify the next operation and verify its result without installing the skills.

## What Changes

- Add `houmao-mgr manual` with a task-oriented index, catalog indexes, and individually callable pages. Advertise it in manager help and the CLI reference.
- Cover first use, existing projects, launch preparation, live control, communication, recovery, and team coordination. Draw on the operator and managed-agent entrypoints for common user intents and operating rules.
- Teach each decision through a short workflow, expected evidence, and pointers to existing command help or detailed reference material.
- Ship the indexes and pages as standalone Markdown resources. Source code registers the command tree and loads the selected resource from the installed package.

## Capabilities

### New Capabilities

- `houmao-mgr-operator-manual` provides offline, task-oriented operating guidance through the installed manager CLI.

### Modified Capabilities

- `docs-cli-reference` documents how to discover and read the operator manual from the manager CLI reference.

## Impact

The change adds a Click command family, packaged Markdown resources, CLI and distribution checks, and a short section in the manager reference. The manual covers workflows using the existing manager operations and points readers to the established documentation for generated loop authoring and execution.

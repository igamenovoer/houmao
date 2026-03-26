## 1. Shared naming contract

- [x] 1.1 Replace the default tmux session-name derivation helper so it generates `<canonical-agent-name>-<epoch-ms>` instead of `<canonical-agent-name>-<agent-id-prefix>`.
- [x] 1.2 Update the shared default-name collision path to raise an explicit conflict error when the generated timestamp-based tmux session name is already occupied.
- [x] 1.3 Add validation that rejects user-provided managed-agent names beginning with `AGENTSYS` plus a separator, case-insensitively, while allowing later or alphanumeric-extended occurrences.
- [x] 1.4 Preserve explicit caller-provided tmux session names as an override that bypasses the default-name generator.

## 2. Managed launch integration

- [x] 2.1 Update tmux-backed managed launch flows, including the serverless `local_interactive` path used by `houmao-mgr agents launch`, to use the shared timestamp-based default when `--session-name` is omitted.
- [x] 2.2 Ensure launch-time identity and manifest persistence continue to record the actual tmux session handle without reverse-parsing the timestamp suffix.
- [x] 2.3 Align launch-time error messages and CLI/operator output with the new reserved-prefix validation and explicit conflict behavior for generated default names.
- [x] 2.4 Verify the implementation does not add tmux-name parsing or raw tmux-list-driven discovery for managed-agent listing or agent-to-session mapping.
- [x] 2.5 Update `houmao-mgr` post-launch targeting validation so `--agent-name` accepts only the raw creation-time name and rejects canonical `AGENTSYS-...` forms.

## 3. Verification and docs

- [x] 3.1 Update unit or integration coverage for reserved-prefix managed-agent name rejection, raw `--agent-name` targeting, default tmux session-name generation, explicit override handling, and generated-name conflict failure.
- [x] 3.2 Update runtime identity and `houmao-mgr` operator docs to describe the new `AGENTSYS-<agent_name>-<epoch-ms>` default naming rule, to state that discovery/mapping continue to go through the shared registry, and to instruct operators to target agents by the raw creation-time name.
- [x] 3.3 Verify the affected launch paths still behave correctly for serverless interactive and tmux-backed headless sessions after the naming change.

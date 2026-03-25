## 1. Local Agent Addressing

- [ ] 1.1 Enforce shared-registry identity rules where `agent_id` is globally unique, `agent_name` is non-unique friendly metadata, and both fields are filesystem-safe and URL-safe.
- [ ] 1.2 Ensure launch accepts required `--agent-name` and optional `--agent-id`, deriving effective `agent_id = md5(agent_name).hexdigest()` when omitted.
- [ ] 1.3 Reshape managed-agent-targeting `houmao-mgr agents` commands to accept exactly one of `--agent-id` or `--agent-name` when explicit target selection is required.
- [ ] 1.4 Extend local registry-first managed-agent resolution to support exact `agent_id`, unique `agent_name`, and unique exact `terminal.session_name` as a local convenience alias.
- [ ] 1.5 Make ambiguous friendly-name and tmux-session alias resolution fail with explicit candidate metadata instead of silently falling through.
- [ ] 1.6 Update `houmao-mgr agents launch` success output to surface `agent_name`, effective `agent_id`, `tmux_session_name`, and `manifest_path` distinctly.

## 2. Runtime Prompt And Send-Keys Split

- [ ] 2.1 Split `local_interactive` runtime semantics into separate semantic prompt-submission and raw control-input methods.
- [ ] 2.2 Make `send_prompt` treat the full prompt as literal text and auto-submit once at the end without parsing `<[key-name]>` tokens.
- [ ] 2.3 Implement submit-aware prompt delivery for `local_interactive` using tmux paste-buffer insertion with bracketed-paste support plus a separate final submit phase.
- [ ] 2.4 Keep raw `send_keys` on the existing exact `<[key-name]>` contract with no implicit Enter or prompt-submission behavior.

## 3. Gateway Prompt And Send-Keys Split

- [ ] 3.1 Add separate gateway adapter and HTTP handling for raw send-keys control instead of routing it through semantic prompt submission.
- [ ] 3.2 Keep `submit_prompt` on the queued semantic gateway request path with literal-only prompt semantics and one automatic final submit.
- [ ] 3.3 Ensure local-interactive gateway prompt execution calls the runtime semantic prompt method only, while raw send-keys uses the dedicated control path.
- [ ] 3.4 Ensure gateway-owned TUI prompt tracking records semantic prompt submissions but not raw send-keys control actions.

## 4. Verification And Documentation

- [ ] 4.1 Add or update tests covering `--agent-id` versus `--agent-name` targeting, non-unique friendly-name ambiguity, tmux-session alias resolution, and the new launch output identity summary.
- [ ] 4.2 Add or update runtime and gateway tests covering the split between literal `send_prompt` auto-submit behavior and raw `<[key-name]>` `send_keys` behavior for `local_interactive`.
- [ ] 4.3 Update workflow and reference docs for serverless `houmao-mgr agents` launch/gateway operation so operators can discover the correct control ref and understand when to use prompt versus send-keys.

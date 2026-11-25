# Tasks

## 1. Owner Access Feedback

- [x] 1.1 Render open and keyed grant/revoke guidance and the open `access init` enrollment hint from the existing result snapshots in `agents/access.py`. Extend `test_gateway_access_commands.py` to verify the stored effect, detached and already-initialized policy, the stderr hint, and the existing stdout and exit behavior.
- [x] 1.2 Update the access operations reference and the packaged `houmao-agent-access` policy and provisioning guidance. Check that each points to the existing owner inspection or first-admin command and describes its verified attached gateway prerequisite where applicable.

## 2. File Signer and Refusal Diagnostics

- [x] 2.1 Add mode-aware guidance at the verified target selection in `agents/files.py`. Add CLI regression coverage for missing selection on keyed mounts, reads, and pushes, for unavailable policy, and for explicit signer and unsigned requests. Verify the keyed preflight sends no file operation and selects no replacement credential.
- [x] 2.2 Carry recognized access error codes through `gateway_client.py` and `GatewayHttpError`. Extend `test_gateway_client.py` with bounded 401 and 403 examples and malformed, unknown, or oversized replies. Verify original status and generic fallback details.
- [x] 2.3 Render status, recognized reason, validated action and mount, and safe caller selection at the file CLI. Test the denied peer push and discovery without an exact resource. Check that diagnostics omit raw bodies and private paths, and that a refusal still makes one attempt and exits nonzero. Update the CLI reference and packaged files discovery guidance with the supported signer and owner inspection steps.

## 3. Busy Publication Feedback

- [x] 3.1 Add stderr recovery advice after emitting a confirmed busy receipt. Test signed managed self, peer, owner, and unsigned self. Verify receipt JSON, exit behavior, and the absence of automatic retry or enqueue. Exercise queued and unconfirmed results to check that their original operation IDs and outcomes remain usable.
- [x] 3.2 Update the versioned-file operations reference and packaged files publication guidance. Check that the documented recovery uses the saved candidate, recorded base, and a fresh operation ID, and that `--when-idle` appears as an explicit managed-self action.

## 4. Owner State and Public Dashboard

- [x] 4.1 Add the verified local policy summary to plain and fancy selected-agent state. Cover local detached policy, unavailable or stale evidence, and delegated or remote state in CLI tests. Verify JSON and collected results retain their current shape with no extra owner-policy lookup. Describe the view in the manager CLI reference.
- [x] 4.2 Render the current public mode and eligible direct-entry or sign-in copy on the dashboard, using a single observation for the page. Extend `test_gateway_web_entry.py` for open, keyed, unavailable, non-Web, and proxy views. Verify public disclosure limits and the existing live recheck on click. Update the dashboard documentation in the gateway access operations reference.

## 5. Cross-Surface Verification

- [x] 5.1 Run the focused CLI, gateway client, dashboard, and file edit suites through Pixi. Verify the issue #97 sequence against the existing file-edit workflow. Open admission still permits a supported push after direct revocation, the keyed peer retains its candidate after denial, and only explicit managed-self scheduling records a queued publication. Confirm the CLI guidance matches each result.

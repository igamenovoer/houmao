# Design

## Context

See [Proposal](proposal.md) for the launch failure reported in issue #90. The packaged registry already uses minimums for DSH, Claude, and the headless and TUI paths for Kimi and Codex. Kimi Web, Kimi ACP, and Codex app-server each have an equality selector in the registry, an executable check during preflight, and a second check in native startup. Preflight runs independently of unattended policy on those native paths.

## Goals / Non-Goals

**Goals**

- Carry one version minimum per native mode through registry selection, manager preflight, provider startup, and explicit relaunch.
- Record the executable version that was verified at startup and distinguish version validation from native compatibility diagnostics.

**Non-Goals**

- Exact package selections in reproducible fixtures and recorded qualification runs identify evidence for a specific build. Usage, refresh, and observation features use their own capability and evidence contracts.

## Decisions

### Use an Inclusive Minimum per Backend

| Tool | Mode or backend | Minimum |
| --- | --- | --- |
| DSH | Managed headless and ACP service | `>=0.2.2rc3` |
| DSH | Web and the raw-launch strategy | `>=0.2.2rc1` |
| Kimi Code | Headless and TUI | `>=2.1.1` |
| Kimi Code | ACP service and Web | `>=2.6.0` |
| Claude Code | Maintained unattended launch and tracked TUI | `>=2.1.296` |
| Codex | Maintained headless and TUI | `>=0.162.1` |
| Codex | App-server service | `>=0.169.0` |

Use the packaged strategy declaration as the source of the applicable minimum for native launch checks. Select the declaration by tool and backend, independently of permission projection and the transient strategy override. Keep strategy identifiers stable so existing references still resolve. The generic specifier parser can continue to represent dependency-style expressions. Enforce the one-minimum convention for packaged strategies with a registry-wide test.

Reuse the launch-policy version parser and release/RC matching. Preserve the version suffix during probing so that release candidates sort correctly and alpha, beta, and development builds retain their existing treatment. Registry-only admission would miss the native checks on `as_is` launches. Keep version probing at the existing provider-start and preflight boundaries, including validation before force takeover. Passive attachment uses the saved owner identity. A fresh native incarnation validates the executable it will start.

### Check the Native Contract Before Readiness

Kimi Web consumes the probed version in launch metadata. Validate that metadata against the Web minimum and retain the checks for the owned process, authenticated loopback listener, native API, configured model and permission, and exact session and workspace. If verification fails, report the failed check with safe context and use the existing cleanup path.

The Kimi ACP and Codex service owners already receive the selected executable and launch metadata. Use the probed version there as the expected identity. Compare the native peer's reported version using normalized version values and publish the actual version in the binding. This ties the handshake to the executable selected for the new incarnation. Verify Kimi's ACP protocol and capabilities and Codex's initialize response and private home. Existing session and thread checks establish that the owner has bound the correct conversation.

A test-build list would require a Houmao release for each tool upgrade. A minimum allows native startup to verify a newer eligible build with the same protocol and ownership checks. Keep the failed version, protocol, capability, or identity check visible in the error. Preserve the per-mode cleanup and actionable Codex headless and TUI alternatives.

## Risks / Trade-offs

- A later build can change its native protocol or defaults. Reject an incompatible startup before publishing readiness. Exercise a prompt and lifecycle operation against actual newer builds to cover behavior that startup alone cannot verify.
- A prerelease suffix can be lost during version extraction. Test representative release and RC output and the existing alpha, beta, and development exclusions.
- A build that launches successfully may lack independently validated usage or refresh support. Record the actual tool version and preserve each feature's own evidence model.

## Migration Plan

Ship the new minimums with preflight and native startup changes in the same release. New launches and explicit relaunches use the version detected for that start. Existing owners continue to use their saved bindings.

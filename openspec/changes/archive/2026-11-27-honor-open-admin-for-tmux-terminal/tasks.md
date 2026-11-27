# Tasks

## 1. Gateway Authorization and Lifetime

- [x] 1.1 Reuse the original terminal interaction decision at ticket issuance, redemption, and stream revalidation. Accept current open and enrolled-admin decisions and preserve keyed SSHSIG login. Test unsigned open issuance, keyed proof, invalid supplied proof, default and self refusal, unavailable policy, and direct-origin enforcement. Update the gateway protocol reference.
- [x] 1.2 Test roster transitions in gateway entry and stream coverage. Exercise first enrollment during issuance and before redemption, active open-stream revocation, a fresh empty roster rejecting old epoch tickets, and a removed admin stream staying closed. Confirm anonymous viewing continues while the live tmux binding is valid.

## 2. Dashboard and Browser Entry

- [x] 2.1 Show the interactive link on verified open and keyed gateways with mode-appropriate guidance. Test open, keyed, and unavailable policy, alongside independent native Web entry. Update the browser terminal operator guide.
- [x] 2.2 Request the existing interactive ticket from the bare browser page and offer keyed sign-in when proof is required. Test live policy changes after dashboard render, same-origin receipt validation, fragment links, and unavailable-policy feedback.

## 3. Gateway Client and CLI

- [x] 3.1 Allow a direct unsigned interactive ticket request in `GatewayClient` while preserving route-specific validation. Verify empty request bodies, the interact fragment receipt, signed caller support, and rejection of proxy or relay paths.
- [x] 3.2 Have `gateway terminal-entry --interact` use existing verified open authority or the current enrolled signer. Test open without a key, keyed with and without a key, explicit invalid proof, policy or listener replacement, and absence of automatic auth or mode fallback. Update command help and the CLI reference.

## 4. Integration Verification

- [x] 4.1 Extend the isolated Chromium and tmux gateway test to open the terminal through the dashboard on an empty roster and use terminal input. Enroll an admin, confirm the previous open stream closes, and exercise keyed sign-in and the anonymous viewer. Run the focused gateway and CLI suites, lint, typecheck, and strict OpenSpec validation.

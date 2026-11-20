# Tasks

## 1. Share the Empty-Roster Admission Rule

- [x] 1.1 Extend the shared access policy to issue the existing revision-bound anonymous grant for unsigned private and admin calls with a valid empty roster. Cover the empty-to-keyed-to-empty transition, invalid supplied proof, valid keyed self and admin proof, first-key possession, and unavailable state in the gateway policy and HTTP tests.
- [x] 1.2 Apply the live policy to owner-file mail forms and both plugin route classes. Verify that keyed self callers cannot trigger owner-file effects, open calls preserve anonymous provenance and configured service identity, and plugin admission precedes lifecycle handling. Update the mailbox, plugin, and access references to explain the immediate reach of an empty roster on upgrade.

## 2. Apply the Policy Across Agent Access Paths

- [x] 2.1 Use current selected-agent policy for passive proxy and direct operations. Test unsigned private forwarding, enrollment before downstream admission, anonymous direct operation revalidation, unavailable retained policy, and continued scope checks for signed relays and internal backing. Update the passive server reference for the roster transitions.
- [x] 2.2 Project effective private proof in the live gateway descriptor and update the registry schema. Test open, keyed, and unavailable values, including an older record that omits the field. Document current policy as authoritative and discovery as locator metadata.

## 3. Open the Web Agent

- [x] 3.1 Make the bare owner-local Web entry URL return an immediate native redirect for a valid empty roster. Test direct DSH and Kimi handoff, keyed login page, refusal on unavailable policy, and enrollment or binding replacement during native lookup. Verify the no-store and referrer protections and document when the browser skips interactive sign-in.
- [x] 3.2 Accept unsigned owner-local ticket issuance for the current empty revision. Test the 60-second result, single-use redemption, expiry, refusal after any roster change, and rejection of invalid proof, self, relay, backing, or unsupported ingress. Verify the existing keyed issue and claim paths and document both issuance modes.
- [x] 3.3 Update the gateway client and scoped CLI to choose unsigned issuance from a fresh verified open descriptor and use the configured signer for keyed issuance. Test unchanged URL and expiry output, owner and generation mismatch, no signer needed in open mode, and no retry after refusal. Update CLI help, the operator manual, and the Web entry reference.
- [x] 3.4 Fix the interactive signing-command generator for Issue #89. Test an absolute path with surrounding whitespace and a whitespace-only field. Keep the literal quoting regression with interior spaces and shell metacharacters. Verify that the login field help and Web entry reference describe trimming and SSH-agent selection.

## 4. Verify the Integrated Access Paths

- [x] 4.1 Exercise open and keyed admission with the verified gateway HTTPS proxy and selected-agent passive fixtures. Verify that a fresh browser reaches the owned native interface in open mode and that a new key closes later anonymous calls. Use isolated tmux and fixture credentials for runtime checks.
- [x] 4.2 Run the focused policy, proxy, Web, CLI, plugin, and mailbox suites. Run `pixi run test`, `pixi run lint`, `pixi run typecheck`, `pixi run docs-build`, and OpenSpec validation for the change. Record verification results and any inherited validation warning.

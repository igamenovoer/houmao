## 1. Runtime mailbox skill references

- [x] 1.1 Update mailbox runtime skill-reference helpers so the visible mailbox subtree is the primary runtime mailbox skill surface while `.system/mailbox/...` remains a compatibility mirror.
- [x] 1.2 Update runtime `mail` prompt construction to name the transport mailbox skill and point at the primary visible mailbox skill path instead of a hidden-only mailbox reference.

## 2. Verification

- [x] 2.1 Refresh focused mailbox and brain-builder tests to assert the visible mailbox skill surface, compatibility-mirror behavior, and updated runtime `mail` prompt wording.
- [x] 2.2 Run the focused mailbox runtime test suite covering mailbox skill projection and runtime `mail` prompt construction.

## 3. Mailbox reference docs

- [x] 3.1 Update mailbox quickstart, runtime-contract, and runtime-integration docs to describe the visible mailbox skill surface as the primary contract and `.system` as compatibility-only.
- [x] 3.2 Verify the updated docs and tests align with the modified `agent-mailbox-system-skills`, `brain-launch-runtime`, and `mailbox-reference-docs` specs.

## 1. Create the mailbox reference subtree

- [x] 1.1 Replace the standalone mailbox reference page with `docs/reference/mailbox/index.md` and create the `contracts`, `operations`, and `internals` subdirectories.
- [x] 1.2 Add a short mailbox index page that explains the documentation structure, introduces key mailbox terms, and links readers to quickstart, contracts, operations, and internals pages.
- [x] 1.3 Add a mailbox quickstart page for mailbox enablement plus `mail check`, `mail send`, and `mail reply` entry workflows, written for first-time readers as well as returning developers.
- [x] 1.4 Establish a consistent mailbox page pattern that includes purpose, mental model, exact technical detail, concrete examples, embedded Mermaid sequence diagrams for important procedures, and source references.

## 2. Document mailbox contracts

- [x] 2.1 Add a contract page for the canonical mailbox message model, addressing, threading, attachments, and immutable-versus-mutable state boundaries, with representative artifact shapes or examples.
- [x] 2.2 Add a contract page for runtime mailbox bindings, runtime-owned mailbox skill integration, and the runtime `mail` command request and result contract, with examples that make the binding and request flow easy to follow.
- [x] 2.3 Add a contract page for managed mailbox helper scripts, including stable flags, payload validation expectations, dependency manifest expectations, and JSON stdout behavior, with concrete payload and result examples.
- [x] 2.4 Add a contract page for filesystem mailbox layout, durable artifacts, mailbox-local rules, and v1 placeholder directories, with an annotated filesystem tree or similar explanatory structure.

## 3. Document mailbox operations and internals

- [x] 3.1 Add an operations page for mailbox bootstrap, read/send/reply workflows, and when to inspect mailbox-local `rules/` content, using stepwise examples and embedded Mermaid sequence diagrams for the important flows.
- [x] 3.2 Add an operations page for address-routed registration lifecycle behavior, including `safe`, `force`, `stash`, `deactivate`, and `purge`, with embedded Mermaid sequence diagrams for the key lifecycle procedures.
- [x] 3.3 Add an operations or internals page for repair and recovery expectations, including canonical-message recovery boundaries and staging cleanup, with an embedded Mermaid sequence diagram where the sequence materially helps understanding.
- [x] 3.4 Add internals pages that explain runtime integration, projected mailbox skill and binding refresh behavior, SQLite state responsibilities, and address-scoped locking behavior with plain-language framing plus exact technical specifics, including Mermaid sequence diagrams for important multi-component flows.

## 4. Align navigation and cross-references

- [x] 4.1 Update `docs/index.md`, `docs/reference/index.md`, and mailbox-related links so they point to the new mailbox subtree entrypoint.
- [x] 4.2 Trim mailbox detail from `docs/reference/brain_launch_runtime.md` so it remains an entrypoint and links to the dedicated mailbox reference pages instead of duplicating them.
- [x] 4.3 Ensure each detailed mailbox reference page identifies the implementation files or projected mailbox asset files it reflects.
- [x] 4.4 Do a final clarity pass across the mailbox subtree to ensure terminology is introduced clearly, examples are present where needed, Mermaid sequence diagrams accompany important procedures, and the docs remain approachable for both new users and developers.

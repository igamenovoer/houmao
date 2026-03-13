## Why

The mailbox system has grown into a multi-surface feature with runtime bindings, filesystem transport rules, managed helper scripts, lifecycle modes, and internal recovery behavior, but the main reference documentation is still concentrated in one page. That makes it hard for operators, implementers, and future maintainers to find the right level of detail without either missing critical constraints or rereading the same mixed overview repeatedly.

We need a mailbox documentation reorganization now because the mailbox feature set is mature enough that its contracts and operating rules deserve a stable reference home under `docs/reference/mailbox/`, with a clearer split between quickstart guidance, stable contracts, operating procedures, and internals. We also need the docs to teach as well as specify: new users should be able to build an intuitive mental model quickly, while developers should still be able to find the exact technical details and source-aligned contracts they need.

## What Changes

- Reorganize mailbox reference documentation into a dedicated `docs/reference/mailbox/` section with an index page and subpages for quickstart, stable contracts, common operations, and internal workings.
- Establish a documentation writing pattern for the mailbox reference pages that starts with intuitive framing and mental models, then drills into exact technical specifics, constraints, and source-backed details.
- Define the minimum documentation coverage for mailbox contracts, including the canonical message model, runtime mailbox bindings, runtime `mail` command contract, managed helper script contract, and filesystem mailbox layout.
- Define the minimum operational guidance coverage for mailbox bootstrap, read/send/reply workflows, address-routed registration lifecycle modes, and repair or recovery expectations.
- Define the minimum internal reference coverage for runtime-owned mailbox integration, projected skill guidance, SQLite state responsibilities, and address-scoped locking behavior.
- Require concrete examples, clearly introduced terminology, and audience-aware explanations so the same docs work for both new users and mailbox implementers.
- Require important mailbox procedures introduced in the docs to include inline Mermaid sequence diagrams embedded directly in the Markdown pages so readers can see the flow as well as read it.
- Keep mailbox docs aligned with the actual code and projected mailbox assets by explicitly identifying the source implementation and asset files that the reference pages must reflect.
- Replace the single-page mailbox reference summary with a shorter navigational index that points readers to the correct detailed subpages.

## Capabilities

### New Capabilities
- `mailbox-reference-docs`: Structured reference documentation for the mailbox system, including information architecture, required contract coverage, operator guidance, and internal implementation reference pages under `docs/reference/mailbox/`.

### Modified Capabilities

## Impact

This change is expected to affect `docs/reference/`, docs navigation pages, and the documentation workflow for mailbox-related changes. It should not change mailbox runtime behavior, filesystem transport behavior, SQLite schema, or managed helper invocation contracts, but it will create a clearer documentation contract that future mailbox work can update incrementally instead of expanding one oversized page. It will also define a higher-quality documentation standard for mailbox topics so repo docs become more approachable for first-time readers without giving up the exactness needed by developers and maintainers.

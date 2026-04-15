## ADDED Requirements

### Requirement: Explicit launch-profile memo seed application is component-scoped
`houmao-mgr agents launch --launch-profile <name>` SHALL apply the selected explicit launch profile's memo seed using component-scoped policy semantics from managed launch runtime.

Direct launch-time overrides for other launch fields, such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir`, SHALL remain one-shot overrides and SHALL NOT rewrite the stored memo seed or its component scope.

#### Scenario: Explicit memo-only launch preserves pages
- **WHEN** explicit launch profile `reviewer-default` stores memo-only seed text with policy `replace`
- **AND WHEN** managed agent `reviewer-default` already has pages
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile reviewer-default`
- **THEN** Houmao replaces only the launched agent's `houmao-memo.md`
- **AND THEN** it leaves the launched agent's pages unchanged
- **AND THEN** the launch completion payload reports the memo seed application result

# Require Two Real Coding Agents Before Closing Each CCCC Issue

Deterministic stand-in bodies and actual-provider tests cannot establish that real coding agents complete the intended gateway communication workflow. Issue #77 therefore requires a successful small chat receive/reply smoke with two real managed coding agents, and issue #78 separately requires a two-real-agent deferred Mail send/read/reply smoke. This accepted decision adds a model-access prerequisite to closure while retaining deterministic stand-in tests for crash and race coverage.

## Consequences

Use the existing supported local fixture launcher and private selected credentials, with distinct gateway/Actor bindings against compatible actual CCCC. The agents may use the same supported client/profile; this gate does not require a full client/model matrix. Missing credentials or unsuccessful execution keep the corresponding issue's acceptance pending, and sanitized evidence must distinguish the required real-agent smoke from stand-in and provider tests.

See the [chat qualification design](../../design.md#8-qualify-installed-packages-and-the-real-provider-boundary) and [deferred Mail qualification design](../../../cccc-02-add-explicit-deferred-mail/design.md#8-qualify-the-provider-journal-and-cross-system-boundaries).

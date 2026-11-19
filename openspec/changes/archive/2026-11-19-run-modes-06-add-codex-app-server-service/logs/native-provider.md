# Codex App-Server Provider

The private wire probe used installed Codex CLI `0.169.0`. Its `initialize` response uses the unversioned `{id, result}` envelope and identifies the selected `codexHome` and caller-qualified build. Houmao completes `initialized` and verifies the bound thread before publishing readiness. The native probe returned an idle, durable thread and a planned rollout path. Codex created the rollout on the first prompt.

Houmao reads native thread state before each prompt because `turn/start` can add input to existing work. The write uses the shared prewrite check and sends the managed request ID as `clientUserMessageId`. The correlated response establishes a native turn handle. Only a matching `turn/completed` notification with a terminal status settles that turn. The provider retains matching early notifications within a fixed limit and deduplicates completed item identities. Partial assistant output keeps its native provenance when the turn fails or the connection closes. Private rollout accounting starts at the last complete native row before dispatch and excludes thread-wide usage notifications.

The provider declines unresolved native approvals and dismisses supported requests for human input. It answers undeclared reverse methods with a bounded error. A targeted interrupt requires the current thread and turn IDs and waits for the matching interrupted outcome. A lost or unverified outcome leaves durable uncertainty and no replay. Cold continuation verifies the persisted rollout and recorded workspace before calling `thread/resume` without overrides for the workspace or history.

## Controlled Verification

**88 passed** across Codex provider, Kimi and DSH ACP transport, DSH provider and driver, and DSH usage tests. The subprocess peer covered early and late correlation, foreign and duplicate notifications, a notification-buffer overflow, tool lifecycle without exposing arguments, typed reverse interactions, exact interrupt acknowledgment before settlement, input permission revocation, busy-native refusal, failed and partial turns, disconnect before and after a native handle, foreign rollout rejection, and fresh incarnation resume. Ruff, scoped strict mypy, and `git diff --check` passed.

The live self-hosted Qwen Responses run confirmed manager and signed gateway control, pinned process and thread identity across prompts, exact interruption, usage, AG-UI, and continuation on an owned replacement process. [Implementation verification](implementation.md)

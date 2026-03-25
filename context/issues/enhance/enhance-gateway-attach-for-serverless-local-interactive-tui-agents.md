# Enhancement: Support Gateway Attach For Serverless `local_interactive` TUI Agents

## Priority
P2 - This is not a core runtime correctness failure, but it blocks an expected control-plane capability for no-server TUI agents and creates a mismatch between the broader gateway design and the current local interactive implementation.

## Status
Open as of 2026-03-25.

## Summary

`houmao-mgr agents gateway attach <agent-ref>` currently rejects a live no-server TUI agent launched through backend `local_interactive`, even though the surrounding runtime, gateway schema, and attachability model already treat that backend as a tmux-backed gateway-capable session shape.

Observed failure:

```text
Gateway attach is only implemented for runtime-owned tmux-backed backends {'cao_rest', 'houmao_server_rest', 'claude_headless', 'codex_headless', 'gemini_headless'} in v1, got backend='local_interactive'.
```

This does not appear to be a fundamental design restriction. It appears to be an implementation gap and boundary mismatch in the current v1 gateway attach path.

## Reproduction

### 1. Launch a no-server TUI agent

```bash
AGENTSYS_AGENT_DEF_DIR=/data1/huangzhe/code/houmao/tests/fixtures/agents \
pixi run houmao-mgr agents launch \
  --agents gpu-kernel-coder \
  --provider claude_code \
  --session-name verify-gateway-1 \
  --yolo
```

### 2. Attempt gateway attach

```bash
pixi run houmao-mgr agents gateway attach 108187a69069c63bb6df84b9eea21a90
```

Observed result:

```text
Gateway attach is only implemented for runtime-owned tmux-backed backends {'cao_rest', 'houmao_server_rest', 'claude_headless', 'codex_headless', 'gemini_headless'} in v1, got backend='local_interactive'.
```

### 3. Confirm runtime sees the session but gateway is unattached

```bash
pixi run houmao-mgr agents gateway status 108187a69069c63bb6df84b9eea21a90
```

Observed fields included:

- `backend: "local_interactive"`
- `gateway_health: "not_attached"`
- `request_admission: "blocked_unavailable"`

## Why This Looks Like A Feature Gap Rather Than A Fundamental Limitation

### 1. Runtime already treats `local_interactive` as tmux-backed

`local_interactive` is part of `_TMUX_BACKED_BACKENDS` in:

- `src/houmao/agents/realm_controller/runtime.py`

That means the runtime already considers it eligible for tmux-oriented lifecycle behaviors such as stable session identity and gateway capability publication.

### 2. Runtime already publishes gateway capability for tmux-backed local interactive sessions

`RuntimeSessionController.ensure_gateway_capability()` publishes attach metadata for tmux-backed sessions without excluding `local_interactive`:

- `src/houmao/agents/realm_controller/runtime.py`

This is strong evidence that the intended session model already includes later gateway attachability for this backend family.

### 3. The stable attach contract explicitly accepts `local_interactive`

`GatewayAttachContractV1` validates `local_interactive` as a gateway-capable backend using the local/headless attach metadata schema:

- `src/houmao/agents/realm_controller/gateway_models.py`

So the persisted gateway contract does not treat `local_interactive` as forbidden.

### 4. Gateway capability storage builds attach contracts for `local_interactive`

`build_attach_contract()` emits the runtime-owned local/headless attach metadata shape for non-REST tmux-backed sessions, including `local_interactive`:

- `src/houmao/agents/realm_controller/gateway_storage.py`

So attachability is not only theoretical; it is actively persisted.

### 5. Gateway service already includes `local_interactive` in its local adapter selection

`_build_gateway_execution_adapter()` routes `local_interactive` through `_LocalHeadlessGatewayAdapter`:

- `src/houmao/agents/realm_controller/gateway_service.py`

This suggests the gateway layer was already being shaped to support local interactive sessions, even if the current adapter naming still reflects headless-first origins.

### 6. TUI runtime surface already exposes the needed control methods

`LocalInteractiveSession` already supports:

- `send_prompt(...)`
- `interrupt()`

in:

- `src/houmao/agents/realm_controller/backends/local_interactive.py`

Those are the core gateway-mediated actions currently exposed by `houmao-mgr agents gateway prompt` and `houmao-mgr agents gateway interrupt`.

## Where The Current Mismatch Lives

The immediate blocker is the hardcoded backend allowlist in:

- `src/houmao/agents/realm_controller/runtime.py`

`_attach_gateway_for_controller()` rejects `local_interactive` before gateway startup proceeds, even though the broader runtime and gateway model already classify it as a tmux-backed attachable local session.

There is also a secondary design smell:

- the gateway service uses `_LocalHeadlessGatewayAdapter` for `local_interactive`
- that adapter's `submit_prompt()` currently expects a `HeadlessInteractiveSession`

Because `LocalInteractiveSession` subclasses `HeadlessInteractiveSession`, this may be more of a naming/abstraction leak than a hard blocker. But the current implementation shape suggests local interactive gateway support was only partially carried through.

## Spec / Contract Reading

The strongest relevant runtime requirement is in:

- `openspec/specs/brain-launch-runtime/spec.md`

That spec says:

- runtime-owned tmux-backed sessions may be made gateway-capable independently of a running gateway
- attach metadata is published for runtime-owned tmux-backed sessions
- live gateway attach should work for every runtime-owned tmux-backed backend whose gateway execution adapter is implemented
- unsupported backends should fail explicitly rather than silently falling back

This spec does not state that serverless TUI sessions are categorically ineligible for gateway attach.

Separately, the TUI tracking spec discusses managed TUI agents gaining an eligible attached live gateway in:

- `openspec/specs/official-tui-state-tracking/spec.md`

That also aligns better with eventual gateway support for local interactive TUI sessions than with any permanent prohibition.

## Assessment

This should be treated as a feature request / implementation completion item, not as a request to violate a core architectural boundary.

Short version:

1. There is no clear fundamental design issue forbidding gateway use with serverless TUI agents.
2. The current runtime and schema layers already lean toward supporting it.
3. The attach path is narrower than the surrounding design and is the main blocking point.

## Desired Direction

### 1. Allow gateway attach for `local_interactive`

Extend `_attach_gateway_for_controller()` so `local_interactive` is admitted when the required adapter and runtime invariants are satisfied.

### 2. Make the local gateway adapter explicitly correct for interactive TUI sessions

Either:

- generalize the existing local adapter naming and semantics so it clearly supports both headless and local interactive runtime-owned tmux sessions, or
- split local headless and local interactive gateway adapters if that yields cleaner invariants

### 3. Verify explicit gateway-mediated prompt and interrupt on no-server TUI sessions

Regression coverage should verify that, for a runtime-owned local interactive session:

- `agents gateway attach` succeeds
- `agents gateway status` reports a live attached gateway
- `agents gateway prompt` reaches the live TUI through gateway queueing
- `agents gateway interrupt` interrupts active work through the gateway path

### 4. Clarify operator-facing docs

If support remains intentionally incomplete for a while, the docs and help text should say so clearly. If support is completed, docs should describe serverless TUI gateway as a supported local-control path.

## Acceptance Criteria

- A live no-server `local_interactive` TUI agent can attach a gateway through `houmao-mgr agents gateway attach <agent-ref>`.
- Gateway status for that session reports an attached live gateway instead of a permanent unsupported-backend posture.
- Gateway-mediated prompt and interrupt work against the attached local interactive session.
- The implementation does not silently route those requests through legacy direct control when the caller explicitly chose the gateway path.
- Automated coverage exists for the supported no-server TUI gateway flow.

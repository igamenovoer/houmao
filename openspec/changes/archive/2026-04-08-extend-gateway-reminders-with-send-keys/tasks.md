## 1. Reminder Delivery Model

- [x] 1.1 Extend the gateway reminder request and response models in `src/houmao/agents/realm_controller/gateway_models.py` so each reminder uses exactly one delivery form: semantic `prompt` or raw `send_keys`, and add `send_keys.ensure_enter` with default `true`.
- [x] 1.2 Update the gateway reminder client and HTTP contract plumbing in `src/houmao/agents/realm_controller/gateway_client.py` and `src/houmao/agents/realm_controller/gateway_service.py` to validate the new reminder delivery shape and expose inspection fields such as `delivery_kind`.

## 2. Gateway Runtime Execution

- [x] 2.1 Extend the gateway execution-adapter boundary in `src/houmao/agents/realm_controller/gateway_service.py` so reminder create/update can detect whether the attached target supports raw control input and reject unsupported `send_keys` reminders with explicit HTTP `422` errors.
- [x] 2.2 Rework reminder execution in `src/houmao/agents/realm_controller/gateway_service.py` so due effective reminders dispatch either semantic prompts or raw send-keys control input while keeping the existing ranking, pause, and readiness-gating behavior unchanged.
- [x] 2.3 Implement `ensure_enter` normalization for send-keys reminders so `ensure_enter=true` guarantees one trailing Enter and `ensure_enter=false` preserves the caller-supplied control-input sequence exactly.

## 3. Skill And Reference Updates

- [x] 3.1 Update the packaged `houmao-agent-gateway` skill assets under `src/houmao/agents/assets/system_skills/houmao-agent-gateway/` to describe prompt reminders versus send-keys reminders, `ensure_enter`, and backend rejection behavior accurately.
- [x] 3.2 Update gateway reminder reference docs under `docs/reference/gateway/` so the operator-facing reminder page explains `send_keys`, exact-key semantics, `ensure_enter`, and the direct live HTTP boundary without inventing a new CLI family.

## 4. Verification

- [x] 4.1 Update gateway unit and integration tests to cover prompt/send-keys exclusivity, default `ensure_enter`, explicit `ensure_enter=false`, unsupported-backend rejection, and raw send-keys reminder execution behavior.
- [x] 4.2 Run the focused reminder, gateway, and skill/doc test suites affected by the change and record the verification results for the change.

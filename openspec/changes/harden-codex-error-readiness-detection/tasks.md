## 1. Codex Signal Classification

- [ ] 1.1 Add profile-private Codex helpers that classify bounded prompt-adjacent terminal failures, bounded prompt-adjacent degraded compact/server failures, and bounded live-edge retry/reconnect surfaces from structural scope plus essential semantic tokens.
- [ ] 1.2 Add detector-level fixtures for red failure blocks, warning-style failed turns, degraded compact/server failures, retry/reconnect status surfaces, and historical warning/error noise outside the bounded current-turn scope.

## 2. Tracker Semantics

- [ ] 2.1 Update the Codex tracked-TUI detector so readiness remains prompt-derived while `current_error_present`, `known_failure`, `chat_context`, `success_candidate`, and `active_evidence` come from the new bounded classifier.
- [ ] 2.2 Update shared tracker/session regression coverage so prompt-ready terminal failures preserve readiness without settling success, degraded compact/server failures remain non-success and non-`known_failure`, and retry/reconnect surfaces remain active.

## 3. Verification and Documentation

- [ ] 3.1 Add or update server-facing regression coverage proving warning-only failures and retry statuses no longer drift into ready-success outcomes under live tracking.
- [ ] 3.2 Update Codex signal and tracked-state reference docs to describe the bounded semantic signal families and their readiness, degraded-context, active, and completion effects without making exact upstream sentences the stable contract.

## 1. Preserve Demo Launch Posture

- [ ] 1.1 Update the mail ping-pong demo brain-build path to pass the tracked recipe `operator_prompt_mode` into `BuildRequest`.
- [ ] 1.2 Verify the built participant brain manifests preserve `launch_policy.operator_prompt_mode` instead of silently defaulting to `interactive`.

## 2. Guard Live Launch Behavior

- [ ] 2.1 Extend demo startup coverage to assert live managed-headless launch metadata or provenance reflects unattended posture when the tracked recipe requests it.
- [ ] 2.2 Confirm the demo startup path still behaves correctly for recipes that omit `operator_prompt_mode`.

## 3. Demo Contract Follow-Through

- [ ] 3.1 Update any demo-facing documentation or artifact expectations that surface launch posture so they match the preserved unattended contract.
- [ ] 3.2 Run the focused demo-pack test suite and any related launch-policy assertions needed to verify the change end to end.

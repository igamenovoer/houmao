## 1. Launch Surface Cleanup

- [x] 1.1 Remove the Houmao CLI `--yolo` option from `houmao-mgr agents launch` and `houmao-mgr project easy instance launch`.
- [x] 1.2 Delete the shared Houmao-managed workspace trust confirmation path and simplify the local launch helper signature and callers accordingly.
- [x] 1.3 Preserve the current `launch.prompt_mode` contract so `unattended` continues to use maintained provider launch policy while `as_is` continues to bypass unattended-owned startup mutations.

## 2. Docs And Workflow Revisions

- [x] 2.1 Update launch-related docs and skill guidance to stop referencing `houmao-mgr ... --yolo` and to describe prompt-mode ownership instead.
- [x] 2.2 Update demos, manual smoke flows, and fixture readmes that currently build Houmao launch commands with `--yolo`.

## 3. Validation

- [x] 3.1 Update unit and integration tests that currently pass `--yolo` only to bypass Houmao's trust prompt.
- [x] 3.2 Add or adjust launch-surface regression coverage so managed launch succeeds without a separate Houmao trust-bypass flag and stored `as_is` posture remains non-injecting.
- [x] 3.3 Run the relevant launch CLI test suites and confirm the revised contract is reflected in OpenSpec artifacts and first-party operator guidance.

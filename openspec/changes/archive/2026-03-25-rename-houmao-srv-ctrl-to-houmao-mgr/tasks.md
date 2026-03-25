## 1. Public CLI Identity

- [x] 1.1 Rename the installed pair-management script from `houmao-srv-ctrl` to `houmao-mgr` in packaging and Click program-name wiring while keeping the internal `houmao.srv_ctrl` package path intact.
- [x] 1.2 Update user-facing CLI help text, prompts, and migration/error guidance in `src/houmao/srv_ctrl/**` and related runtime/launcher entrypoints to refer to `houmao-mgr`.
- [x] 1.3 Update any code paths that check for or invoke the public pair CLI so repo-owned automation expects `houmao-mgr` instead of `houmao-srv-ctrl`.

## 2. Docs And Demo Surface

- [x] 2.1 Update `README.md`, `GEMINI.md`, `docs/reference/**`, and `docs/migration/**` to describe the supported pair as `houmao-server + houmao-mgr` and to use `houmao-mgr ...` command examples.
- [x] 2.2 Update demo docs and demo implementation under `scripts/demo/**` and `src/houmao/demo/**` so the required public CLI and example commands use `houmao-mgr`.
- [x] 2.3 Align remaining live repo-owned gateway wording with the renamed CLI so pair-owned attach guidance consistently uses `houmao-mgr agents gateway attach`.

## 3. Verification

- [x] 3.1 Update unit tests and any demo/preflight checks to assert `houmao-mgr` as the supported public binary name and help surface.
- [x] 3.2 Run a live-reference sweep and verify that remaining `houmao-srv-ctrl` mentions are limited to intentional internal module paths or archived change history.

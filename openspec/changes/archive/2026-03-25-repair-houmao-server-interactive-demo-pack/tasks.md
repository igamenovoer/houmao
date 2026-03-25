## 1. Startup Surface And Run-Owned Artifact Ownership

- [x] 1.1 Replace the demo's private detached launch helper usage with a subprocess that invokes `houmao-mgr cao launch --headless --yolo` from the demo workdir.
- [x] 1.2 Pass the demo-owned runtime, registry, jobs, and home environment to both install and detached launch subprocesses so delegated manifests and related artifacts stay under the run root.
- [x] 1.3 Update startup-side polling, manifest discovery, and error messages to describe the detached compatibility launch path rather than the old private-helper wording.

## 2. Stop Flow And Operator Documentation

- [x] 2.1 Change the normal demo stop path to `POST /houmao/agents/{agent_ref}/stop` via `HoumaoServerClient.stop_managed_agent`, while preserving stale-session tolerance and separate partial-start cleanup behavior.
- [x] 2.2 Refresh `scripts/demo/houmao-server-interactive-full-pipeline-demo/README.md` and shell-wrapper help text so startup and stop describe the current `houmao-server + houmao-mgr` boundary accurately.

## 3. Regression Coverage

- [x] 3.1 Update `tests/unit/demo/test_houmao_server_interactive_full_pipeline_demo.py` to assert detached startup uses the public `houmao-mgr cao launch --headless` command shape with the demo-owned environment.
- [x] 3.2 Update demo stop tests to assert managed-agent stop routing and stale-session inactive-state handling under the revised control surface.

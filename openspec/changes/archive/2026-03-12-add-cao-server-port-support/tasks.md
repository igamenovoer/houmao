## 1. Launcher Port-Aware Lifecycle Support

- [x] 1.1 Update CAO launcher base-url validation so supported targets are `http://localhost:<port>` and `http://127.0.0.1:<port>` with explicit ports instead of an exact `:9889` allowlist.
- [x] 1.2 Ensure launcher CLI overrides remain available for supported config values and that non-default `--base-url` overrides participate in the same validation and resolution path as file-backed values.
- [x] 1.3 Change launcher startup to derive the requested port from the effective `base_url`, pass that port through CAO's supported launch mechanism, and fail explicitly if the requested base URL never becomes healthy after spawn.
- [x] 1.4 Refresh launcher-facing config examples, CLI help, structured messages, and install/troubleshooting text to describe configurable loopback port support while keeping artifact ownership keyed by `<host>-<port>`.

## 2. Shared Loopback Transport Policy

- [x] 2.1 Generalize shared CAO loopback no-proxy helpers from two exact URLs to supported loopback hosts with explicit ports.
- [x] 2.2 Update launcher health probes, the CAO REST client, and runtime-managed tmux env injection to use the broadened loopback-with-port contract consistently.
- [x] 2.3 Preserve the interactive demo's fixed `http://127.0.0.1:9889` contract and ensure this change does not accidentally broaden the demo workflow surface.

## 3. Demo And Script Impact Points

- [x] 3.1 Update repo-owned non-interactive CAO demo scripts that currently exact-match `http://localhost:9889` or `http://127.0.0.1:9889` so they accept supported loopback CAO ports while still skipping remote URLs.
- [x] 3.2 Keep the CAO launcher tutorial/demo pack pinned to `http://127.0.0.1:9889` and update any surrounding guidance in this change so the tutorial is clearly documented as an intentional fixed-port exception.
- [x] 3.3 Update exploratory helper scripts and surrounding references that still document `http://localhost:9889` as the only normal CAO loopback path.

## 4. Verification And Documentation

- [x] 4.1 Extend unit coverage for launcher validation, config-override handling, no-proxy helpers, and runtime CAO transport behavior with non-default loopback port cases.
- [x] 4.2 Update integration coverage to prove launcher-managed start/status/stop works on a non-default loopback port and does not report success against the wrong port.
- [x] 4.3 Update active docs and the fixed-port issue note so repo guidance matches the tracked CAO fork's configurable-port behavior, while clearly calling out the interactive demo and launcher tutorial's unchanged fixed-port paths.

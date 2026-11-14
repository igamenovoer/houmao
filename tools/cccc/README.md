# Native CCCC Development Service

This utility builds the reference CCCC checkout and runs its daemon and Web UI inside the existing Linux environment. It uses a separate Pixi workspace; Docker and nested container privileges are unnecessary. These files are development/operational tooling and are not part of the released Houmao package.

## Install and Build

From the Houmao project root:

```bash
git clone https://github.com/ChesterRa/cccc.git extern/orphan/cccc
pixi install --manifest-path tools/cccc/pixi.toml
pixi run --manifest-path tools/cccc/pixi.toml build
```

Skip cloning when the checkout already exists. The Pixi lockfile records the toolchain for Linux ARM64 and x86-64. Rust 1.88 matches the upstream toolchain; Node.js 24 builds the embedded Web UI. Cargo uses the upstream `Cargo.lock`. The first build downloads Rust crates, frontend packages, and the upstream checksum-verified Sherpa/ONNX native archive. Build output and caches live outside the checkout.

The default Cargo development profile follows upstream's disabled debug information and retains incremental builds. This is a local development build, not an upstream release artifact or a benchmark qualification. The helper builds the selected source checkout without modifying tracked upstream files.

## Start and Inspect

```bash
pixi run --manifest-path tools/cccc/pixi.toml start
pixi run --manifest-path tools/cccc/pixi.toml status
pixi run --manifest-path tools/cccc/pixi.toml cccc --version
pixi run --manifest-path tools/cccc/pixi.toml cccc doctor
pixi run --manifest-path tools/cccc/pixi.toml cccc groups
```

The Web UI listens on <http://127.0.0.1:8848>. The HTTP health route is `/api/v1/health`; daemon IPC uses CCCC's private local Unix-domain socket. Forward the Web port through the outer container, editor, or SSH when accessing it from another machine. The helper deliberately selects loopback; upstream remote Web access setup is a separate deployment choice.

The `cccc` task preserves Pixi's original invocation directory (`INIT_CWD`), so relative CLI arguments such as `attach .` target the caller's project. Build and background service commands use the explicitly selected source checkout.

`start` detaches the service, waits for the daemon-backed health response, and records its PID and source revision. A repeated start reuses the verified owned process. Use `run` instead of `start` for foreground operation. `stop` verifies process birth identity, executable command, and `CCCC_HOME` before signalling a process:

```bash
pixi run --manifest-path tools/cccc/pixi.toml stop
pixi run --manifest-path tools/cccc/pixi.toml run
```

## Files and Configuration

The default persistent root is `~/.local/share/houmao-cccc/`:

| Path Under the Root | Purpose |
| --- | --- |
| `data/` | Selected `CCCC_HOME`, including private daemon IPC, Groups, ledgers, and instance configuration |
| `target/debug/cccc` | Locally built native executable |
| `cache/cargo/` | Cargo registry and dependency downloads |
| `cache/npm/` | Frontend package download cache |
| `server.log` | Owner-private service output |
| `runtime.json` | Owner-private helper process descriptor and source revision |

The helper leaves the developer's `HOME` unchanged. It does not load the repository's `.env`, install agent CLIs, configure provider keys, or attach existing agent sessions. Model credentials are unnecessary for starting and checking the coordination service. Configure any later CCCC-managed actors explicitly, using protected sources rather than tracked files or shell arguments containing keys.

This environment covers the native coordination service and Web UI. CCCC's optional projected-browser/Web Model actors additionally need a system Chrome/Chromium installation and display/VNC tools; those are not installed by this minimal workspace. Existing agent CLIs on the caller's `PATH` may appear in `cccc doctor`, but no agents are launched by this helper.

These environment variables select the development instance:

| Variable | Default |
| --- | --- |
| `HOUMAO_CCCC_SOURCE` | `<project>/extern/orphan/cccc` |
| `HOUMAO_CCCC_ROOT` | `~/.local/share/houmao-cccc` (must be outside the checkout) |
| `HOUMAO_CCCC_PORT` | `8848` |
| `HOUMAO_CCCC_BUILD_JOBS` | `4` |

Use the same root for build and lifecycle commands. Multiple independent instances need different roots and ports. Rebuild after intentionally changing the source checkout, then stop/start the owned service to activate the new executable. Preserve its data directory when restarting.

See [SERVICES.md](../../SERVICES.md) for the instance actually qualified in this workspace. The upstream [Dockerfile](../../extern/orphan/cccc/docker/Dockerfile), [source build helper](../../extern/orphan/cccc/scripts/build_package.sh), and [CLI reference](../../extern/orphan/cccc/docs/reference/cli.md) describe its native build and service behavior.

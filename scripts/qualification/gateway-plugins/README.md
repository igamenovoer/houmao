# Installed Gateway Plugin Qualification

This utility builds Houmao, the independent notification example, and two synthetic fixture distributions. It installs their wheels into a fresh environment using a local wheelhouse, copies its runner outside the checkout, and launches normal gateways through supported runtime APIs. The deterministic installed Codex fixture makes no provider calls and needs no authentication.

Classify the inputs by purpose: the example is standalone sample code, fixture distributions are CI inputs, and this driver is development qualification tooling. None is imported by production Houmao.

## Prepare Local Wheels

Choose output directories outside the checkout. Preparation builds the four project wheels and downloads their binary dependency wheels. This step may access the package index:

```bash
pixi run python scripts/qualification/gateway-plugins/qualify.py prepare \
  --wheelhouse /absolute/private/gateway-plugin-wheels
```

Use a fresh wheelhouse, or remove superseded project wheels before preparing again. The driver requires exactly one version of each qualification artifact. Missing build tooling, wheel artifacts, runtime dependency wheels, or tmux produce explicit setup failures.

## Run Offline

The qualification action invokes pip with `--no-index` and `--find-links`. It does not fetch packages or call model providers:

```bash
pixi run python scripts/qualification/gateway-plugins/qualify.py run \
  --wheelhouse /absolute/private/gateway-plugin-wheels \
  --work-root /absolute/private/gateway-plugin-run
```

The work root must be outside the checkout and must not contain an existing `venv`. Its environment omits `PYTHONPATH`, `PYTHONHOME`, and provider key variables. The installed driver uses Python isolation mode and checks that Houmao, the example, and the fixture modules resolve inside the fresh environment. It rejects checkout source and site-package search paths. Pixi's base interpreter may contribute only its standard-library directory, extension directory, and standard-library archive. A failed isolation assertion cannot be treated as a passing package test.

Both detached-process and same-session auxiliary tmux-window gateways run against an installed deterministic headless executable. Synthetic instances cover selected-only imports, duplicate entry points, missing implementations, unsupported SDK versions, import/startup/worker failures, route conflicts, reserved status routes, owner/account isolation, and safe diagnostics.

The installed notification plugin uses the current managed self key for ordinary routes. Each execution mode enrolls a generated admin key, checks private access under both caller roles, verifies who can use the credential control, and removes the final key to reopen administration. Generated keys and the isolated tmux socket stay under private external fixture roots.

The execution fixture counts actual client invocations. Immediate busy errors leave that count unchanged until a fresh sender request arrives. A transparent tmux wrapper can pause a native launch before handoff. The driver changes the existing body generation while paused, then verifies an error and no late delivery. The wrapper delegates all other commands to the selected real tmux binary.

Each process mode also restarts the gateway while preserving its owner binding and successful source cursor. The sender deliberately discards one completed reply, then retries the same source ID and observes a second dispatch. A separate paused request loses its gateway to `SIGKILL`; releasing the orphaned launch immediately must not invoke the provider. Restarting the gateway must keep that failed payload undelivered until a fresh sender request arrives.

`qualification.json` contains sanitized versions, environment facts, process modes, behavioral results, and cleanup outcome. `operations.log` contains local troubleshooting details and paths; keep it private. The driver stops only the sessions it creates and never stores message bodies in its qualification report.

## Run the Integration Wrapper

After preparation, select the wheelhouse explicitly:

```bash
HOUMAO_GATEWAY_PLUGIN_WHEELHOUSE=/absolute/private/gateway-plugin-wheels \
  pixi run pytest tests/integration/agents/realm_controller/test_gateway_plugin_packages.py -q
```

The test fails with a setup explanation when this prerequisite is absent. It does not silently skip installed-wheel qualification. The test uses a fresh temporary work root and asks the same driver to perform the offline run.

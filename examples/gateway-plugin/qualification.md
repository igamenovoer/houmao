# Installed Wheel Qualification

Qualified on 2026-11-13 using Python 3.13.13 on Linux `aarch64`. The canonical installed-package integration target passed both tests in 87.97 seconds. The example's focused HTTP/resource contract suite passed 11 tests.

## Environment and Artifacts

The driver installed Houmao and three external distributions into a fresh virtual environment with pip `--no-index` and a preprovisioned local wheelhouse. Its copied runner and working directories were outside the checkout. Import assertions confirmed that Houmao, the example, and the fixture package resolved inside the installed environment. Checkout source and site-package search paths were absent; only the managed interpreter's standard-library paths were allowed.

An isolated tmux server used a private temporary socket directory. The installed `houmao-fixture-codex` executable emitted deterministic provider events. Provider network calls: `0`.

| Wheel | Version | SHA256 |
| --- | --- | --- |
| `houmao-2.4.0-py3-none-any.whl` | `2.4.0` | `6ee757ca5dd523e82bb5869e03a3c05420cf7c9ca5ae02ac1b61945f1f7917bb` |
| `houmao_example_notifications-0.1.0-py3-none-any.whl` | `0.1.0` | `31b59d0e4295dc870f597acd2aec10e58810d45a180d638e3d81b5bacd3cbc08` |
| `houmao_gateway_qualification_fixtures-0.1.0-py3-none-any.whl` | `0.1.0` | `df8ec2416d9c3d19ab179e098fbe2908ae4af943b2993397fd2c12c0f140bf8f` |
| `houmao_gateway_duplicate_fixture-0.1.0-py3-none-any.whl` | `0.1.0` | `d1ba63b00df17fbf359d19aec1dc4cd6262b4fe44fd661bd3e4ae2e5848ff6ba` |

The qualified Houmao wheel matched the final distribution wheel byte for byte.

## Results

| Check | Detached Process | Same-Session Auxiliary Window |
| --- | --- | --- |
| Normal runtime launch, dynamic listener binding, healthy external routes, and installed `houmao-mgr` status | Passed | Passed |
| Selected-only entry-point imports, isolated failed instances, and preserved core health | Passed | Passed |
| Fixed owner/account binding and rejected caller authority overrides | Passed | Passed |
| Immediate busy error | HTTP `409` | HTTP `409` |
| Gateway-only restart preserves the binding and successful source cursor | Passed | Passed |
| Discarded success reply followed by a fresh same-ID retry can duplicate dispatch | Passed | Passed |
| Gateway `SIGKILL` during paused handoff fails the sender connection | Passed | Passed |
| Gateway recovery restores configuration without replaying the interrupted event | Passed | Passed |
| A fresh sender retry after gateway recovery succeeds | Passed | Passed |
| Body change during paused handoff fails the original request | Generation replacement, HTTP `503` | Body-window death, HTTP `503` |
| Failed requests cause no extra native client invocation | Passed | Passed |
| Owned sessions and resources stop successfully | Passed | Passed |

Each mode recorded exactly five native client invocations, corresponding to explicit successful sender attempts. The deliberately duplicated source ID accounts for two invocations. Busy, interrupted, and superseded attempts did not increase the count.

Eight adversarial selections covered conflicting routes, a reserved status route, startup failure, worker failure, unsupported SDK version, duplicate entry points, a missing implementation, and an import failure. Their custom routes failed safely while the healthy instance and core health remained available. An unselected implementation's import marker remained absent. Distinct owners using the same configured account received distinct binding IDs.

In detached mode, the released orphaned bridge rejected the dead gateway's request before provider launch. In auxiliary-window mode, gateway death stopped the owned paused launcher before a bridge started. Both cases preserved the invocation count through normal recovery and required a fresh sender request.

The negative prerequisite test returned an explicit setup failure for an empty wheelhouse before creating a virtual environment. No installed-package case was skipped.

## Reproduce

Provision local wheels, then run the canonical integration target with an explicitly selected wheelhouse:

```bash
pixi run python scripts/qualification/gateway-plugins/qualify.py prepare \
  --wheelhouse /absolute/private/gateway-plugin-wheels

HOUMAO_GATEWAY_PLUGIN_WHEELHOUSE=/absolute/private/gateway-plugin-wheels \
  pixi run pytest tests/integration/agents/realm_controller/test_gateway_plugin_packages.py -q

pixi run pytest tests/unit/gateway_plugins/test_example_package.py -q
```

The [qualification utility guide](../../scripts/qualification/gateway-plugins/README.md) explains offline installation, private local diagnostics, and temporary output roots. Its generated `qualification.json` contains sanitized environment facts, versions, artifact hashes, process modes, behavioral results, and cleanup status.

These runs qualify installed package wiring and local headless dispatch using a deterministic execution stub. External-service connectivity and live provider behavior require their own qualification. The evidence contains no credentials, private paths, or notification bodies.

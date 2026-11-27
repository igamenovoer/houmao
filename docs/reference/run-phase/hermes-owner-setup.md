# Prepare a Hermes Execution Owner

Managed Hermes workers use an installation prepared for their execution owner. One installation serves Service, TUI, and Headless workers in that context, including workers from separate projects. Prepare it as the Linux account that runs the workers. Select a dedicated canonical directory outside project runtime directories and personal Hermes data.

## Prepare the Native Runtime

Use stock Hermes v0.23.4, commit `8fc0374447313e276f6b9a2764bfc750190c966a`. The supported source layout places the checkout at `<hermes-root>/hermes-agent` and the prepared tools and dependency generations under the same root. Use the pinned Hermes source installer to provision the Python runtime, the `all` extras, and the Ink build. [Hermes Package Management](https://hermes-agent.nousresearch.com/docs/reference/package-management)

```bash
hermes_root="$HOME/.local/share/houmao/hermes"
hermes_build=8fc0374447313e276f6b9a2764bfc750190c966a
umask 077
install -d -m 0700 "$hermes_root" "$hermes_root/gateway-locks" "$hermes_root/profiles"
hermes_root="$(cd "$hermes_root" && pwd -P)"
git clone https://github.com/NousResearch/hermes-agent.git "$hermes_root/hermes-agent"
git -C "$hermes_root/hermes-agent" checkout --detach "$hermes_build"
HERMES_RUNTIME_DIR="$hermes_root/tools" \
  bash "$hermes_root/hermes-agent/scripts/install.sh" \
    --hermes-home "$hermes_root" --channel main --commit "$hermes_build" \
    --non-interactive --skip-browser --skip-computer-use
chmod go-w "$hermes_root/hermes-agent" "$hermes_root/tools"
```

Houmao enables profile multiplexing when it starts the shared gateway. An owner who starts the gateway separately can enable the same behavior with `gateway.multiplex_profiles: true` in the root's private `config.yaml`. Keep the root's default profile free of provider credentials and messaging adapter settings. Houmao projects the selected credential and launch settings into each named profile and controls that profile's activation.

## Select the Installation

For the current-account manager, set `HOUMAO_HERMES_INSTALLATION_ROOT` to the canonical directory in the environment used to start `houmao-mgr` and `houmao-passive-server`. For a provisioned execution route, set the same variable in the target owner's trusted policy `profile.environment`. The manager selects the stock checkout launcher at `<hermes-root>/hermes-agent/.hermes/bin/hermes`. An explicit `HOUMAO_HERMES_EXECUTABLE` must resolve to that launcher. [Execution Contexts](execution-contexts.md)

Current-account projects share an execution context when they use the same `HOUMAO_GLOBAL_RUNTIME_DIR` and `HOUMAO_GLOBAL_REGISTRY_DIR`. Houmao records the context that claims the prepared installation on its first managed build. Each project retains its own local home link.

The launch check reads the prepared Python generation, build provenance, Ink build, and native capabilities before allocating a worker profile. If this check fails, repair the installation under the same owner and root, using the pinned installer or native `hermes pm install` for Python dependencies. Perform dependency or source maintenance before launching workers. Ordinary launches and turns use the prepared dependencies with native lazy installation disabled.

Each project's runtime home entry points to the worker's canonical profile under `<hermes-root>/profiles`. The working directory is still selected independently. A managed stop keeps the worker's profile and session for relaunch. Explicit managed cleanup removes the eligible profile and its recorded project link. [Managed Hermes](hermes-modes.md)

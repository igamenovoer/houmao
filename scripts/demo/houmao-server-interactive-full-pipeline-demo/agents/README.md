# Demo-Owned Native Agent Definitions

This directory is the native launch source used by the interactive full-pipeline demo pack.

The demo startup command sets `AGENTSYS_AGENT_DEF_DIR` to this path and launches `--agents gpu-kernel-coder` through the selected provider tool lane.

The tracked assets here are intentionally minimal and focused on demo startup:

- recipe selectors under `brains/brain-recipes/`
- tool adapters under `brains/tool-adapters/`
- config and credential profile roots under `brains/cli-configs/` and `brains/api-creds/`
- one matching role prompt under `roles/gpu-kernel-coder/system-prompt.md`

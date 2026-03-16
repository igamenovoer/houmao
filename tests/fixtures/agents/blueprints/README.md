# Agent Blueprints

Blueprints are optional, secret-free bindings between:

- a brain recipe (`agents/brains/brain-recipes/...`)
- a role package (`agents/roles/...`)

Blueprints make named agent presets easy to share without embedding credentials.

The selected brain recipe still determines the tool, config profile, and credential profile. This lets multiple blueprints intentionally point at the same credential profile, or at different ones, without storing secrets in the blueprint itself.

The realm-controller CLI can source blueprints directly with `build-brain --blueprint ...` and `start-session --blueprint ...`, so blueprints are the native way to launch named agents while keeping credential choice inside the recipe layer.

# Claude Config Profile: default

This directory holds secret-free config that will be copied into the constructed runtime home for the `claude` tool adapter.

For Claude Code, most state is created at runtime under the configured `CLAUDE_CONFIG_DIR`. Keeping this profile minimal is fine; add files here only when you need to pin stable defaults (for example `settings.json`).

# Kimi Auth Bundles

Kimi demo runs expect a host-local bundle at `tests/fixtures/auth-bundles/kimi/personal-a-default/`.

Do not commit live Kimi credentials. Create the local bundle only on machines that run the demo. The demo preflights this exact directory and fails before tmux launch when it is missing.

The Kimi adapter can project optional files such as `config.toml`, `credentials/`, `credentials/kimi-code.json`, and `env/vars.env`. Keep secret-bearing files untracked.

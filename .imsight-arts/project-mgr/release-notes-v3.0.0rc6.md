Houmao 3.0.0rc6 adds configurable tmux launch servers, uses native Kimi configuration, and improves peer discovery across tmux servers.

## What Changed

- Select `user-default`, `new`, `socket`, or `houmao-default` in a launch profile or with `--tmux-server` for one launch. Houmao stores its shared default in the owner's registry, starts the server on demand, and saves each agent's socket for relaunch. [Launch Profiles](https://igamenovoer.github.io/houmao/getting-started/launch-profiles/#choosing-a-tmux-server)
- Look up peers, exchange mail, and address authorized terminal operations through saved records across tmux servers. Managed self queries use the current runtime manifest. The shared tmux adapter uses libtmux.
- Open the public gateway dashboard for a summary and browser entry into the bound native Web session. DSH Web opens the recorded conversation in its Workspace, including before the first prompt. [DSH Web](https://igamenovoer.github.io/houmao/reference/run-phase/dsh-web/)
- Provider startup uses the resolved launch environment. Supported agent tool releases and release candidates are accepted at or above their applicable version floors. [Launch Policy](https://igamenovoer.github.io/houmao/reference/build-phase/launch-policy/)

## Upgrade From 3.0.0rc5

- Move Kimi provider and model settings into native `config.toml`. To use numeric reasoning overrides, declare each model's native labels in order under `support_efforts`. Keep API keys in the private credential bundle. [Kimi Configuration](https://igamenovoer.github.io/houmao/reference/build-phase/launch-policy/#kimi-native-configuration)
- Local tmux-backed fixtures now share the Houmao server. Use `fixture.py prepare --tmux-server new` for runs that need a private server.

## Install the Candidate

```bash
uv tool install 'houmao==3.0.0rc6'
npx skills add https://github.com/igamenovoer/houmao-skills#v3.0.0rc6
```

[Compare v3.0.0rc5 and v3.0.0rc6](https://github.com/igamenovoer/houmao/compare/v3.0.0rc5...v3.0.0rc6)

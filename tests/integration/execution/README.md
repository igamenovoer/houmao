# Execution-Owner Integration Fixtures

These CI fixtures create disposable Linux accounts and a narrowly scoped sudo rule. Run them only with explicit opt-in and passwordless sudo for test setup:

```bash
HOUMAO_EXECUTION_INTEGRATION=1 pixi run python -m pytest tests/integration/execution/test_fixture_boundaries.py -q
```

The `execution_accounts` fixture yields an `ExecutionSandbox` with `operator`, `owner`, and `second_owner` account records. Each record provides `name`, `uid`, `gid`, and `home`. The fixture root lives under `/tmp/houmao-execution-*`, outside the checkout. Agent credentials and generated SSH keys stay there. The fixture never imports ambient authentication or mounts a container-control socket.

`run_as(account, argv)` uses setup authority for a probe under a fixture account. `delegated(owner, input=...)` instead invokes sudo as the genuinely restricted operator. Its policy allows only the root-owned, no-argument `helper` entrypoint as the two designated owners. Direct `/usr/bin/id`, extra helper arguments, and root RunAs are rejected. Use `install_helper(script)` to replace the probe with a fixed invocation of a prepared Houmao owner entrypoint; do not accept arbitrary request arguments in that wrapper.

For native-transport qualification, `authorize_helper_arguments(arguments)` changes the fixture policy to permit exactly one fixed literal argument sequence. The product helper sequence is `internals executor serve-stdio --policy <outside-checkout-policy>`. A different policy path or extra argument remains denied. This method belongs only to root-authorized test setup. `delegated()` follows the recorded sequence; the normal product transport can address the same helper and fixed policy directly.

The real owner-stdio probes additionally require an explicitly selected installed entrypoint:

```bash
HOUMAO_EXECUTION_INTEGRATION=1 HOUMAO_EXECUTION_ENTRYPOINT=/absolute/path/to/houmao-mgr pixi run python -m pytest tests/integration/execution/test_owner_stdio.py -q
```

These probes invoke the actual product `execute_request` transport as the restricted operator. They check sudo and SSH fresh-context description, owner UID/GID, policy refusal, exact sudo argument restrictions, and absence of state initialization. They do not claim native-agent birth or lifecycle qualification.

`test_native_owner.py` supplies the separate native qualification. Select `HOUMAO_DSH_EXECUTABLE` explicitly. The ACP case requires DSH 0.2.2-rc.3 or later, and the Web case requires DSH 0.2.2-rc.1 or later. Both cases use the maintained fixture preparation workflow with explicit cloud case/model metadata, a synthetic external credential file, a controlled loopback model server, and unattended operation. The cases exercise DSH ACP through sudo and DSH Web through SSH. They provision target-readable copies of installed Node/Bun binaries.

Each native case creates two agents under one target account and execution profile. Existing adapter auth-file mappings project two generated Ed25519 key references into the agents' separate native homes. Only digest values enter assertions. The tests verify full launch/control/refresh/relaunch, file ownership, target-only paths, sibling key/generation preservation, and same-name tmux isolation. Shared account permissions remain shared; these checks do not claim key confidentiality between same-UID processes.

`tmux(account, argv)` always supplies the account's explicit private socket and discards inherited `TMUX` and `TMUX_PANE` through a minimal subprocess environment. Tests may use identical session names on different fixture servers. Teardown targets only those recorded sockets and never uses the shared localhost server. Production lifecycle tests should retain unrelated sessions on the same private server to verify targeted teardown.

The `execution_ssh` fixture starts a separate OpenSSH daemon bound to a random loopback port. It uses generated host/client keys, a pinned known-hosts file, public-key authentication, and one allowed owner account. It disables password authentication, forwarding, and user-supplied SSH environment. Its `client_argv(command)` returns explicit batch-mode client arguments; pass them to `run_as(operator, ...)`. The fixture leaves the system SSH daemon and its configuration unchanged.

Setup records exact account identities, its single sudoers path, and newly started process sessions. Teardown removes the delegation policy first, stops only recorded process sessions and private tmux servers, and deletes only matching fixture accounts. If an account identity changes or removal fails, teardown reports the failure and preserves the scratch root for investigation. Calling `close()` twice is safe after successful cleanup. A setup exception also invokes cleanup.

The fixture-boundary tests establish actual UID switching, owner file modes, restricted sudo denials, tmux server isolation, SSH host verification, and cleanup. They do not replace product launch/control qualification. The latter must use the real owner stdio helper and maintained agent fixture workflow with an explicitly selected case and model.

Container qualification requires an explicitly prepared existing Docker container and authorized native Docker exec access. The development environment inspected on 2026-11-17 had no Docker/Podman executable or daemon socket; its root capability bounding set lacked `CAP_SYS_ADMIN` and `CAP_NET_ADMIN`. These fixtures do not install or start a host/container daemon. A missing prerequisite must remain visible as unverified container qualification.

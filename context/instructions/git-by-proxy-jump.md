# Access Git via SSH ProxyJump

This guide shows how to use Git over SSH when direct access is blocked and you must hop through a relay host.

## 1) Prepare keys

- Relay host key (example): `~/.ssh/fast-access`
- Git host key (example): `~/.ssh/id_ed25519`
- Host-specific note: on `b200-1`, use `~/.ssh/id_ed25519` for Git pull/push authentication.
- Load your Git key into agent:

```bash
ssh-add ~/.ssh/id_ed25519
ssh-add -l
```

## 2) Create an SSH config for jump routing

Put this in a config file (for example `/tmp/git_proxyjump_ssh_config`):

```sshconfig
Host relay-host
  HostName <relay-hostname-or-ip>
  User <relay-user>
  IdentityFile ~/.ssh/fast-access
  IdentitiesOnly yes

Host github.com
  User git
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  ProxyJump relay-host
```

Replace placeholders:
- `<relay-hostname-or-ip>`
- `<relay-user>`

## 3) Test SSH path

```bash
ssh -F /tmp/git_proxyjump_ssh_config -T git@github.com
```

You should get a successful auth message from GitHub (no shell access is expected).

## 4) Use Git with this SSH route

One-off push/pull:

```bash
GIT_SSH_COMMAND='ssh -F /tmp/git_proxyjump_ssh_config' git pull --rebase origin main
GIT_SSH_COMMAND='ssh -F /tmp/git_proxyjump_ssh_config' git push origin main
```

Or set remote to SSH form once:

```bash
git remote set-url origin git@github.com:<owner>/<repo>.git
```

## 5) Typical issues

- `Permission denied (publickey)`: wrong key, key not loaded, or wrong user (`git` for GitHub).
- `fetch first` on push: remote has new commits; run `git pull --rebase origin <branch>` first.
- Passphrase prompt in non-interactive context: load key via `ssh-add` before running Git commands.

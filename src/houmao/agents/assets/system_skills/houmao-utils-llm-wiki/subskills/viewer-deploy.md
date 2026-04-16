# Viewer Deploy Subskill

Use this subskill when the user asks to deploy, install, launch, repair, or update the bundled LLM Wiki web viewer.

## Inputs To Resolve

- **Installation directory**: required. If the user did not supply it, ask for a local directory where the viewer should be installed.
- **Wiki root**: required before launch. It must be an existing LLM Wiki root containing `wiki/index.md` and `audit/`. If there is not exactly one safe candidate, ask the user.
- **Port**: ask when the user has a preference; otherwise default to `8080`.
- **Host**: default to `127.0.0.1`. Do not bind to `0.0.0.0` unless the user explicitly asks and understands the viewer has no authentication.
- **Author**: optional. When provided, it is passed to the viewer so feedback files use that author.

## Preferred Automation

Run the helper from the skill root:

```bash
python3 scripts/deploy_viewer.py \
  --install-dir "<install-dir>" \
  --wiki "<wiki-root>" \
  --port 8080
```

Useful variants:

```bash
# Prepare, install, and build without starting the server.
python3 scripts/deploy_viewer.py --install-dir "<install-dir>" --wiki "<wiki-root>" --launch-mode no-launch

# Force npm or bun.
python3 scripts/deploy_viewer.py --install-dir "<install-dir>" --wiki "<wiki-root>" --package-manager npm
python3 scripts/deploy_viewer.py --install-dir "<install-dir>" --wiki "<wiki-root>" --package-manager bun

# Start in the foreground when the user wants to own the process.
python3 scripts/deploy_viewer.py --install-dir "<install-dir>" --wiki "<wiki-root>" --launch-mode foreground
```

## Deployment Behavior

The helper copies `viewer/audit-shared/` and `viewer/web/` from this skill into the installation directory. It excludes packaged lockfiles, `node_modules/`, `dist/`, and TypeScript build metadata. It writes `.llm-wiki-viewer.json` so later runs know the directory is managed.

If the installation directory is inside a Git worktree, the helper adds local-only excludes under `.git/info/exclude` and writes installation-local ignore rules when doing so will not modify a tracked `.gitignore`.

## Tooling Behavior

The helper detects `node`, `npm`, and `bun`.

- Prefer `node` plus `npm` when available.
- Use `bun` only when npm is unavailable or the user explicitly requests bun.
- Stop with a clear message if required tools are missing.

The install/build order is always:

```bash
cd "<install-dir>/audit-shared"
npm install --no-package-lock
npm run build

cd "<install-dir>/web"
npm install --no-package-lock
npm run build
```

With bun fallback:

```bash
cd "<install-dir>/audit-shared"
bun install
bun run build

cd "<install-dir>/web"
bun install
bun run build
```

## Launch Behavior

Launch command shape:

```bash
cd "<install-dir>/web"
npm start -- --wiki "<wiki-root>" --port "<port>" --host 127.0.0.1
```

Or with bun:

```bash
cd "<install-dir>/web"
bun run start -- --wiki "<wiki-root>" --port "<port>" --host 127.0.0.1
```

After launch, report:

- local URL, usually `http://127.0.0.1:8080`
- installation directory
- wiki root
- exact launch command
- PID, process-group stop command, and log path when launched in background

## Troubleshooting

- Missing `node`/`npm`: ask the user to install Node.js with npm, or install bun and rerun with `--package-manager bun`.
- Port busy: ask for another port and rerun with `--port <port>`.
- Invalid wiki root: ask for the directory that contains `README.md`, `wiki/`, `audit/`, `log/`, `raw/`, and `outputs/`.
- Install failure: report the failed command and leave the copied source in place so the user can inspect it.

# DSH Development Runtime Preparation

These utilities prepare the reference source and an explicitly selected development executable for Houmao's DSH integration. They are development tooling, excluded from the product wheel. No command launches an agent, loads `.env`, discovers credentials, or changes a personal DSH home.

## Prepare the Pinned Reference

From the Houmao project root:

```bash
pixi run python tools/dsh/prepare.py source
```

The helper clones `https://github.com/deepseek-ai/deepseek-harness.git` into the ignored `extern/orphan/deepseek-harness/` tree and selects commit `39163dd30f703a79079e2d2446545cff3c453738`. An existing checkout must already have that exact revision and no tracked modifications. The helper refuses to reset an existing checkout. Inspect this reference before looking up external DSH behavior elsewhere.

## Select an Installed Runtime

```bash
pixi run python tools/dsh/prepare.py inspect --executable "$(command -v dsh)"
```

The selected executable must be inside an identifiable `@deepseek-ai/dsh` package. Both its package version and actual `--version` output must match the pinned source's CLI package version, `0.2.2-rc.3`. Inspection invokes only `--version`, in a disposable working directory with isolated `DSH_HOME` and `DSH_AGENTS_HOME` values. It excludes ambient provider credentials from that subprocess.

The JSON report includes the exact source revision, resolved executable location, executable SHA-256, installed DSH package inventory, and a digest of the installed DeepSeek package metadata and JavaScript. Published npm metadata does not attest to a source commit. The report keeps that limitation explicit; equal version strings do not prove equal source and executable bytes. ACP's placeholder `agentInfo.version` is insufficient evidence.

## Install an Isolated Matching Runtime

If the existing executable differs from the pinned reference, preserve the existing installation and prepare a separate runtime:

```bash
pixi run python tools/dsh/prepare.py runtime
pixi run python tools/dsh/prepare.py inspect \
  --executable "$PWD/tmp/dsh/runtime/node_modules/.bin/dsh"
```

Bun must be available on `PATH`; the package requires Node.js 24.9.0 or newer. The helper reads the exact npm package version from the verified reference, writes a minimal private package manifest, and installs it with Bun. It uses `tmp/dsh/runtime/` by default. `--root /external/path` selects another development root; existing nonempty roots require this helper's ownership marker. The resulting `build.json`, package lockfile, and installed packages remain generated development state. Repeated preparation preserves the explicit version and re-identifies the installed bytes.

An explicit npm installation is also available when Bun's registry resolution is unavailable:

```bash
pixi run python tools/dsh/prepare.py runtime --installer npm --root "$PWD/tmp/dsh/npm-runtime"
```

The helper records the selected installer and hashes its generated lockfile. It does not silently switch package managers after an installation failure.

The helper does not change the caller's `PATH` or Bun global packages. Supply the isolated executable explicitly to qualification and launch configuration. Product agent launch never installs npm packages or clones this reference.

## Qualify the Identified Build

Runtime preparation establishes executable identity. Native conformance tests must separately establish companion loading, literal system-prompt injection, ACP capabilities, admission and recovery behavior, and physical journal format. Live provider checks must record their model, protocol, and actual outcome independently of hermetic checks. A prepared or version-matched executable is not a passing live qualification result.

For a source-built executable, follow the pinned upstream [source build instructions](../../extern/orphan/deepseek-harness/README.md): `pnpm install`, `pnpm run build`, then `pnpm dsh`. Run build commands only against a dedicated development checkout. Preserve the source revision and build artifact hashes in the qualification report; do not infer provenance from an unrelated global executable.

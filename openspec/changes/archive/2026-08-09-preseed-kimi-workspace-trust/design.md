## Context

See proposal.md for motivation. The smoke run (`tmp/kimi-native-prompt-smoke/run-20260809T123938Z`) proved the modal blocks unattended TUI input; the Kimi 0.34 source checkout (`extern/orphan/kimi-code`) provided the exact suppression contract:

- The TUI shows the modal only when `getWorkspaceTrustInfo(cwd)` reports untrusted (`apps/kimi-code/src/tui/kimi-tui.ts:3151` `maybeRunWorkspaceTrustPrompt`). No CLI flag, config value, or `--auto` bypasses it; declining exits the program.
- Trust state is presence-only: a JSON document at `$KIMI_CODE_HOME/workspace-trust/<encodeWorkDirKey(cwd)>` (`packages/agent-core-v2/src/workspace/workspaceTrust/workspaceTrustService.ts:101` trusts when the document exists; content is not validated on read).
- `encodeWorkDirKey` (`packages/agent-core-v2/src/_base/utils/workdir-slug.ts:29`): normalize the path (backslashes to slashes, strip trailing slashes), take the basename, slugify (lowercase, non-`[a-z0-9._-]` runs → `-`, strip leading/trailing `-`, truncate to 40 chars, re-strip), append `_<sha256(normalized path)[:12]>`. Verified: a Python recomputation reproduced the live record `wd_run-20260809t123938z_8f56092721df` byte-for-byte.
- Canonical record bytes: `{"root": "<cwd>", "trustedAt": <epoch milliseconds>}` (compact JSON, no trailing newline — `JsonAtomicDocumentStore` encodes via plain `JSON.stringify`).
- Trust gates only project-level MCP config (`.mcp.json`, `.kimi-code/mcp.json`); headless `-p` never shows the modal but follows the same trusted/untrusted config split.

## Goals / Non-Goals

**Goals:**

- Unattended managed Kimi launches (headless and TUI, fresh and relaunch) never surface the trust modal and always follow the trusted config path.
- The pre-seed shares the `SYSTEM.md` lifecycle: one writer, two enforcement points (brain construction, provider start), provenance recorded.
- `as_is` launches and non-Kimi tools are untouched.

**Non-Goals:**

- Changing Kimi's trust semantics or upstream feature requests.
- Pre-trusting anything beyond the launch working directory (no recursive or parent-dir trust).
- Migrating existing stopped brains; the next provider start re-asserts the record anyway.
- Project MCP server management; trust only un-gates Kimi's native loading decision.

## Decisions

### 1. Implement `encodeWorkDirKey` parity in Python with a pinned test vector

Add a small helper (sibling to `kimi_system_prompt.py`) that reproduces `encodeWorkDirKey` exactly, including the slug truncation edge cases. Pin the verified live vector (`/data/.../run-20260809T123938Z` → `wd_run-20260809t123938z_8f56092721df`) plus synthetic edge cases (uppercase, spaces, trailing slash, long names, dot names) in unit tests.

Alternative considered: shell out to `kimi` or node to compute the key. Rejected — the algorithm is ten lines and a runtime dependency on the provider for home construction is circular.

### 2. One writer, gated on Kimi + unattended, enforced at provider start

`ensure_kimi_workspace_trust(home_path, workdir)` writes the canonical record by atomic replacement (same pattern as `ensure_kimi_system_prompt`), returns typed provenance (state `projected`/`unchanged`, path, workspace key), and is a no-op byte-wise when the record already matches. Provider-start planning calls it with the launch plan's actual working directory before process start (fresh headless, fresh TUI, relaunch), repairing drift and covering relaunch-into-different-workdir, gated on the Kimi tool lane and `operator_prompt_mode == unattended`.

Alternative considered: also pre-seed at brain construction, mirroring the two-enforcement-point `SYSTEM.md` lifecycle. Rejected during implementation — the trust key is derived from the launch working directory, and `BuildRequest` has no working-directory concept (brains are built workdir-agnostic), so a build-time write has no correct input. Provider start is the first point where the real workdir is known, and it runs before every provider process, so no case is left uncovered.

### 3. Provenance extends the existing native-prompt payload, no schema change

Add a `workspace_trust` sub-object beside `native_system_prompt` in the same metadata/provenance payloads (path, key, state). Session-manifest and launch-plan schemas carry these as metadata maps, so no schema version bump.

### 4. No trust removal on stop or rebuild

The record is harmless provider state inside a Houmao-owned home; cleanup follows the home lifecycle (clean rebuild removes the whole home). Houmao never writes "untrust" — Kimi defines untrust as deletion, and deletion only matters if the operator uses the home manually, which is unsupported.

## Risks / Trade-offs

- [A later Kimi release changes the key algorithm or record shape] → The pinned live test vector fails loudly on requalification; the strategy declares `>=0.34.0` source evidence, same posture as the `SYSTEM.md` contract.
- [Pre-trusting weakens Kimi's MCP injection guard] → The workdir is operator-chosen at launch and the home is Houmao-owned; unattended mode already asserts the operator's intent to run without confirmations. `as_is` keeps the native guard.
- [Kimi validates record content in a future release] → We write the full canonical shape (`root`, `trustedAt` epoch ms), not a minimal stub, so content validation would still pass.

## Migration Plan

1. Land the helper, both call sites, provenance, and unit tests together.
2. Re-run the smoke harness TUI leg: it passes when `trust_dialog_accepted` is `false` (no modal mounted) — update the script to fail if the modal appears rather than accepting it.
3. No operator migration: existing stopped brains self-heal on next provider start.

Rollback is release-level: remove the call sites; homes with stray trust records are unaffected.

## Open Questions

None. The suppression contract is verified against the 0.34.0 source and a live record.

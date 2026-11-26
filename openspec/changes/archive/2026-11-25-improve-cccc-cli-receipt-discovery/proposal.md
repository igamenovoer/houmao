# Proposal

## Why

The live receiver-v2 round trip succeeded, but the sending agent made five failed CLI probes while discovering the Group and inspecting a handoff. Issues [#101](https://github.com/igamenovoer/houmao/issues/101) and [#102](https://github.com/igamenovoer/houmao/issues/102) identify two fixes for that workflow: accept the existing short message handle for receipt lookup and explain the correct CLI inputs at the point of use.

## What Changes

- Let `chat deliveries --handle HANDLE` inspect the exact selected event in gateway mode. The caller can use the handle from an incoming request fence or the `event.handle` from its own send or reply result.
- Retain `--event-ref` for gateway receipt lookup and `--event-id` for direct receipt lookup. Report unsupported target forms with mode-specific guidance.
- Support `members --group GROUP_ID` as an assertion about the Group already selected by the gateway instance or direct Actor profile. On mismatch, report a conflict and explain how to select the intended binding.
- Add a top-level `--version` that reports the installed CLI version. Show exact common commands and mode-specific receipt inputs in help, and give safe, actionable diagnostics for invalid options and stale targeting.

## Capabilities

### New Capabilities

### Modified Capabilities

- `cccc-chat` covers scoped receipt targets, Group assertions in membership discovery, and installed CLI version, help, and usage diagnostics.

## Impact

The optional `houmao-cccc` package, its gateway `GET /chat/deliveries` and `GET /members` routes, its docs, and its verification suites are affected. Receipt lookup uses the existing CCCC receiver-v2 operation and gateway read permission. The compact request fence retains its current fields and uses the existing handle.

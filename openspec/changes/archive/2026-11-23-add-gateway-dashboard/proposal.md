# Proposal

## Why

Opening a live gateway's base URL returns an API 404. Operators need to know the Web entry path or obtain a temporary link from the manager before they can reach the native agent interface. [Houmao issue #91](https://github.com/igamenovoer/houmao/issues/91)

## What Changes

- Serve a public, read-only dashboard at `GET /` that identifies the managed agent and shows its backend, run mode, gateway health, and native Web availability.
- Offer **Open agent Web UI** for a verified live Web agent on the owner-local origin. Use the existing bare `/v1/web/enter` path so the live roster selects immediate entry or admin sign-in.
- Explain unavailable Web entry on non-Web agents, when the native surface is down, and when an operator visits through an advertised proxy.
- Document the gateway base URL as the starting point for browser access.

## Capabilities

### New Capabilities

- `gateway-dashboard` defines the browser landing page, safe agent summary, and native Web entry action.

### Modified Capabilities

- `agent-gateway-reference-docs` adds the dashboard workflow and owner-local entry guidance.

## Impact

The gateway HTTP app gains one public HTML route and a packaged page. The implementation uses existing runtime observation and Web entry authority. The gateway contract and operator guides describe the page and its relationship to the existing API and manager CLI.

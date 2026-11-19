# HTTPS Gateway Integration Verification

The unmodified `test_authenticated_gateway_over_a_verified_https_proxy` passed alone in 1.81 seconds on the working source. The attached and detached self-status cases also passed with capability publication and registry lock acquisition disabled. The mixed integration batch occasionally returned HTTP 503 for the first public message after successful signed self mail status.

A disposable copy of the HTTPS test forced the failing order with thread events. It held the HTTP caller inside `OwnerPromptClaim.active()` after the caller had read the incomplete worker state. The worker confirmed handoff and settled the claim. The caller then observed the settled claim as inactive, and the response contained `dispatch_outcome=unknown` for `contact-1`.

The probe returned the same HTTP 503 on the working source and on the independently archived pre-change `HEAD` source, loaded through `PYTHONPATH`. Both runs printed the assertion that the caller's claim check saw the already-settled attempt. The failure occurs in the public-dispatch confirmation after self status has returned. The preceding Codex service change also recorded a mixed-batch failure followed by an isolated pass. [Previous integration results](../../archive/2026-11-19-run-modes-06-add-codex-app-server-service/logs/implementation.md).

A later run of the full HTTPS module passed both self-status cases and returned HTTP 409 with `dispatch_outcome=not_sent` for `contact-2`. The fixture sent that request immediately after the first native handoff acknowledgment. The ready-only public prompt path can refuse a second request while the first worker finishes its settlement.

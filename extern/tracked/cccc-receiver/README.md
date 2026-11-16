# CCCC External Receiver Compatibility Dependency

This directory contains the durable source inputs for Houmao's CCCC provider interface. `upstream.json` pins the upstream repository/revision and ordered patch series; `PROTOCOL.md` describes the Actor-scoped protocol. The patches are maintained external dependency changes and are not imported or compiled when a Houmao gateway starts.

Prepare a disposable source checkout and build it through the native Pixi workspace. The preparation helper verifies the pinned revision and applies the tracked patch series without modifying `extern/orphan/cccc`. Runtime credentials, CCCC data, build caches, and prepared sources belong outside tracked product source. Report the revision, patch digest, and negotiated protocol version in qualification evidence.

The source license is preserved in `LICENSE.upstream`; the patch series modifies that licensed upstream source. This compatibility extension has not been accepted upstream. A future upstream replacement must pass the same receiver conformance, owner-isolation, delivery-fencing, and installed-plugin qualification checks before replacing these patches.

The ordered series keeps qualified CHAT in `0001-external-receiver.patch` and adds explicit deferred Mail in `0002-explicit-deferred-mail.patch`. Mail adds expected-cursor reads, pre-commit complete-response bounds, retained ledger operation decisions, and content-free native notices. Both patches must be prepared and built together for the Mail capability flags; never replace an existing prepared checkout with a different patch selection in place.

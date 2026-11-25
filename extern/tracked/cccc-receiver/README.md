# CCCC External Receiver Compatibility Dependency

This directory contains the durable source inputs for Houmao's CCCC provider interface. `upstream.json` pins the upstream repository/revision and ordered patch series; `PROTOCOL.md` describes the Actor-scoped protocol. The patches are maintained external dependency changes and are not imported or compiled when a Houmao gateway starts.

Prepare a disposable source checkout and build it through the native Pixi workspace. The preparation helper verifies the pinned revision and applies the tracked patch series without modifying `extern/orphan/cccc`. Runtime credentials, CCCC data, build caches, and prepared sources belong outside tracked product source. Report the revision, patch digest, and negotiated protocol version in qualification evidence.

The source license is preserved in `LICENSE.upstream`; the patch series modifies that licensed upstream source. This compatibility extension has not been accepted upstream. A future upstream replacement must pass the same receiver conformance, owner-isolation, delivery-fencing, and installed-plugin qualification checks before replacing these patches.

The series introduces external chat in `0001-external-receiver.patch`, adds deferred Mail in `0002-explicit-deferred-mail.patch`, upgrades intake and handoff to protocol v2 in `0003-queued-receiver-v2.patch`, and adds durable gateway tool-read claims in `0004-gateway-queue-reads.patch`. The preparation helper applies the complete ordered series to a fresh source checkout.

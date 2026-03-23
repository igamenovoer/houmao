# mail-ping-pong-responder

Thin responder role for the headless mail ping-pong gateway demo.

This role relies on the runtime-owned mailbox skill for transport details and adds only the ping-pong reply behavior: read the newest actionable initiator message in the tracked thread, reply in-thread with the current UTC time, then stop.

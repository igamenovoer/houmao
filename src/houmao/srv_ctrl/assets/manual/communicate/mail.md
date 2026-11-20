# Leave a Durable Handoff

Choose a prompt for work the receiver should take on now. Choose mail when the work needs a durable inbox record, a reply thread, or attachments. Use scoped `mail resolve-live` to identify the mailbox and select `offline` or `online` explicitly. Pin that channel's binding with `--expected-binding-id`.

From a verified managed session, use `agents self mail send` to send as that agent. For an operator-origin note to a supported local filesystem inbox, use selected-agent `mail post`. Include the requested action, relevant artifact, and reply expectation. Retain the channel, binding ID, and message reference for follow-up. `mail peek` inspects a message while preserving its read status.

Check authoritative delivery evidence. A submission-only receipt needs follow-up against the mailbox, and a stored message has its own delivery status independent of any wakeup. `houmao-mgr agents self mail --help` shows the current-session commands. [Scoped Mail Reference](https://igamenovoer.github.io/houmao/reference/cli/agents-mail/)

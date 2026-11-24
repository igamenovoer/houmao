# Agent Email Communication Skill Delta

## ADDED Requirements

### Requirement: Mail skill explains conditional attachment authority
The mail skill SHALL explain that a gateway send, reply, or post requires its corresponding action on the selected mailbox binding. It SHALL describe `mail.attachment.owner_file` as an additional action required on that binding when the gateway request includes owner-file attachments.

#### Scenario: Basic mail write carries no attachments
- **WHEN** the caller sends, replies, or posts a text-only message
- **THEN** the skill describes the selected binding's ordinary mail action as the relevant gateway permission
- **AND THEN** it leaves the existing authorized no-gateway fallback available where supported

#### Scenario: Mail write includes an owner-file attachment
- **WHEN** the caller sends, replies, or posts with an owner-file attachment
- **THEN** the skill explains that the caller also needs `mail.attachment.owner_file` on the same channel and binding
- **AND THEN** it directs the caller to the maintained access workflow for any required grant

## ADDED Requirements

### Requirement: Mailbox system skills are not projected into Gemini homes
Runtime mailbox-skill projection SHALL expose no Gemini destination, `.gemini/skills` path, or Gemini discovery contract.

#### Scenario: Mailbox skill destination rejects Gemini
- **WHEN** mailbox skill projection receives Gemini as its target tool
- **THEN** projection fails as unsupported
- **AND THEN** it does not create `.gemini/skills` content

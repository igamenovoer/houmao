# Generic Responses Setup

Use the shared test-fixture helper with an explicit API case, model, and endpoint. It renders the selected URL into run-local configuration and supplies `OPENAI_API_KEY` through private credential state. The tracked config has an empty required URL and contains no model or account endpoint default.

For a direct native build, supply `OPENAI_BASE_URL` in the selected local auth environment. Brain construction fills the generic provider URL from that value and rejects absent or conflicting routing. Codex uses Responses; a Chat Completions-only endpoint is insufficient. Optional native-login tests use their explicitly imported login state independently.

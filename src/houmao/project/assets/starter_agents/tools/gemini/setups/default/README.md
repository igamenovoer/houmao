# Gemini Config Profile: default

This directory holds secret-free config that will be copied into the constructed runtime home for the `gemini` tool adapter (under `.gemini/`).

Keeping this profile minimal is fine. Add files here only when you want to pin stable defaults (for example `.gemini/settings.json`).

For maintained unattended Gemini startup, Houmao owns the effective `approval-mode`, sandbox posture, and any restrictive settings keys that would shrink the built-in tool surface. Copied settings are preserved unless they conflict with that unattended contract.

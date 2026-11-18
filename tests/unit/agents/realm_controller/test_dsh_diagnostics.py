"""Verify redaction before DSH's diagnostic text reaches a public boundary."""

from houmao.agents.realm_controller.backends.dsh_diagnostics import sanitize_dsh_diagnostic


def test_scrubs_longest_raw_encoded_and_labeled_credentials() -> None:
    """Remove complete overlapping secrets, URL encodings, and common auth spellings."""

    text = (
        "HTTP 400\ninvalid request root/key root%2fkey root%2Fkey; "
        'Bearer unsigned-bearer, sk-provider-secret, "apiKey": "quoted secret", '
        "access_token=ambient-token, launch_token: other-token\nCookie: a=one; b=two"
    )
    diagnostic = sanitize_dsh_diagnostic(text, secret_values=("root", "root/key"))
    assert diagnostic.startswith("HTTP 400 invalid request [REDACTED] [REDACTED] [REDACTED]")
    assert diagnostic.count("[REDACTED]") == 9
    assert "\n" not in diagnostic
    assert sanitize_dsh_diagnostic(diagnostic) == diagnostic


def test_truncates_after_scrubbing_and_normalizing() -> None:
    """Truncation cannot preserve the starting fragment of a known secret."""

    text = "failure\n\x1b[31mprivate-key-credential\x1b[0m " + ("details " * 50)
    diagnostic = sanitize_dsh_diagnostic(
        text, secret_values=("private-key-credential",), max_length=25
    )
    assert diagnostic.startswith("failure [REDACTED]")
    assert len(diagnostic) == 25
    assert diagnostic.endswith("…")

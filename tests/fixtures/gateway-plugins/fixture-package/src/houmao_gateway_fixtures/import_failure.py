"""Fail import with a private sentinel that host status must suppress."""

raise RuntimeError("PRIVATE_FIXTURE_EXCEPTION_MUST_NOT_LEAK")

"""Registry-first passive server for distributed agent coordination.

This package implements ``houmao-passive-server``, a lightweight FastAPI
application that discovers agents from the shared filesystem registry and
provides coordination, observation, and proxy services on top of them.

Unlike ``houmao-server``, this server has no CAO compatibility layer, no
child process supervision, and no registration-backed session admission.
It is designed as a clean replacement aligned with the distributed-agent
architecture described in ``context/design/future/distributed-agent-architecture.md``.
"""

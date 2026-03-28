"""Small helper used by the mailbox demo fixture."""


def compose_status_note(task_name: str) -> str:
    """Return a short deterministic status note for one mailbox task."""

    normalized = task_name.strip() or "mailbox task"
    return f"Status: {normalized} is ready for the next mailbox turn."

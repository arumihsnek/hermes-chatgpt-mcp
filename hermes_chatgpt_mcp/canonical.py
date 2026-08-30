"""Compatibility shims for canonical Hermes primitives.

The MCP adapter must call one canonical mutation boundary.  This module keeps
that boundary local for older hermes-agent installations that have not yet
exposed the safe metadata primitive on ``kanban_db``.
"""
from __future__ import annotations


def update_task_fields(hermes, conn, task_id: str, *, title=None, body=None, priority=None, author: str):
    def field(value, name, default=None):
        return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)

    before = hermes.get_task(conn, task_id)
    if before is None:
        raise LookupError(f"unknown task {task_id}")
    if str(field(before, "status", "")) == "triage":
        raise ValueError(f"task {task_id} is not editable")
    requested = {name: value for name, value in (("title", title), ("body", body), ("priority", priority)) if value is not None}
    changed_fields = [name for name, value in requested.items() if field(before, name) != value]
    if changed_fields:
        assignments = ", ".join(f"{name} = ?" for name in changed_fields)
        conn.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", [requested[name] for name in changed_fields] + [task_id])
        hermes.add_comment(conn, task_id, author, "Edited — updated " + ", ".join(changed_fields))
        append_event = getattr(hermes, "_append_event", None)
        if append_event is not None:
            append_event(conn, task_id, "edited_fields", {"by": author, "changed_fields": changed_fields})
    return changed_fields

"""Session summary report generation.

Extracted from graph_executor.py — generates human-readable markdown
summaries when a workflow reaches a terminal state.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pixl.models.node_instance import NodeState

if TYPE_CHECKING:
    from pixl.models.session import WorkflowSession
    from pixl.models.workflow import WorkflowSnapshot
    from pixl.storage import WorkflowSessionStore


def save_session_summary(
    *,
    session: WorkflowSession,
    snapshot: WorkflowSnapshot,
    store: WorkflowSessionStore,
    session_dir: Path,
    artifacts_dir: Path,
) -> None:
    """Generate and save a human-readable session summary.

    Called when workflow reaches terminal state (completed/failed/cancelled).
    """
    events = store.load_events(session.id)

    if not events:
        return

    started_at = events[0].timestamp
    completed_at = events[-1].timestamp
    duration_seconds = (completed_at - started_at).total_seconds()

    # Count events by type
    event_counts: dict = {}
    for e in events:
        event_counts[e.type] = event_counts.get(e.type, 0) + 1

    stages = []
    for node_id, node in snapshot.graph.nodes.items():
        instance = session.get_node_instance(node_id)
        if not instance:
            stages.append(
                {
                    "stage": node_id,
                    "type": node.type.value,
                    "status": "skipped",
                    "duration": "-",
                }
            )
            continue

        state = instance.get("state", "")
        started = instance.get("started_at")
        ended = instance.get("ended_at")

        duration_str = "-"
        if started and ended:
            start = datetime.fromisoformat(started)
            end = datetime.fromisoformat(ended)
            stage_duration = (end - start).total_seconds()
            duration_str = f"{stage_duration:.1f}s"

        if state == NodeState.TASK_COMPLETED.value:
            status = "completed"
        elif state == NodeState.GATE_APPROVED.value:
            status = "approved"
        elif state == NodeState.GATE_REJECTED.value:
            status = "rejected"
        elif state == NodeState.TASK_FAILED.value:
            status = "failed"
        elif state == NodeState.GATE_WAITING.value:
            status = "waiting"
        elif state == NodeState.TASK_RUNNING.value:
            status = "running"
        else:
            status = state

        stages.append(
            {
                "stage": node_id,
                "type": node.type.value,
                "status": status,
                "duration": duration_str,
            }
        )

    # Determine final status
    final_status = session.compute_status_with_snapshot(snapshot)
    status_emoji = {
        "completed": "✅",
        "failed": "❌",
        "cancelled": "⚠️",
        "paused": "⏸️",
        "running": "🔄",
        "created": "📝",
    }.get(final_status.value, "❓")

    lines = []
    lines.append("# Workflow Session Summary")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| **Status** | {status_emoji} {final_status.value.upper()} |")
    lines.append(f"| **Session ID** | `{session.id}` |")
    lines.append(f"| **Workflow** | {snapshot.template_id} v{snapshot.template_version} |")
    lines.append(f"| **Feature** | {session.feature_id} |")
    lines.append(f"| **Started** | {started_at.strftime('%Y-%m-%d %H:%M:%S')} |")
    lines.append(f"| **Ended** | {completed_at.strftime('%Y-%m-%d %H:%M:%S')} |")
    lines.append(
        f"| **Duration** | {duration_seconds:.1f} seconds ({duration_seconds / 60:.1f} minutes) |"
    )
    lines.append(f"| **Total Stages** | {len(snapshot.graph.nodes)} |")
    lines.append(f"| **Total Events** | {len(events)} |")
    lines.append("")

    # Stage breakdown
    lines.append("## Stage Breakdown")
    lines.append("")
    lines.append("| Stage | Type | Status | Duration |")
    lines.append("|-------|------|--------|----------|")
    for stage in stages:
        status_icon = {
            "completed": "✅",
            "approved": "✅",
            "rejected": "❌",
            "failed": "❌",
            "waiting": "⏳",
            "running": "🔄",
            "skipped": "⏭️",
        }.get(stage["status"], "❓")
        lines.append(
            f"| {stage['stage']} | {stage['type']} | "
            f"{status_icon} {stage['status']} | {stage['duration']} |"
        )
    lines.append("")

    # Artifacts produced
    lines.append("## Artifacts")
    lines.append("")

    if artifacts_dir.exists():
        artifact_files = [f for f in artifacts_dir.rglob("*") if f.is_file()]
        if artifact_files:
            for artifact in sorted(artifact_files):
                rel_path = artifact.relative_to(artifacts_dir)
                size = artifact.stat().st_size
                lines.append(f"- `{rel_path}` ({size} bytes)")
            lines.append("")
        else:
            lines.append("No artifacts produced.")
            lines.append("")
    else:
        lines.append("No artifacts directory found.")
        lines.append("")

    # Event summary
    lines.append("## Event Summary")
    lines.append("")
    for event_type, count in sorted(event_counts.items()):
        lines.append(f"- **{event_type}**: {count}")
    lines.append("")

    # Session files
    lines.append("## Session Files")
    lines.append("")
    lines.append(f"Session data stored in: `{session_dir}`")
    lines.append("")
    lines.append("| File/Dir | Description |")
    lines.append("|----------|-------------|")
    lines.append("| `pixl.db` | Session state, events, and snapshots (SQLite) |")
    lines.append("| `artifacts/` | Generated artifacts (if any) |")
    lines.append("| `summary.md` | This summary file |")
    lines.append("")

    # Commands to resume/view
    lines.append("## Commands")
    lines.append("")
    lines.append("```bash")
    lines.append("# View events")
    lines.append(f"pixl events {session.id}")
    lines.append("")
    lines.append("# View session status")
    lines.append("pixl status --workflow")
    lines.append("")
    lines.append("# Resume if paused")
    lines.append(f"pixl resume {session.id}")
    lines.append("```")
    lines.append("")

    session_dir.mkdir(parents=True, exist_ok=True)
    summary_file = session_dir / "summary.md"
    summary_file.write_text("\n".join(lines))

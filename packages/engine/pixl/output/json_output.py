"""JSON output formatting for machine consumption."""

import json
import sys
from datetime import datetime
from typing import Any

from pixl.models.feature import Feature


class JsonOutput:
    """Structured JSON output for pixl CLI.

    Outputs newline-delimited JSON (JSONL) for streaming consumption.
    Each line is a complete JSON object representing an event.
    """

    def __init__(self, stream=None) -> None:
        self._stream = stream or sys.stdout

    def _emit(self, event_type: str, data: dict[str, Any] | None = None, **kwargs) -> None:
        """Emit a JSON event."""
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        }
        if data:
            event["data"] = data

        self._stream.write(json.dumps(event) + "\n")
        self._stream.flush()

    # Basic output methods (mirror Console interface)

    def print(self, message: str, style: str | None = None) -> None:
        """Emit a print event."""
        self._emit("print", message=message)

    def info(self, message: str) -> None:
        """Emit an info event."""
        self._emit("info", message=message)

    def success(self, message: str) -> None:
        """Emit a success event."""
        self._emit("success", message=message)

    def warning(self, message: str) -> None:
        """Emit a warning event."""
        self._emit("warning", message=message)

    def error(self, message: str) -> None:
        """Emit an error event."""
        self._emit("error", message=message)

    def meta(self, message: str) -> None:
        """Emit a meta event."""
        self._emit("meta", message=message)

    def status(self, message: str) -> None:
        """Emit a status event (for progress updates)."""
        self._emit("status", message=message)

    def markdown(self, content: str) -> None:
        """Emit markdown content."""
        self._emit("markdown", content=content)

    # Feature display methods

    def feature_row(self, feature: Feature) -> None:
        """Emit a feature row."""
        self._emit("feature", data=feature.model_dump(mode="json"))

    def feature_table(self, features: list[Feature], title: str = "Features") -> None:
        """Emit features as a list."""
        self._emit(
            "features",
            data=[f.model_dump(mode="json") for f in features],
            title=title,
            count=len(features),
        )

    def feature_detail(self, feature: Feature) -> None:
        """Emit detailed feature information."""
        self._emit("feature_detail", data=feature.model_dump(mode="json"))

    # Stats display

    def stats(self, stats: dict[str, int]) -> None:
        """Emit backlog statistics."""
        self._emit("stats", data=stats)

    # Progress display (no-ops for JSON, use status events instead)

    def progress(self, description: str = "Working...") -> "JsonProgressContext":
        """Create a progress context (emits start/end events)."""
        return JsonProgressContext(self, description)

    def spinner(self, message: str) -> "JsonSpinnerContext":
        """Create a spinner context (emits start/end events)."""
        return JsonSpinnerContext(self, message)

    # Cost display

    def cost_warning(self, cost: float, threshold: float) -> None:
        """Emit cost warning."""
        if cost >= threshold:
            self._emit("cost_warning", cost=cost, threshold=threshold)

    def cost_summary(self, cost: float, tokens: int) -> None:
        """Emit cost summary."""
        self._emit("cost_summary", cost=cost, tokens=tokens)

    # Additional JSON-specific methods

    def start(self, command: str, feature_id: str | None = None) -> None:
        """Emit command start event."""
        self._emit("start", command=command, feature_id=feature_id)

    def complete(
        self,
        success: bool,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Emit command completion event."""
        self._emit(
            "complete",
            success=success,
            result=result,
            error=error,
        )

    def tool_call(
        self,
        tool_name: str,
        tool_id: str | None = None,
        input_data: dict[str, Any] | None = None,
    ) -> None:
        """Emit tool call event."""
        self._emit(
            "tool_call",
            tool=tool_name,
            tool_id=tool_id,
            input=input_data,
        )

    def tool_result(
        self,
        tool_name: str,
        tool_id: str | None = None,
        output: str | None = None,
        error: str | None = None,
    ) -> None:
        """Emit tool result event."""
        self._emit(
            "tool_result",
            tool=tool_name,
            tool_id=tool_id,
            output=output,
            error=error,
        )

    def thinking(self, content: str) -> None:
        """Emit thinking content."""
        self._emit("thinking", content=content)

    def text(self, content: str) -> None:
        """Emit text content from assistant."""
        self._emit("text", content=content)

    def tokens(self, input_tokens: int, output_tokens: int, model: str) -> None:
        """Emit token usage."""
        self._emit(
            "tokens",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            model=model,
        )


class JsonProgressContext:
    """Context manager for progress tracking in JSON mode."""

    def __init__(self, output: JsonOutput, description: str) -> None:
        self._output = output
        self._description = description
        self._task_id: int | None = None

    def __enter__(self) -> "JsonProgressContext":
        self._output._emit("progress_start", description=self._description)
        return self

    def __exit__(self, *args) -> None:
        self._output._emit("progress_end", description=self._description)

    def add_task(self, description: str, total: int = 100) -> int:
        """Add a task (returns task ID)."""
        self._task_id = 0
        self._output._emit(
            "progress_task",
            task_id=self._task_id,
            description=description,
            total=total,
        )
        return self._task_id

    def update(self, task_id: int, advance: int = 1) -> None:
        """Update task progress."""
        self._output._emit("progress_update", task_id=task_id, advance=advance)


class JsonSpinnerContext:
    """Context manager for spinner in JSON mode."""

    def __init__(self, output: JsonOutput, message: str) -> None:
        self._output = output
        self._message = message

    def __enter__(self) -> "JsonSpinnerContext":
        self._output._emit("spinner_start", message=self._message)
        return self

    def __exit__(self, *args) -> None:
        self._output._emit("spinner_end", message=self._message)

    def update(self, message: str) -> None:
        """Update spinner message."""
        self._message = message
        self._output._emit("spinner_update", message=message)

"""Output context for managing output format globally."""

from contextvars import ContextVar
from enum import StrEnum

from pixl.output.console import Console
from pixl.output.json_output import JsonOutput

class OutputFormat(StrEnum):
    """Output format options."""

    TEXT = "text"
    JSON = "json"

# Global context variable for output format
_output_format: ContextVar[OutputFormat] = ContextVar("output_format", default=OutputFormat.TEXT)
_output_instance: ContextVar[Console | JsonOutput | None] = ContextVar(
    "output_instance", default=None
)

def set_output_format(fmt: OutputFormat) -> None:
    """Set the global output format."""
    _output_format.set(fmt)
    _output_instance.set(None)

def get_output_format() -> OutputFormat:
    """Get the current output format."""
    return _output_format.get()

def get_output() -> Console | JsonOutput:
    """Get the output instance for the current format.

    Returns either a Console (for text mode) or JsonOutput (for json mode).
    The instance is cached per context.
    """
    instance = _output_instance.get()
    if instance is None:
        fmt = _output_format.get()
        instance = JsonOutput() if fmt == OutputFormat.JSON else Console()
        _output_instance.set(instance)
    return instance

def is_json_mode() -> bool:
    """Check if we're in JSON output mode."""
    return _output_format.get() == OutputFormat.JSON

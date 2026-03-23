"""Pixl output formatting."""

from pixl.output.console import Console, console
from pixl.output.context import (
    OutputFormat,
    get_output,
    get_output_format,
    is_json_mode,
    set_output_format,
)
from pixl.output.json_output import JsonOutput

__all__ = [
    "Console",
    "console",
    "JsonOutput",
    "OutputFormat",
    "get_output",
    "get_output_format",
    "set_output_format",
    "is_json_mode",
]

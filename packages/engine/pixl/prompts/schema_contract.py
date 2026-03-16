"""Schema-derived payload contract rendering for prompt injection.

Keeps prompt instructions aligned with JSON Schema by deriving compact,
deterministic guidance directly from schema files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def load_json_schema(schema_path: str | Path) -> dict[str, Any] | None:
    """Load a JSON schema from disk.

    Returns None when the file is missing or malformed.
    """
    path = Path(schema_path)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def render_payload_contract(
    schema_data: Mapping[str, Any],
    *,
    heading: str = "## Payload Contract (Derived from output_schema)",
) -> str:
    """Render compact payload requirements from a JSON Schema."""
    required = _required_fields(schema_data)
    enum_constraints = _enum_constraints(schema_data)
    example_payload = _canonical_example_payload(schema_data, required, enum_constraints)

    lines = [
        heading,
        "",
        "Your `<pixl_output>.payload` MUST satisfy this schema-derived contract:",
    ]

    if required:
        required_keys = ", ".join(f"`{key}`" for key in required)
        lines.append(f"- Required keys: {required_keys}")
    else:
        lines.append("- Required keys: none")

    if enum_constraints:
        lines.append("- Enum constraints:")
        for key, values in enum_constraints.items():
            rendered = " | ".join(f"`{value}`" for value in values)
            lines.append(f"  - `{key}`: {rendered}")

    if example_payload:
        lines.extend(
            [
                "- Canonical minimal payload example:",
                "```json",
                json.dumps(example_payload, indent=2),
                "```",
            ]
        )

    return "\n".join(lines)


def render_payload_contract_from_path(
    schema_path: str | Path,
    *,
    heading: str = "## Payload Contract (Derived from output_schema)",
) -> str | None:
    """Load a schema and render payload contract text."""
    schema_data = load_json_schema(schema_path)
    if schema_data is None:
        return None
    return render_payload_contract(schema_data, heading=heading)


def _required_fields(schema_data: Mapping[str, Any]) -> list[str]:
    raw = schema_data.get("required")
    if not isinstance(raw, list):
        return []
    required: list[str] = []
    for item in raw:
        if isinstance(item, str):
            required.append(item)
    return required


def _enum_constraints(schema_data: Mapping[str, Any]) -> dict[str, list[str]]:
    properties = schema_data.get("properties")
    if not isinstance(properties, Mapping):
        return {}

    constraints: dict[str, list[str]] = {}
    for key, value in properties.items():
        if not isinstance(key, str):
            continue
        if not isinstance(value, Mapping):
            continue
        raw_enum = value.get("enum")
        if not isinstance(raw_enum, list):
            continue

        enum_values: list[str] = []
        for enum_item in raw_enum:
            if isinstance(enum_item, str):
                enum_values.append(enum_item)
            else:
                enum_values.append(str(enum_item))
        if enum_values:
            constraints[key] = enum_values
    return constraints


def _canonical_example_payload(
    schema_data: Mapping[str, Any],
    required: list[str],
    enum_constraints: dict[str, list[str]],
) -> dict[str, Any]:
    properties = schema_data.get("properties")
    if not isinstance(properties, Mapping):
        return {}

    example: dict[str, Any] = {}
    for key in required:
        prop_schema = properties.get(key)
        if not isinstance(prop_schema, Mapping):
            continue
        example[key] = _infer_example_value(prop_schema)

    # If there are no required fields, still provide one deterministic enum hint.
    if not example and enum_constraints:
        first_key = sorted(enum_constraints.keys())[0]
        first_value = enum_constraints[first_key][0]
        example[first_key] = first_value

    return example


def _infer_example_value(prop_schema: Mapping[str, Any]) -> Any:
    raw_enum = prop_schema.get("enum")
    if isinstance(raw_enum, list) and raw_enum:
        return raw_enum[0]

    raw_type = prop_schema.get("type")
    if raw_type == "string":
        return "<value>"
    if raw_type == "integer":
        return 0
    if raw_type == "number":
        return 0
    if raw_type == "boolean":
        return False
    if raw_type == "array":
        return []
    if raw_type == "object":
        return {}
    if raw_type == "null":
        return None
    return "<value>"


__all__ = [
    "load_json_schema",
    "render_payload_contract",
    "render_payload_contract_from_path",
]

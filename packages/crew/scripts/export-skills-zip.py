#!/usr/bin/env python3
"""Export pixl-crew skills as ZIP files compatible with claude.ai uploads.

claude.ai supports custom skill uploads via Settings > Features as ZIP files.
This script repackages SKILL.md files with cleaned frontmatter (name + description only)
and bundles any local references/scripts/examples directories.

Usage:
    python3 scripts/export-skills-zip.py [OPTIONS]

Options:
    --output-dir DIR   Output directory (default: dist/skills-zips/)
    --skill NAME       Export a single skill by directory name
    --mega-zip         Also create one ZIP containing all individual ZIPs
    --dry-run          Validate and report only, no ZIPs created
    --verbose          Verbose logging
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
import zipfile
from pathlib import Path

# --- Constants ---

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "dist" / "skills-zips"

NAME_OVERRIDES: dict[str, str] = {
    "claude-md": "project-md-generator",
}

RESERVED_WORDS = {"anthropic", "claude"}
NAME_REGEX = re.compile(r"^[a-z0-9-]+$")
MAX_NAME_LEN = 64
MAX_DESC_LEN = 1024
XML_TAG_RE = re.compile(r"<[a-zA-Z/][^>]*>")

CLAUDE_CODE_ONLY_FIELDS = {"allowed-tools", "argument-hint", "context", "disable-model-invocation"}
BUNDLE_DIRS = {"references", "scripts", "examples"}
EXCLUDE_FILES = {"config.json", ".DS_Store"}

BODY_LINE_WARN = 500

CLAUDE_CODE_MARKERS = ["Agent tool", "subagent", "pixl ", "pixl_cli", "run_in_background"]


# --- Frontmatter parsing ---

def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from SKILL.md content. Returns (fields, body)."""
    if not text.startswith("---"):
        return {}, text

    end = text.find("\n---", 3)
    if end == -1:
        return {}, text

    fm_block = text[4:end]
    body = text[end + 4:].lstrip("\n")

    fields: dict[str, str] = {}
    for line in fm_block.split("\n"):
        line = line.strip()
        if not line:
            continue
        colon = line.find(":")
        if colon == -1:
            continue
        key = line[:colon].strip()
        value = line[colon + 1:].strip()
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        fields[key] = value

    return fields, body


def rebuild_skill_md(name: str, description: str, body: str) -> str:
    """Reconstruct SKILL.md with only name + description in frontmatter."""
    # Escape description for YAML if it contains special chars
    needs_quotes = any(c in description for c in (':', '"', "'", "{", "}", "[", "]", "#", "&", "*", "!", "|", ">", ","))
    if needs_quotes:
        escaped_desc = '"' + description.replace("\\", "\\\\").replace('"', '\\"') + '"'
    else:
        escaped_desc = description

    return f"---\nname: {name}\ndescription: {escaped_desc}\n---\n\n{body}"


# --- Validation ---

def validate_name(name: str) -> list[str]:
    """Validate skill name for claude.ai compatibility. Returns list of errors."""
    errors = []
    if not NAME_REGEX.match(name):
        errors.append(f"Name '{name}' contains invalid characters (allowed: a-z, 0-9, -)")
    if len(name) > MAX_NAME_LEN:
        errors.append(f"Name '{name}' exceeds {MAX_NAME_LEN} chars ({len(name)})")
    for word in RESERVED_WORDS:
        if word in name:
            errors.append(f"Name '{name}' contains reserved word '{word}'")
    return errors


def validate_description(description: str) -> list[str]:
    """Validate skill description for claude.ai compatibility. Returns list of errors."""
    errors = []
    if not description:
        errors.append("Description is empty")
    if len(description) > MAX_DESC_LEN:
        errors.append(f"Description exceeds {MAX_DESC_LEN} chars ({len(description)})")
    if XML_TAG_RE.search(description):
        errors.append("Description contains XML tags")
    return errors


def check_warnings(name: str, body: str, skill_dir: Path) -> list[str]:
    """Check for non-blocking warnings."""
    warnings = []
    body_lines = body.count("\n") + 1
    if body_lines > BODY_LINE_WARN:
        warnings.append(f"Body has {body_lines} lines (>{BODY_LINE_WARN})")

    # Check for crew-level reference paths
    if "references/" in body:
        # Distinguish local (bundled) vs crew-level references
        for match in re.finditer(r"(?:Read|read)\s+`?references/", body):
            warnings.append("References crew-level references/ path (may not be bundled)")
            break

    # Check for Claude Code-specific features
    for marker in CLAUDE_CODE_MARKERS:
        if marker in body:
            warnings.append(f"Uses Claude Code feature: '{marker}'")
            break

    return warnings


# --- ZIP creation ---

def collect_bundle_files(skill_dir: Path) -> list[tuple[str, Path]]:
    """Collect files from references/, scripts/, examples/ subdirs. Returns (arcname, filepath) pairs."""
    files = []
    for subdir_name in BUNDLE_DIRS:
        subdir = skill_dir / subdir_name
        if not subdir.is_dir():
            continue
        for root, _, filenames in os.walk(subdir):
            root_path = Path(root)
            for filename in filenames:
                if filename in EXCLUDE_FILES:
                    continue
                filepath = root_path / filename
                arcname = str(filepath.relative_to(skill_dir))
                files.append((arcname, filepath))
    return files


def create_skill_zip(
    skill_dir: Path,
    output_dir: Path,
    dry_run: bool,
    verbose: bool,
) -> tuple[str | None, list[str], list[str]]:
    """Process a single skill directory. Returns (zip_path | None, errors, warnings)."""
    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.exists():
        return None, [f"No SKILL.md in {skill_dir.name}"], []

    text = skill_md_path.read_text(encoding="utf-8")
    fields, body = parse_frontmatter(text)

    raw_name = fields.get("name", skill_dir.name)
    description = fields.get("description", "")

    # Apply name overrides
    name = NAME_OVERRIDES.get(raw_name, raw_name)

    # Validate
    errors = validate_name(name)
    errors.extend(validate_description(description))

    if errors:
        return None, errors, []

    warnings = check_warnings(name, body, skill_dir)

    if dry_run:
        if verbose:
            bundle_files = collect_bundle_files(skill_dir)
            print(f"  OK: {name} ({len(bundle_files)} bundled files)")
            for w in warnings:
                print(f"    WARN: {w}")
        return name, [], warnings

    # Build cleaned SKILL.md
    cleaned_md = rebuild_skill_md(name, description, body)

    # Collect bundled files
    bundle_files = collect_bundle_files(skill_dir)

    # Create ZIP
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{name}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{name}/SKILL.md", cleaned_md)
        for arcname, filepath in bundle_files:
            zf.write(filepath, f"{name}/{arcname}")

    if verbose:
        print(f"  ZIP: {zip_path.name} ({len(bundle_files)} bundled files)")
        for w in warnings:
            print(f"    WARN: {w}")

    return str(zip_path), [], warnings


# --- Main ---

def main() -> int:
    parser = argparse.ArgumentParser(description="Export pixl-crew skills as claude.ai-compatible ZIPs")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--skill", type=str, help="Export a single skill by directory name")
    parser.add_argument("--mega-zip", action="store_true", help="Also create one ZIP containing all individual ZIPs")
    parser.add_argument("--dry-run", action="store_true", help="Validate and report only")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    if not SKILLS_DIR.is_dir():
        print(f"ERROR: Skills directory not found: {SKILLS_DIR}", file=sys.stderr)
        return 1

    # Discover skill directories
    if args.skill:
        skill_dirs = [SKILLS_DIR / args.skill]
        if not skill_dirs[0].is_dir():
            print(f"ERROR: Skill directory not found: {args.skill}", file=sys.stderr)
            return 1
    else:
        skill_dirs = sorted(
            d for d in SKILLS_DIR.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        )

    if not skill_dirs:
        print("No skills found.", file=sys.stderr)
        return 1

    mode = "DRY RUN" if args.dry_run else "EXPORT"
    print(f"\n{'='*60}")
    print(f"pixl-crew skill export ({mode})")
    print(f"{'='*60}")
    print(f"Skills directory: {SKILLS_DIR}")
    print(f"Output directory: {args.output_dir}")
    print(f"Skills found: {len(skill_dirs)}")
    print()

    exported = []
    all_errors: dict[str, list[str]] = {}
    all_warnings: dict[str, list[str]] = {}
    zip_paths: list[str] = []

    for skill_dir in skill_dirs:
        result, errors, warnings = create_skill_zip(
            skill_dir, args.output_dir, args.dry_run, args.verbose,
        )

        if errors:
            all_errors[skill_dir.name] = errors
            if args.verbose:
                print(f"  FAIL: {skill_dir.name}")
                for e in errors:
                    print(f"    ERROR: {e}")
        else:
            exported.append(skill_dir.name)
            if result and not args.dry_run:
                zip_paths.append(result)

        if warnings:
            all_warnings[skill_dir.name] = warnings

    # Mega-ZIP
    if args.mega_zip and zip_paths and not args.dry_run:
        mega_path = args.output_dir / "pixl-crew-skills.zip"
        with zipfile.ZipFile(mega_path, "w", zipfile.ZIP_DEFLATED) as mega:
            for zp in zip_paths:
                mega.write(zp, Path(zp).name)
        if args.verbose:
            print(f"\n  MEGA: {mega_path.name} ({len(zip_paths)} skills)")

    # Summary
    print(f"\n{'='*60}")
    print(f"Summary")
    print(f"{'='*60}")
    print(f"  Exported: {len(exported)}")
    print(f"  Errors:   {len(all_errors)}")
    print(f"  Warnings: {len(all_warnings)}")

    if all_errors:
        print(f"\nFailed skills:")
        for name, errors in sorted(all_errors.items()):
            for e in errors:
                print(f"  {name}: {e}")

    if all_warnings and args.verbose:
        print(f"\nWarnings:")
        for name, warnings in sorted(all_warnings.items()):
            for w in warnings:
                print(f"  {name}: {w}")

    if not args.dry_run and exported:
        print(f"\nOutput: {args.output_dir}/")
        if args.mega_zip:
            print(f"Mega-ZIP: {args.output_dir}/pixl-crew-skills.zip")

    print()
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())

---
name: file-parser
description: "Parse and extract content from PDF, text, and JSON files using the file-parser CLI. Use when asked to read a PDF, extract text from a document, parse a JSON file, process scanned PDFs with OCR, or when an agent needs to consume file contents for analysis. Supports page selection for PDFs and OCR for scanned documents."
allowed-tools: Bash, Read, Write, Glob, Grep
argument-hint: "<file path> [--pages 1-3,5] [--ocr auto]"
---

## Overview

Wrapper around the `file-parser` CLI (`hamzaPixl/file-parser-cli`). Extracts content from PDF, text, and JSON files so agents can consume and process the data. Automatically detects file type from extension and routes to the correct parser.

## Prerequisites

The CLI must be installed. Check with:

```bash
command -v file-parser || (cd ~/code/pixl/file-parser-cli && uv sync)
```

If not on PATH, use the full invocation: `cd ~/code/pixl/file-parser-cli && uv run file-parser ...`

## Step 1: Detect File Type

1. Receive the file path from the user or agent
2. Check the file exists: `ls -la <path>`
3. Determine the parser from extension:
   - `.pdf` → `pdf` command
   - `.txt`, `.md`, `.csv`, `.log`, `.env`, `.yml`, `.yaml`, `.toml`, `.ini`, `.cfg` → `text` command
   - `.json`, `.jsonl`, `.geojson` → `json` command
4. If extension is ambiguous, check file content with `file <path>`

## Step 2: Extract Content

### PDF Files

```bash
cd ~/code/pixl/file-parser-cli && uv run file-parser pdf "<file_path>"
```

Options:

- **Page selection**: `--pages 1-3,5,8-10` (1-indexed, comma-separated ranges)
- **OCR mode**: `--ocr auto` (OCR only when text extraction returns nothing)
- **OCR always**: `--ocr always` (force OCR on all pages, useful for scanned docs)
- **OCR DPI**: `--ocr-dpi 300` (higher = better quality, slower)

Strategy:

1. First try without OCR: `uv run file-parser pdf "<path>"`
2. If output is empty or garbled, retry with: `uv run file-parser pdf "<path>" --ocr auto`
3. For large PDFs (50+ pages), extract in chunks: `--pages 1-20`, then `--pages 21-40`, etc.

### Text Files

```bash
cd ~/code/pixl/file-parser-cli && uv run file-parser text "<file_path>"
```

Options:

- **Encoding**: `--encoding utf-8` (default), `--encoding latin-1`, etc.

### JSON Files

```bash
cd ~/code/pixl/file-parser-cli && uv run file-parser json "<file_path>"
```

Options:

- **Compact output**: `--compact` (no whitespace, useful for large files)
- **Encoding**: `--encoding utf-8`

## Step 3: Process Extracted Content

After extraction, process based on the task context:

1. **Summarization**: Summarize the extracted text for the user
2. **Data extraction**: Pull specific fields, tables, or structured data from the content
3. **Analysis**: Answer questions about the document content
4. **Transformation**: Convert the content to another format (e.g., PDF table → JSON, PDF → markdown)
5. **Integration**: Feed the extracted content into another workflow (e.g., content pipeline, translation)

For large documents, extract relevant sections only (use `--pages`) rather than consuming the entire file.

## Step 4: Output

Present the results based on what was requested:

- **Direct display**: Show the extracted content to the user
- **Save to file**: Write processed content to a new file
- **Pass to next step**: Feed into another skill or agent workflow

## Validation Checklist

- [ ] **FP-01**: File exists and is readable
- [ ] **FP-02**: Correct parser was selected for the file type
- [ ] **FP-03**: Content was successfully extracted (non-empty output)
- [ ] **FP-04**: For PDFs: page count matches expected (check with extraction output)
- [ ] **FP-05**: For OCR: fallback to OCR was attempted if initial extraction was empty
- [ ] **FP-06**: Output was delivered in the format the user/agent requested

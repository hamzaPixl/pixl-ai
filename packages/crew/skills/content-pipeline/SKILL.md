---
name: content-pipeline
description: "AUTOMATED multi-step LLM content generation pipeline: discovery → research → generate → translate → validate → assemble. Use when you need to batch-generate content across multiple pages/sections, auto-translate, or run quality validation loops. For content STRATEGY and manual copywriting, use /content-marketing instead."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<content brief or topic>"
disable-model-invocation: true
---

## Overview

Generates content through a structured pipeline: requirements discovery, research, parallel content generation, optional translation, quality validation, and final assembly.

## Required References

Before starting, read `references/writing/writing-plans.md` for content structure, tone guidelines, and editorial workflow patterns.

## Step 1: Discovery

1. Understand content requirements (type, audience, tone, length)
2. Identify brand voice and style guidelines
3. Determine output format (markdown, HTML, JSON)
4. Check for multilingual requirements

## Step 2: Research

1. Analyze existing content for style and patterns
2. Gather domain knowledge relevant to the topic
3. Identify key messages and value propositions
4. Create content outline

## Step 3: Generate (Parallel)

Generate content sections in parallel:

1. Each section gets its own generation pass
2. Follow the brand voice and style guidelines
3. Apply humanizer patterns from `references/writing/humanizer.md` to avoid AI-sounding text
4. Include SEO keywords where applicable

## Step 4: Translate (Conditional)

**Only if multilingual content is requested.**

1. Translate content to target locales
2. Adapt idioms and cultural references (not word-for-word)
3. Preserve formatting and structure
4. Flag untranslatable terms

## Step 5: Validate

1. Check content against requirements
2. Verify tone and voice consistency
3. Check for factual accuracy
4. Validate links and references
5. Run spelling and grammar checks

## Step 6: Assemble

1. Combine all content sections into final output
2. Apply consistent formatting
3. Add metadata (author, date, tags)
4. Generate table of contents if applicable

---
name: multi-agent-pipeline
description: "Build a multi-agent LLM pipeline with orchestrator, domain agents, and structured output. Use when asked to create an agent system, multi-agent workflow, LLM pipeline, agent orchestration, or any system with multiple specialized AI agents."
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
argument-hint: "<pipeline description or domain areas>"
context: fork
disable-model-invocation: true
---

## Overview

Scaffolds a multi-agent LLM pipeline with an orchestrator that coordinates specialized domain agents. Produces structured output with type safety.

## Step 1: Discovery

1. Understand the pipeline's purpose and domain areas
2. Identify how many agents are needed and their specializations
3. Determine the orchestration pattern (sequential, parallel, map-reduce)
4. Define input/output schemas

## Step 2: Base Agent

1. Create the base agent class/interface
2. Define the agent contract (input, process, output)
3. Add LLM provider abstraction (support multiple providers)
4. Implement structured output parsing

## Step 3: Domain Agents (Parallel)

For each identified domain area:

1. Create a specialized agent with domain-specific system prompt
2. Define the agent's input/output schema
3. Add domain-specific tools and knowledge
4. Test the agent in isolation

## Step 4: Orchestrator

1. Build the orchestrator that coordinates domain agents
2. Implement the chosen orchestration pattern
3. Add error handling and retry logic
4. Wire input routing and output aggregation

## Step 5: Runner

1. Create the pipeline entry point
2. Add configuration for LLM provider, model, temperature
3. Implement logging and tracing
4. Add cost tracking

## Step 6: Verify

- [ ] Each domain agent produces valid output in isolation
- [ ] Orchestrator correctly routes to agents
- [ ] Full pipeline runs end-to-end
- [ ] Structured output matches expected schema
- [ ] Error handling works (agent failure, timeout)

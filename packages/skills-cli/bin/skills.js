#!/usr/bin/env node
/**
 * skills — install Claude Code skills from GitHub
 *
 * Usage:
 *   npx @pixl/skills add <github-url> [--skill <name>] [--scope user|project] [--force]
 *
 * Examples:
 *   npx @pixl/skills add https://github.com/remotion-dev/skills --skill remotion-best-practices
 *   npx @pixl/skills add https://github.com/org/skills-repo               # auto-detect
 *   npx @pixl/skills add https://github.com/org/repo --scope project      # project-local
 */

import { add } from "../src/add.js";

const VERSION = "9.0.0";

function parseArgs(argv) {
  const args = argv.slice(2);
  const opts = { skill: null, scope: "user", force: false, token: null };
  const positional = [];

  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === "--skill" || a === "-s")     { opts.skill  = args[++i]; }
    else if (a === "--scope")              { opts.scope  = args[++i]; }
    else if (a === "--force" || a === "-f"){ opts.force  = true; }
    else if (a === "--token")              { opts.token  = args[++i]; }
    else if (a === "--version" || a === "-v") { console.log(VERSION); process.exit(0); }
    else if (a === "--help"   || a === "-h") { printHelp(); process.exit(0); }
    else if (!a.startsWith("-"))           { positional.push(a); }
  }

  return { positional, opts };
}

function printHelp() {
  console.log(`
  skills — install Claude Code skills from GitHub

  Usage:
    npx @pixl/skills <command> [options]

  Commands:
    add <github-url>   Install a skill from a GitHub repository

  Options for add:
    --skill  <name>    Skill directory to install (required if repo has multiple)
    --scope  <scope>   Install scope: user (default) or project
    --force            Overwrite if already installed
    --token  <token>   GitHub token (or set GITHUB_TOKEN env var)
    --version          Print version
    --help             Print this help

  Examples:
    npx @pixl/skills add https://github.com/remotion-dev/skills --skill remotion-best-practices
    npx @pixl/skills add https://github.com/org/my-skills --scope project
`);
}

async function main() {
  const { positional, opts } = parseArgs(process.argv);
  const [command, ...rest] = positional;

  if (!command || command === "help") {
    printHelp();
    process.exit(0);
  }

  if (command === "add") {
    const url = rest[0];
    if (!url) {
      console.error("  Error: missing GitHub URL\n  Usage: skills add <url> [--skill <name>]\n");
      process.exit(1);
    }
    try {
      await add(url, opts);
    } catch (err) {
      console.error(`\n  Error: ${err.message}\n`);
      process.exit(1);
    }
    return;
  }

  console.error(`  Unknown command: ${command}\n  Run 'skills --help' for usage.\n`);
  process.exit(1);
}

main();

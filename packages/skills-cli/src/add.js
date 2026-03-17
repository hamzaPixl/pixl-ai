import { parseGitHubUrl, listSkills, fetchSkillFiles, downloadFile } from "./github.js";
import { resolveInstallDir, writeFiles, existingVersion } from "./install.js";

/**
 * `skills add <url>` handler.
 *
 * @param {string} url      GitHub repo URL
 * @param {object} opts
 * @param {string} [opts.skill]   Specific skill name to install
 * @param {string} [opts.scope]   "user" | "project" (default: "user")
 * @param {string} [opts.token]   GitHub token (or GITHUB_TOKEN env var)
 * @param {boolean} [opts.force]  Overwrite existing skill
 */
export async function add(url, opts = {}) {
  const token = opts.token ?? process.env.GITHUB_TOKEN;
  const scope = opts.scope ?? "user";

  // Parse repo
  const { owner, repo } = parseGitHubUrl(url);
  console.log(`\n  source  github.com/${owner}/${repo}`);

  // Discover skills in the repo
  const available = await listSkills(owner, repo, token);
  if (available.length === 0) {
    throw new Error("No skills (SKILL.md) found in this repository.");
  }

  // Resolve which skill path to install
  let skillPath;
  if (opts.skill) {
    // Match against full path or last path component (e.g. "remotion" matches "skills/remotion")
    skillPath =
      available.find((p) => p === opts.skill) ??
      available.find((p) => p.split("/").pop() === opts.skill) ??
      available.find((p) => p.toLowerCase().includes(opts.skill.toLowerCase()));

    if (!skillPath) {
      console.error(
        `\n  Skill "${opts.skill}" not found. Available skills:\n\n${available.map((s) => `    ${s}`).join("\n")}\n`
      );
      process.exit(1);
    }
  } else if (available.length === 1) {
    skillPath = available[0];
    console.log(`  skill   ${skillPath} (auto-detected)`);
  } else {
    console.error(
      `\n  Multiple skills found. Use --skill <name> to pick one:\n\n${available
        .map((s) => `    ${s}`)
        .join("\n")}\n`
    );
    process.exit(1);
  }

  // Install under the last path component as the skill name
  const skillName = skillPath === "." ? repo : skillPath.split("/").pop();
  console.log(`  skill   ${skillName} (${skillPath})`);

  // Check for existing install
  const installDir = resolveInstallDir(skillName, scope);
  const existing = existingVersion(installDir);
  if (existing && !opts.force) {
    console.log(`\n  ⚠  already installed (${existing})`);
    console.log(`  Use --force to overwrite.\n`);
    process.exit(0);
  }

  // Fetch file list
  console.log(`  fetching file list...`);
  let skillFiles;
  try {
    skillFiles = await fetchSkillFiles(owner, repo, skillPath, token);
  } catch (err) {
    if (err.message.includes("404")) {
      throw new Error(`Skill path "${skillPath}" not found in ${owner}/${repo}`);
    }
    throw err;
  }

  if (skillFiles.length === 0) {
    throw new Error(`Skill directory "${skillName}" is empty.`);
  }

  console.log(`  downloading ${skillFiles.length} file(s)...`);

  // Download in parallel (capped at 5 concurrent)
  const CONCURRENCY = 5;
  const downloaded = [];
  for (let i = 0; i < skillFiles.length; i += CONCURRENCY) {
    const batch = skillFiles.slice(i, i + CONCURRENCY);
    const results = await Promise.all(
      batch.map(async (f) => ({
        path: f.path,
        content: await downloadFile(f.downloadUrl, token),
      }))
    );
    downloaded.push(...results);
  }

  // Write to disk
  const written = writeFiles(installDir, downloaded);

  console.log(`\n  ✓ installed ${skillName} → ${installDir}`);
  console.log(`    ${written.length} file(s) written`);
  console.log(`\n  Restart Claude Code to activate the skill.\n`);
}

import fs from "node:fs";
import path from "node:path";
import os from "node:os";

/**
 * Resolve the skills install directory.
 *
 * Scopes:
 *   user    → ~/.claude/skills/<name>/           (default)
 *   project → <cwd>/.claude/skills/<name>/
 *   local   → <cwd>/.claude/skills/<name>/       (alias for project)
 */
export function resolveInstallDir(skillName, scope = "user") {
  const base =
    scope === "user"
      ? path.join(os.homedir(), ".claude", "skills")
      : path.join(process.cwd(), ".claude", "skills");

  return path.join(base, skillName);
}

/**
 * Write files to the install directory, creating intermediate dirs.
 * files: Array<{ path: string, content: Buffer }>
 */
export function writeFiles(installDir, files) {
  const written = [];
  for (const { path: relPath, content } of files) {
    const dest = path.join(installDir, relPath);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.writeFileSync(dest, content);
    written.push(dest);
  }
  return written;
}

/**
 * Check whether a skill is already installed.
 * Returns the existing version string if SKILL.md has a version frontmatter field, else null.
 */
export function existingVersion(installDir) {
  const skillMd = path.join(installDir, "SKILL.md");
  if (!fs.existsSync(skillMd)) return null;
  const text = fs.readFileSync(skillMd, "utf8");
  const match = text.match(/^version:\s*(.+)$/m);
  return match ? match[1].trim() : "(no version)";
}

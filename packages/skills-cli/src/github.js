/**
 * GitHub API helpers — zero dependencies, uses native fetch (Node 18+).
 */

const GH_API = "https://api.github.com";

/**
 * Parse a GitHub URL into { owner, repo }.
 * Accepts:
 *   https://github.com/owner/repo
 *   https://github.com/owner/repo.git
 *   github.com/owner/repo
 */
export function parseGitHubUrl(url) {
  const cleaned = url.replace(/^https?:\/\//, "").replace(/\.git$/, "");
  const parts = cleaned.split("/").filter(Boolean);
  if (parts[0] !== "github.com" || parts.length < 3) {
    throw new Error(`Not a valid GitHub URL: ${url}`);
  }
  return { owner: parts[1], repo: parts[2] };
}

/**
 * Fetch JSON from the GitHub API with optional token auth.
 */
async function ghFetch(path, token) {
  const headers = {
    Accept: "application/vnd.github+json",
    "User-Agent": "@pixl/skills",
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${GH_API}${path}`, { headers });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`GitHub API ${res.status} for ${path}: ${body.slice(0, 200)}`);
  }
  return res.json();
}

/**
 * Discover skills in a repo by searching for SKILL.md files (up to 2 levels deep).
 * Returns an array of skill paths relative to the repo root (e.g. "remotion" or "skills/remotion").
 */
export async function listSkills(owner, repo, token) {
  const skillPaths = [];

  async function scan(apiPath, depth) {
    let contents;
    try {
      contents = await ghFetch(`/repos/${owner}/${repo}/contents/${apiPath}`, token);
    } catch {
      return;
    }
    const items = Array.isArray(contents) ? contents : [contents];

    const hasSkillMd = items.some((i) => i.type === "file" && i.name === "SKILL.md");
    if (hasSkillMd) {
      skillPaths.push(apiPath);
      return; // don't recurse into a skill dir
    }

    if (depth < 2) {
      for (const item of items) {
        if (item.type === "dir" && !item.name.startsWith(".")) {
          await scan(item.path, depth + 1);
        }
      }
    }
  }

  // Check root first, then subdirs
  const root = await ghFetch(`/repos/${owner}/${repo}/contents`, token);
  const rootItems = Array.isArray(root) ? root : [root];
  const rootHasSkillMd = rootItems.some((i) => i.type === "file" && i.name === "SKILL.md");

  if (rootHasSkillMd) {
    skillPaths.push(".");
  } else {
    for (const item of rootItems) {
      if (item.type === "dir" && !item.name.startsWith(".")) {
        await scan(item.path, 1);
      }
    }
  }

  return skillPaths;
}

/**
 * Recursively fetch all files in a skill directory.
 * Returns an array of { path: string (relative), downloadUrl: string }.
 */
export async function fetchSkillFiles(owner, repo, skillPath, token) {
  const files = [];
  // prefix to strip from item.path to get relative file path within the skill
  const stripPrefix = skillPath === "." ? "" : `${skillPath}/`;

  async function walk(apiPath) {
    const contentsPath =
      apiPath === "." ? `/repos/${owner}/${repo}/contents` : `/repos/${owner}/${repo}/contents/${apiPath}`;
    const contents = await ghFetch(contentsPath, token);
    const items = Array.isArray(contents) ? contents : [contents];
    for (const item of items) {
      if (item.type === "file") {
        files.push({
          path: stripPrefix ? item.path.replace(stripPrefix, "") : item.path,
          downloadUrl: item.download_url,
        });
      } else if (item.type === "dir") {
        await walk(item.path);
      }
    }
  }

  await walk(skillPath);
  return files;
}

/**
 * Download raw file content.
 */
export async function downloadFile(url, token) {
  const headers = { "User-Agent": "@pixl/skills" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error(`Download failed ${res.status}: ${url}`);
  return Buffer.from(await res.arrayBuffer());
}

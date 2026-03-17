import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { parseGitHubUrl } from "./github.js";
import { resolveInstallDir } from "./install.js";
import os from "node:os";
import path from "node:path";

describe("parseGitHubUrl", () => {
  it("parses standard https url", () => {
    const r = parseGitHubUrl("https://github.com/remotion-dev/skills");
    assert.equal(r.owner, "remotion-dev");
    assert.equal(r.repo, "skills");
  });

  it("parses .git suffix", () => {
    const r = parseGitHubUrl("https://github.com/org/repo.git");
    assert.equal(r.repo, "repo");
  });

  it("parses without protocol", () => {
    const r = parseGitHubUrl("github.com/owner/repo");
    assert.equal(r.owner, "owner");
    assert.equal(r.repo, "repo");
  });

  it("throws on non-github url", () => {
    assert.throws(() => parseGitHubUrl("https://gitlab.com/owner/repo"), /Not a valid GitHub URL/);
  });
});

describe("resolveInstallDir", () => {
  it("user scope resolves to ~/.claude/skills/<name>", () => {
    const dir = resolveInstallDir("my-skill", "user");
    assert.equal(dir, path.join(os.homedir(), ".claude", "skills", "my-skill"));
  });

  it("project scope resolves to <cwd>/.claude/skills/<name>", () => {
    const dir = resolveInstallDir("my-skill", "project");
    assert.equal(dir, path.join(process.cwd(), ".claude", "skills", "my-skill"));
  });
});

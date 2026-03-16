# Agent Scope Boundaries

Defines the file ownership, read-only access, forbidden actions, and output format for every agent role in the `/website-project` pipeline. These boundaries prevent file conflicts during parallel execution.

---

## Scope Rules

1. **Exclusive ownership:** Each file is owned by exactly one agent at any given time. Only the owning agent may create or modify that file.
2. **Read-only access:** All agents may read any file in the project, but writing is restricted to owned files only.
3. **No cross-boundary writes:** An agent that modifies a file outside its scope has violated the contract. The orchestrator should discard that change and re-delegate.
4. **Shared imports are read-only:** Files in `lib/`, `components/ui/`, and `node_modules/` are read-only for all section and layout agents. Only the orchestrator or devops agent may modify `lib/` files.

---

## Agent Role Boundaries

### 1. Frontend Engineer (Design Extraction) -- Phase 1

| Property              | Value                                                    |
| --------------------- | -------------------------------------------------------- |
| **Phase**             | 1 (Discovery)                                            |
| **Assigned files**    | None -- output only, no file creation                    |
| **Read-only scope**   | Reference URLs, Figma data, `references/frontend/*`      |
| **Forbidden actions** | Creating any project files, modifying any existing files |
| **Output format**     | Structured `discovery_packet.design` object (JSON/YAML)  |

### 2. Product Owner -- Phase 1

| Property              | Value                                                    |
| --------------------- | -------------------------------------------------------- |
| **Phase**             | 1 (Discovery)                                            |
| **Assigned files**    | None -- output only, no file creation                    |
| **Read-only scope**   | User brief, reference analysis output (if available)     |
| **Forbidden actions** | Creating any project files, modifying any existing files |
| **Output format**     | Structured `discovery_packet.tasks` object (JSON/YAML)   |

### 3. Explorer (Reference Analysis) -- Phase 1

| Property              | Value                                                      |
| --------------------- | ---------------------------------------------------------- |
| **Phase**             | 1 (Discovery)                                              |
| **Assigned files**    | None -- output only, no file creation                      |
| **Read-only scope**   | Reference URLs, competitor sites, `references/frontend/*`  |
| **Forbidden actions** | Creating any project files, modifying any existing files   |
| **Output format**     | Structured `discovery_packet.reference` object (JSON/YAML) |

### 4. Architect -- Phase 2

| Property              | Value                                                      |
| --------------------- | ---------------------------------------------------------- |
| **Phase**             | 2 (Architecture)                                           |
| **Assigned files**    | None -- output only, no file creation                      |
| **Read-only scope**   | `.context/discovery-packet.json`, all `references/*` files |
| **Forbidden actions** | Creating any project files, modifying any existing files   |
| **Output format**     | Structured `architecture_packet` object (JSON/YAML)        |

### 5. Frontend Engineer (Section Builder) -- Phase 3, Wave A

| Property              | Value                                                                                                                                                     |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Phase**             | 3 (Implementation, Wave A)                                                                                                                                |
| **Assigned files**    | Specific section files from the architect's implementation group (e.g., `components/sections/hero.tsx`, `components/sections/features.tsx`)               |
| **Read-only scope**   | `lib/*`, `components/ui/*`, `app/globals.css`, `references/*`, `.context/*`                                                                               |
| **Forbidden actions** | Modifying files outside assigned list, modifying `lib/` files, modifying other agents' section files, modifying `app/page-client.tsx` or `app/layout.tsx` |
| **Output format**     | React component files (`.tsx`) at the assigned file paths                                                                                                 |

#### Phase 3 Section Distribution Logic

The number of frontend engineer agents (N) is determined by the architect in Phase 2 based on:

1. **Section count:** Count the total number of section components to build.
2. **Complexity balance:** Group sections so each agent has roughly equal work. A complex section (e.g., pricing with toggle logic) counts as 1.5-2x a simple section (e.g., CTA banner).
3. **Typical grouping:**
   - 3-5 sections: N = 2 agents (2-3 sections each)
   - 6-8 sections: N = 3 agents (2-3 sections each)
   - 9+ sections: N = 4 agents (2-3 sections each)
4. **Maximum:** N = 4 frontend agents. Beyond this, coordination overhead exceeds parallelism benefit.

**Non-overlapping assignment rules:**

- Each file path appears in exactly one implementation group
- No two groups share any file path
- The orchestrator validates zero overlap before spawning agents
- If a section depends on a shared component (e.g., a custom card), that component belongs to `components/ui/` (read-only) or is inlined in the section file

### 6. Frontend Engineer (Layout Builder) -- Phase 3, Wave C

| Property              | Value                                                                                                |
| --------------------- | ---------------------------------------------------------------------------------------------------- |
| **Phase**             | 3 (Implementation, Wave C)                                                                           |
| **Assigned files**    | Exactly one of: `components/nav.tsx` OR `components/footer.tsx`                                      |
| **Read-only scope**   | `lib/*`, `components/ui/*`, `components/sections/*`, `app/globals.css`, `references/*`, `.context/*` |
| **Forbidden actions** | Modifying the other layout component, modifying any section files, modifying `app/layout.tsx`        |
| **Output format**     | React component file (`.tsx`) at the assigned file path                                              |

### 7. DevOps Engineer -- Phase 3, Wave B

| Property              | Value                                                                                                                              |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **Phase**             | 3 (Implementation, Wave B)                                                                                                         |
| **Assigned files**    | `app/sitemap.ts`, `app/robots.ts`, `next.config.js` (or `.mjs`/`.ts`), deployment config files (e.g., `vercel.json`, `Dockerfile`) |
| **Read-only scope**   | `app/layout.tsx` (for metadata context), `lib/*`, `.context/*`                                                                     |
| **Forbidden actions** | Modifying any files in `components/`, modifying `app/page-client.tsx`, modifying `app/globals.css`                                 |
| **Output format**     | TypeScript/config files at the assigned file paths                                                                                 |

**Special rule for `app/layout.tsx`:** The devops agent may add metadata exports (e.g., `export const metadata = {...}`) to `app/layout.tsx` ONLY if the orchestrator explicitly delegates this. Otherwise, `app/layout.tsx` is modified only by the orchestrator during integration.

### 8. QA Engineer -- Phase 4

| Property              | Value                                                                                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Phase**             | 4 (Quality)                                                                                                                                            |
| **Assigned files**    | All project files (via `/self-review-fix-loop` sub-agents)                                                                                             |
| **Read-only scope**   | Entire project (reviewers are read-only; fixers have write access)                                                                                     |
| **Forbidden actions** | Changing the architecture (adding/removing pages or sections), modifying design tokens in `app/globals.css`, changing font imports in `app/layout.tsx` |
| **Output format**     | Review findings (JSON) + fixed files                                                                                                                   |

### 9. Tech Lead -- Phase 4

| Property              | Value                                                                                                   |
| --------------------- | ------------------------------------------------------------------------------------------------------- |
| **Phase**             | 4 (Quality)                                                                                             |
| **Assigned files**    | None -- review only, no file creation or modification                                                   |
| **Read-only scope**   | Entire project, `.context/*` packets, git diff                                                          |
| **Forbidden actions** | Creating or modifying any files                                                                         |
| **Output format**     | Verdict: `APPROVE`, `REQUEST_CHANGES` (with specific file-level feedback), or `REJECT` (with reasoning) |

---

## Conflict Resolution

If a conflict is detected (two agents modified the same file):

1. **Identify the owner:** Check the implementation group assignments from the architecture packet.
2. **Keep the owner's version:** The agent assigned to the file keeps its changes.
3. **Discard the violator's changes:** The other agent's modifications to that file are discarded.
4. **Re-delegate if needed:** If the violator's intent was valid (e.g., a necessary cross-cutting change), the orchestrator delegates that change to the file's owner or performs it during integration.

---

## Summary Table

| Agent Role               | Phase | Writes To                            | Must Not Touch                                  |
| ------------------------ | ----- | ------------------------------------ | ----------------------------------------------- |
| FE (design extraction)   | 1     | (none)                               | Any project file                                |
| Product Owner            | 1     | (none)                               | Any project file                                |
| Explorer                 | 1     | (none)                               | Any project file                                |
| Architect                | 2     | (none)                               | Any project file                                |
| FE (section builder) x N | 3-A   | Assigned section `.tsx` files        | Other agents' sections, lib/, app/, nav, footer |
| FE (layout builder) x 2  | 3-C   | `nav.tsx` or `footer.tsx` (one each) | The other layout file, sections, app/           |
| DevOps Engineer          | 3-B   | sitemap, robots, config files        | components/, page files, globals.css            |
| QA Engineer              | 4     | Any file (via fix sub-agents)        | Architecture changes, design tokens, fonts      |
| Tech Lead                | 4     | (none)                               | Any project file                                |

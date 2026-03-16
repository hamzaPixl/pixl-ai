# Context Packet Schema

Defines the three packet types used for inter-phase communication in the `/website-project` pipeline. Each packet is a JSON file written to `.context/` in the project directory.

## Size Guidelines

- **Discovery packet:** Target under 5KB. Strip raw HTML, screenshots, and verbose logs before assembling.
- **Architecture packet:** Target under 8KB. Include only file paths, component names, and structural decisions.
- **Implementation packet:** Target under 3KB. This is a summary, not a full diff.

If a packet exceeds these targets, review for redundant or verbose content and slim it down. Downstream agents should not need to parse more than 10KB of context to begin work.

---

## 1. `discovery_packet`

Written to `.context/discovery-packet.json` after Phase 1 completes.

```yaml
discovery_packet:
  type: "discovery" # string — always "discovery"
  version: "1.0" # string — schema version
  metadata:
    skill: "website-project" # string — originating skill
    project: "" # string — project name or slug
    created_at: "" # string — ISO 8601 timestamp
    source_brief: "" # string — summary of user's original request (1-2 sentences)

  design:
    archetype: "" # string — e.g., "minimal", "bold", "luxury"
    colors:
      primary_hsl: "" # string — HSL values, e.g., "217 91% 60%"
      secondary_hsl: "" # string — HSL values
      accent_hsl: "" # string — HSL values
      surface_hsl: "" # string — HSL values
    typography:
      font_sans: "" # string — display name, e.g., "Inter"
      font_serif: "" # string — display name, e.g., "Playfair Display"
      font_sans_import: "" # string — next/font/google import name
      font_serif_import: "" # string — next/font/google import name
      font_serif_weight: "" # string — weight config, e.g., "400;700"
      heading_font: "" # string — "sans" or "serif"
    shape:
      border_radius: "" # string — CSS value, e.g., "8px"
    shadows:
      sm: "" # string — CSS box-shadow or "none"
      md: "" # string — CSS box-shadow
      lg: "" # string — CSS box-shadow
    motion:
      duration_micro: "" # string — e.g., "150ms"
      duration_page: "" # string — e.g., "400ms"
      ease: "" # string — cubic bezier array, e.g., "[0.4, 0, 0.2, 1]"
      distance: "" # string — pixel distance, e.g., "24"
      stagger: "" # string — seconds, e.g., "0.08"
    layout:
      nav_classes: "" # string — Tailwind classes for nav
      footer_classes: "" # string — Tailwind classes for footer
      section_padding: "" # string — Tailwind padding, e.g., "py-16 sm:py-24"
      max_width: "" # string — Tailwind suffix, e.g., "6xl"
    variants:
      hero: "" # string — variant name, e.g., "split"
      nav: "" # string — variant name, e.g., "transparent"
      footer: "" # string — variant name, e.g., "minimal"
      features: "" # string — variant name, e.g., "bento"
      testimonials: "" # string — variant name, e.g., "single-spotlight"
      cta: "" # string — variant name, e.g., "card"
      pricing: "" # string — variant name, e.g., "comparison-table"

  tasks:
    items: # array — ordered task list
      - id: "" # string — unique task ID, e.g., "T1"
        title: "" # string — short task description
        agent_role: "" # string — assigned specialist role
        dependencies: [] # array of string — task IDs this depends on
        parallel_group: "" # string — group name for parallel execution
        acceptance_criteria: [] # array of string — testable completion conditions
    parallel_groups: # array — groups of tasks that can run simultaneously
      - name: "" # string — group name
        task_ids: [] # array of string — task IDs in this group

  reference:
    sections: # array — sections found on reference site(s)
      - name: "" # string — section name, e.g., "Hero"
        order: 0 # number — position on page (0-indexed)
        content_pattern: "" # string — brief description of content structure
    nav_structure: "" # string — description of navigation pattern
    content_tone: "" # string — e.g., "professional", "playful", "authoritative"
    cta_placement: [] # array of string — where CTAs appear
    responsive_notes: "" # string — notable responsive behavior observed
```

### Example

```json
{
  "type": "discovery",
  "version": "1.0",
  "metadata": {
    "skill": "website-project",
    "project": "acme-landing",
    "created_at": "2026-02-26T10:00:00Z",
    "source_brief": "Build a SaaS landing page for Acme Analytics with pricing, testimonials, and a contact form."
  },
  "design": {
    "archetype": "corporate",
    "colors": {
      "primary_hsl": "217 91% 60%",
      "secondary_hsl": "187 70% 50%",
      "accent_hsl": "217 40% 96%",
      "surface_hsl": "217 10% 97%"
    },
    "typography": {
      "font_sans": "Inter",
      "font_serif": "Playfair Display",
      "font_sans_import": "Inter",
      "font_serif_import": "Playfair_Display",
      "font_serif_weight": "400;700",
      "heading_font": "serif"
    },
    "shape": { "border_radius": "8px" },
    "shadows": {
      "sm": "0 1px 2px rgba(0,0,0,0.04)",
      "md": "0 2px 8px rgba(0,0,0,0.06)",
      "lg": "0 4px 16px rgba(0,0,0,0.08)"
    },
    "motion": {
      "duration_micro": "200ms",
      "duration_page": "400ms",
      "ease": "[0.4, 0, 0.2, 1]",
      "distance": "24",
      "stagger": "0.08"
    },
    "layout": {
      "nav_classes": "bg-background/80 backdrop-blur-md border-b border-border",
      "footer_classes": "bg-muted text-foreground border-t border-border",
      "section_padding": "py-16 sm:py-24",
      "max_width": "7xl"
    },
    "variants": {
      "hero": "split",
      "nav": "bar",
      "footer": "4-column",
      "features": "card-grid",
      "testimonials": "carousel",
      "cta": "banner",
      "pricing": "tier-cards"
    }
  },
  "tasks": {
    "items": [
      {
        "id": "T1",
        "title": "Scaffold Next.js project with design tokens",
        "agent_role": "frontend-engineer",
        "dependencies": [],
        "parallel_group": "scaffold",
        "acceptance_criteria": [
          "npm run build succeeds",
          "design-config.ts has correct tokens"
        ]
      }
    ],
    "parallel_groups": [{ "name": "scaffold", "task_ids": ["T1"] }]
  },
  "reference": {
    "sections": [
      {
        "name": "Hero",
        "order": 0,
        "content_pattern": "Split layout with headline left, product screenshot right"
      },
      {
        "name": "Logos",
        "order": 1,
        "content_pattern": "Horizontal logo strip with 6 client logos"
      }
    ],
    "nav_structure": "Sticky top bar with logo left, links center, CTA button right",
    "content_tone": "professional",
    "cta_placement": ["hero", "after features", "footer"],
    "responsive_notes": "Hero collapses to stacked on mobile, nav becomes hamburger"
  }
}
```

---

## 2. `architecture_packet`

Written to `.context/architecture-packet.json` after Phase 2 completes. Extends the discovery packet.

```yaml
architecture_packet:
  type: "architecture" # string — always "architecture"
  version: "1.0" # string — schema version
  metadata:
    skill: "website-project" # string
    project: "" # string
    created_at: "" # string — ISO 8601

  component_tree: # array — all components with hierarchy
    - name: "" # string — component name, e.g., "HeroSection"
      file_path: "" # string — relative path, e.g., "components/sections/hero.tsx"
      props: [] # array of string — prop names and types
      children: [] # array of string — child component names
      parent: "" # string — parent component name or "page"

  page_structure: # array — pages with their section ordering
    - route: "" # string — e.g., "/" or "/pricing"
      file_path: "" # string — e.g., "app/page-client.tsx"
      sections: # array — ordered sections for this page
        - component: "" # string — component name
          file_path: "" # string — component file path
          order: 0 # number — render order (0-indexed)

  implementation_groups: # array — non-overlapping file groups for parallel agents
    - group_id: "" # string — e.g., "FE-1"
      files: [] # array of string — file paths owned by this group
      description: "" # string — what this group builds

  shared_components: # array — components built separately (nav, footer, layout)
    - name: "" # string — component name
      file_path: "" # string — file path
      wave: "" # string — which wave builds this ("C" for layout components)

  token_gaps: [] # array of string — any missing tokens flagged by architect
```

### Example

```json
{
  "type": "architecture",
  "version": "1.0",
  "metadata": {
    "skill": "website-project",
    "project": "acme-landing",
    "created_at": "2026-02-26T10:15:00Z"
  },
  "component_tree": [
    {
      "name": "HeroSection",
      "file_path": "components/sections/hero.tsx",
      "props": ["title: string", "subtitle: string", "ctaLabel: string"],
      "children": ["Button"],
      "parent": "page"
    }
  ],
  "page_structure": [
    {
      "route": "/",
      "file_path": "app/page-client.tsx",
      "sections": [
        {
          "component": "HeroSection",
          "file_path": "components/sections/hero.tsx",
          "order": 0
        },
        {
          "component": "FeaturesSection",
          "file_path": "components/sections/features.tsx",
          "order": 1
        }
      ]
    }
  ],
  "implementation_groups": [
    {
      "group_id": "FE-1",
      "files": [
        "components/sections/hero.tsx",
        "components/sections/features.tsx"
      ],
      "description": "Hero and features sections"
    },
    {
      "group_id": "FE-2",
      "files": ["components/sections/testimonials.tsx"],
      "description": "Testimonials section"
    },
    {
      "group_id": "FE-3",
      "files": [
        "components/sections/pricing.tsx",
        "components/sections/cta.tsx"
      ],
      "description": "Pricing and CTA sections"
    }
  ],
  "shared_components": [
    { "name": "Nav", "file_path": "components/nav.tsx", "wave": "C" },
    { "name": "Footer", "file_path": "components/footer.tsx", "wave": "C" }
  ],
  "token_gaps": []
}
```

---

## 3. `implementation_packet`

Written to `.context/implementation-packet.json` after Phase 3 completes.

```yaml
implementation_packet:
  type: "implementation" # string — always "implementation"
  version: "1.0" # string — schema version
  metadata:
    skill: "website-project" # string
    project: "" # string
    created_at: "" # string — ISO 8601

  files_created: # array — all files created during Phase 3
    - path: "" # string — relative file path
      purpose: "" # string — what this file does
      agent: "" # string — which agent created it (e.g., "FE-1")

  files_modified: # array — all files modified during Phase 3
    - path: "" # string — relative file path
      change_summary: "" # string — what was changed
      agent: "" # string — which agent modified it

  deviations: [] # array of string — any differences from architecture packet

  build_results:
    tsc_pass: false # boolean — did npx tsc --noEmit pass?
    build_pass: false # boolean — did npm run build pass?
    errors: [] # array of string — any error messages

  known_issues: [] # array of string — incomplete items or known problems
```

### Example

```json
{
  "type": "implementation",
  "version": "1.0",
  "metadata": {
    "skill": "website-project",
    "project": "acme-landing",
    "created_at": "2026-02-26T11:00:00Z"
  },
  "files_created": [
    {
      "path": "components/sections/hero.tsx",
      "purpose": "Split hero with headline and product image",
      "agent": "FE-1"
    },
    {
      "path": "components/sections/features.tsx",
      "purpose": "Card grid with 6 feature cards",
      "agent": "FE-1"
    },
    {
      "path": "components/nav.tsx",
      "purpose": "Sticky bar navigation",
      "agent": "LC-1"
    },
    {
      "path": "app/sitemap.ts",
      "purpose": "Dynamic sitemap generation",
      "agent": "DE-1"
    }
  ],
  "files_modified": [
    {
      "path": "app/page-client.tsx",
      "change_summary": "Imported and composed all section components",
      "agent": "orchestrator"
    },
    {
      "path": "app/layout.tsx",
      "change_summary": "Added nav, footer, and SEO metadata",
      "agent": "orchestrator"
    }
  ],
  "deviations": [],
  "build_results": {
    "tsc_pass": true,
    "build_pass": true,
    "errors": []
  },
  "known_issues": []
}
```

---
name: intro-video-brief
description: "Research a product from GitHub/URLs/user input and produce a video-brief.json for a product intro video. Also enhances existing Remotion video projects by auditing scenes and improving copy, timing, and animation. Use when creating or improving a marketing intro video, product demo video, or launch video. Output feeds directly into the /remotion skill."
allowed-tools: Read, Write, Bash, Glob, Grep, WebFetch, WebSearch
argument-hint: "<github-url|website-url|'description'|path/to/remotion-project> [--platform 16:9|9:16|1:1] [--duration 30s|60s] [--tone minimal|energetic|bold|corporate|playful] [--enhance]"
---

## Overview

Two modes:

- **Create mode** (default): Research product → interview user → generate `video-brief.json` → pass to `/remotion`
- **Enhance mode** (`--enhance` or when a Remotion project path is provided): Audit existing Remotion composition → identify issues → produce an improved `video-brief.json` + inline code suggestions

**Design principle**: Every video must feel like real motion design — varied scene types, distinct atmospheres per scene, kinetic typography, and intentional hard cuts alongside smooth transitions. Never let every scene use the same layout, same entry animation, or same background treatment.

---

## Mode Detection

Detect which mode to run:

1. **Enhance mode** if any of:
   - Argument contains `--enhance`
   - Argument is a directory path containing `remotion.config.ts`, `src/Root.tsx`, or `src/compositions/`
   - User says "improve", "enhance", "fix", "audit", or "update" the video

2. **Create mode** otherwise (GitHub URL, website URL, or free-form description)

---

## SCENE TYPE VOCABULARY

The full palette of scene types. Pick the right type for each moment — never use the same type twice in a row.

| Type | Duration | Purpose | Layout |
|---|---|---|---|
| `impact_word` | 1–2s | Single word/phrase lands on pure black. Shock, tension. | Full screen, centered, one element |
| `kinetic_text` | 2–4s | Words stagger in at different sizes/weights. Manifesto energy. | Freeform — words scattered or stacked with rhythm |
| `product_slam` | 2–3s | Product name slams in with spring overshoot, glow explodes then settles. | Full-bleed logotype |
| `comparison` | 4–6s | Before/After split — left side crossed out, right side lit up with brand color. Rows appear sequentially. | Two-column vertical list |
| `pipeline_flow` | 3–5s | Animated DAG or pipeline — nodes appear sequentially, connectors draw between them, particles flow along paths. | Horizontal or graph layout |
| `agent_formation` | 3–4s | Role/agent nodes orbit or grid-snap into position from off-screen. Each gets a label staggered in. | Radial or grid |
| `counter_moment` | 2–4s | One or two giant numbers count up from 0. Supporting label fades in underneath. | Asymmetric — number dominates |
| `case_study` | 4–6s | Real project outcome: company name, key stats, one-line result. Stat bars or counter animations. | Split: left=context, right=numbers |
| `typewriter_terminal` | 3–6s | Simulated terminal/code output types character by character. Shows process or reasoning. | Dark card, monospace font |
| `feature_reveal` | 2.5–3.5s | Feature name (large, bold) + 1-line benefit. Appears with directional entry, not just fade. | Off-center — title left, detail right or below |
| `split_scene` | 3–5s | Screen split diagonally or horizontally. Two concepts shown simultaneously. | Geometric split |
| `product_reveal` | 2–3s | Product name fully revealed after build-up. Tagline appears beneath. | Centered, dramatic |
| `social_proof` | 2–3s | Logos, numbers, or short quotes that establish credibility. | Grid or horizontal strip |
| `cta` | 2.5–3.5s | Final call to action. URL/button with pulse. Product name returns smaller. | Centered, accent background |

---

## ANIMATION VOCABULARY

### Entry Animations

| Animation | Description | Remotion implementation |
|---|---|---|
| `word_stagger` | Each word delays N frames (8–12f), appears with fade+slideY | Map words, each gets `frame - i*stagger` offset |
| `char_stagger` | Character-by-character reveal with stagger (2–4f per char) | Map chars, each gets `frame - i*charDelay` |
| `weight_morph` | Font weight interpolates thin→black during entry | `interpolate(frame, [0,20], [100, 900])` on fontWeight |
| `slam` | Fast spring overshoot (stiffness 300, damping 10) then settles. Hits hard. | `spring({ stiffness: 300, damping: 10 })` |
| `scanline` | Horizontal reveal bar sweeps top→bottom, text appears behind it | Clip-path animation from top |
| `orbit_in` | Elements start off a circular path and snap to final position via spring | Polar→cartesian coordinate interpolation |
| `count_up` | Number goes from 0 to target value, optionally with easing | `Math.floor(interpolate(frame, [0, dur], [0, target]))` |
| `hard_cut` | No entry animation — element is simply present at frame 0 of scene. Jarring, intentional. | No animation wrapper |
| `diagonal_wipe` | Content revealed behind diagonal clip-path that sweeps across | CSS clip-path polygon animation |
| `glitch_in` | Element appears with 2–3 frames of chromatic offset then stabilizes | Multi-layer offset interpolation |
| `typewriter` | Characters appear one by one at constant rate | `.substring(0, Math.floor(frame/2))` |
| `fade_up` | Standard fade + 24px translateY. Slow (20–30f). | Classic interpolate combo |
| `scale_in` | Scale from 0.8→1.0 with fade. Gentle. | `spring({ damping: 18 })` on scale |
| `slide_from_left` | Enters from left edge (translateX -200px → 0) | `interpolate` with easing |
| `particle_burst` | Accent-colored particles explode from element center on frame 0 | `noise2D` offsets per particle, radial spread |

### Exit Animations

| Animation | When to use |
|---|---|
| `hard_cut_out` | After `impact_word` or `counter_moment` — abrupt exit amplifies impact |
| `fade_out` | Standard, gentle — good after `feature_reveal` or `social_proof` |
| `scale_out` | Zoom out slightly while fading — closing, stepping back |
| `slide_out_left` | Swipe away — good before directional entry from right |
| `scanline_out` | Reverse scanline — mirrors scanline_in for consistency |
| `glitch_out` | Mirror of glitch_in — abrupt tech aesthetic |

### Transition Types Between Scenes

| Transition | Frames | Use when |
|---|---|---|
| `hard_cut` | 0f | After `impact_word`, between `counter_moment` and `case_study`. Creates rhythm. |
| `crossfade` | 20f | Default smooth transition |
| `zoom_cut` | 0f + scale change | Scale up 5% at end of scene A, start scene B at 95% scale. Energy spike. |
| `directional_wipe` | 15–20f | After `pipeline_flow` — direction matches data flow |
| `flash` | 3f | White/accent frame flash between scenes for impact. Use sparingly. |

---

## SCENE ATMOSPHERE DESIGN

Each scene must have its own distinct visual character. Never use the same background across all scenes.

| Scene type | Background treatment | Lighting |
|---|---|---|
| `impact_word` | Pure #000000 — no grid, no glow, nothing | No ambient — only the text |
| `kinetic_text` | Very dark bg, subtle texture or noise grain | Words create their own light via color |
| `product_slam` | Brand gradient emerges from black as logo lands | Radial glow pulse from logo center |
| `comparison` | Split bg: left = dark slate, right = near-black with accent tint | Accent line border between columns |
| `pipeline_flow` | Dark bg, subtle grid, glowing nodes and connectors | Node glow intensifies as particle passes |
| `agent_formation` | Deep dark, radial accent glow at formation center | Each node has its own micro-glow |
| `counter_moment` | Full black or brand color — number is the entire visual | Number glow in accent color |
| `case_study` | Near-black, one accent-colored stat bar or data element | Minimal — content is the hero |
| `typewriter_terminal` | Dark card / terminal bg, monospace font, cursor blink | Subtle green or accent text glow |
| `feature_reveal` | Scene-specific hue shift — each feature gets a slight bg variation | Off-axis light source (not center) |
| `product_reveal` | bg shifts from dark→brand color area as tagline appears | Full radial bloom |
| `cta` | Accent background or deep dark with accent button | Button pulse + ambient glow |

---

## CREATE MODE

### Step 1: Gather Inputs

1. **Parse the argument** to identify:
   - Directory path → read content files directly (README, content.ts, globals.css, package.json)
   - GitHub URL (`github.com/org/repo`) → fetch README + repo metadata
   - Website URL → fetch homepage content
   - Free-form description → use as product context directly

2. **Ask missing essentials** (only ask what cannot be inferred):
   ```
   Quick questions to shape your intro video:

   1. Target platform? [16:9 YouTube/Web | 9:16 TikTok/Reels | 1:1 Instagram]
   2. Video duration? [15s | 30s | 60s]
   3. Visual tone? [minimal | energetic | bold | corporate | playful]
   4. Primary brand color? (hex or "I don't know — pick from the product")
   5. Should I include a voiceover script? [yes | no]
   ```
   Skip any question the user already answered via arguments or description.

### Step 2: Research the Product

#### 2a: Local project directory

If a local path is provided, read:
- `README.md` → product name, tagline, key features
- `lib/content.ts` or equivalent content files → hero copy, features, comparison data, stats, use cases
- `globals.css` or `tailwind.config.*` → brand colors, fonts, design tokens
- `package.json` → tech stack

Extract specifically:
```
PRODUCT NAME: ...
TAGLINE: ... (hero headline, ≤ 8 words)
HOOK TENSION: ... (the "without" side of comparison, or the pain point)
KEY FEATURES: (3-5, benefit-led)
REAL STATS: (actual numbers from proof/traction sections)
REAL CASE STUDIES: (actual project outcomes with names, numbers, timelines)
COMPARISON ROWS: (before/after pairs if present)
CTA TEXT: ...
CTA URL: ...
BRAND COLORS: (from CSS vars)
FONTS: ...
```

#### 2b: GitHub Repository

Fetch and extract:
- `README.md` → product name, tagline, key features
- Repo description, stars, topics/tags
- `package.json` or `pyproject.toml` → tech stack, version

#### 2c: Website URL

Fetch homepage and extract:
- Hero headline + subheadline
- Feature section highlights (3-6 items)
- Primary CTA text
- Brand colors (CSS vars, meta theme-color)
- Fonts

#### 2d: WebSearch fallback

If URLs unavailable: search `"[product name]" site:github.com OR "[product name]" features`

### Step 3: Brand Extraction

**Colors:**
1. From local CSS → extract `--color-*` or `--primary`, `--accent`, `--background`
2. From website CSS → computed primary
3. Fallback by tone:
   - `minimal` → white bg, near-black text, slate accent
   - `energetic` → dark bg, purple→blue gradient, bright accent
   - `bold` → black/white, one strong accent (red or orange)
   - `corporate` → navy/blue, white, grey
   - `playful` → bright multicolor, rounded, pastel

**Fonts by tone:**
| Tone       | Heading             | Body          |
|------------|---------------------|---------------|
| minimal    | Inter               | Inter         |
| energetic  | Space Grotesk / Sora| Inter         |
| bold       | Clash Display       | DM Sans       |
| corporate  | IBM Plex Sans       | IBM Plex Sans |
| playful    | Nunito / Fredoka    | Nunito        |

### Step 4: Scene Planning

**Duration presets (at 30fps):**
| Duration | Total frames | Scene count |
|----------|-------------|-------------|
| 15s      | 450f        | 5–6 scenes  |
| 30s      | 900f        | 7–10 scenes |
| 60s      | 1800f       | 12–16 scenes|

**Critical rules for scene selection:**
- Never use the same scene type twice in a row
- Never use the same entry animation twice in a row
- Alternate between high-energy (impact_word, counter_moment, slam) and calmer scenes (feature_reveal, pipeline_flow)
- Use at least 2 `hard_cut` transitions in a 30s video — they create rhythm
- Every scene must have a distinct atmosphere (see Scene Atmosphere Design above)
- Use real data (actual stats, real case study names) — never invent numbers

**Scene sequence templates by tone:**

For `energetic` / `bold` (recommended for tech/AI products):
```
1. impact_word         → "hard_cut" →
2. comparison          → "crossfade" →
3. product_slam        → "zoom_cut" →
4. pipeline_flow       → "hard_cut" →
5. agent_formation     → "crossfade" →
6. counter_moment      → "hard_cut" →
7. case_study          → "crossfade" →
8. feature_reveal      → "crossfade" →
9. cta
```

For `minimal` (SaaS, B2B, design tools):
```
1. kinetic_text        → "crossfade" →
2. product_reveal      → "crossfade" →
3. feature_reveal ×3   → "crossfade" each →
4. social_proof        → "crossfade" →
5. cta
```

For `corporate`:
```
1. kinetic_text        → "crossfade" →
2. product_reveal      → "crossfade" →
3. comparison          → "slide →
4. pipeline_flow       → "crossfade" →
5. counter_moment      → "crossfade" →
6. cta
```

**Copy rules:**
- `impact_word` headlines: ≤ 5 words, opens tension. Example: `"Chaos."` or `"AI code. No guardrails."`
- `kinetic_text` lines: each word/phrase ≤ 3 words, staggered timing. Reads like a manifesto.
- `comparison` rows: left = pain point (≤ 6 words), right = solution (≤ 6 words). Use real product comparison data if available.
- `counter_moment`: one or two numbers max. Use real stats — never invent.
- `case_study`: real project name, real numbers, one-line outcome. ≤ 15 words total.
- `feature_reveal` title: benefit-led ≤ 4 words. Sub: ≤ 10 words.
- `cta`: ≤ 4 words, specific action.

### Step 5: Voiceover Script (if enabled)

Pace: ~2.5 words/second. Keep under:
- 15s → ~35 words | 30s → ~75 words | 60s → ~150 words

Template:
```
[Hook tension] — "Right now, AI code ships with no guardrails."
[Reveal] — "Introducing [Product] — [tagline]"
[Key benefit 1-2] — "[Benefit statement]"
[Real proof] — "[Real stat from actual data]"
[CTA] — "Join the waitlist at [URL]"
```

---

## ENHANCE MODE

### Step E1: Discover the Remotion Project

Scan the project directory:
```
remotion.config.ts        → fps, output resolution, entry point
src/Root.tsx              → registered compositions (IDs, durations, fps)
src/compositions/         → individual scene components
src/components/           → reusable elements
public/                   → assets (fonts, images, audio)
video-brief.json          → existing brief (if present)
```

Also look for associated content files adjacent to the Remotion project:
```
../lib/content.ts         → product copy, features, stats, comparison data
../README.md              → product description
../app/globals.css        → brand tokens
```

Read each composition file and map:
- Component name → scene type (map to vocabulary above)
- `durationInFrames` → actual scene timing
- `fps` → frame rate
- Props and hardcoded content (copy, colors, fonts)
- Animation patterns used (`spring`, `interpolate`, `useCurrentFrame`)
- Background: is it the same across all scenes? (structural red flag)

### Step E2: Audit the Video

Evaluate against these criteria and flag issues:

#### Structure & Dynamism (new)
- [ ] **STRUCT-01**: At least 3 distinct scene types used (not all the same layout)
- [ ] **STRUCT-02**: At least 1 hard cut transition (pure 0f cut) — no all-crossfade video
- [ ] **STRUCT-03**: Each scene has a distinct background/atmosphere (not 1 shared bg)
- [ ] **STRUCT-04**: Real product data used (actual stats, real use cases) — not placeholder copy
- [ ] **STRUCT-05**: High-energy and calmer scenes alternate — not all same intensity

#### Copy Quality
- [ ] **COPY-01**: Hook headline ≤ 6 words and opens a tension/question
- [ ] **COPY-02**: Product name is the largest element in reveal scene
- [ ] **COPY-03**: Feature titles are benefit-led (not feature-led)
- [ ] **COPY-04**: CTA is specific and actionable (not just "Learn more")
- [ ] **COPY-05**: No scene has more than 12 words of body text
- [ ] **COPY-06**: Real stats used where available — no invented numbers

#### Timing
- [ ] **TIME-01**: Hook is ≤ 3s (90f at 30fps) — longer loses attention
- [ ] **TIME-02**: CTA is ≥ 2s (60f) — needs time to register
- [ ] **TIME-03**: Feature scenes are 2.5–4s each
- [ ] **TIME-04**: Total duration matches target (15/30/60s)
- [ ] **TIME-05**: Hard cuts used ≥ 1× for rhythm (0f transitions)

#### Animation
- [ ] **ANIM-01**: Text animates in — no static text appearing without motion
- [ ] **ANIM-02**: Consistent easing family across scenes (spring or ease — not both randomly)
- [ ] **ANIM-03**: No same entry animation used 3× in a row
- [ ] **ANIM-04**: Spring animations don't overshoot text bounds
- [ ] **ANIM-05**: Exit animations exist (not just entry)
- [ ] **ANIM-06**: At least 1 kinetic/dynamic entry (word_stagger, slam, scanline, count_up) — not all fade_up

#### Brand Consistency
- [ ] **BRAND-01**: Same primary color used across all scenes
- [ ] **BRAND-02**: ≤ 2 font families in the video
- [ ] **BRAND-03**: Spacing/padding is consistent between scenes
- [ ] **BRAND-04**: Each scene has distinct atmosphere while staying on-brand

#### Technical (Remotion-specific)
- [ ] **TECH-01**: No hardcoded `Math.random()` in components (breaks frame consistency)
- [ ] **TECH-02**: All assets imported via `staticFile()` not raw paths
- [ ] **TECH-03**: `Img` component used instead of `<img>` tag
- [ ] **TECH-04**: Audio uses `<Audio>` not raw `<audio>` HTML
- [ ] **TECH-05**: No `useEffect` with side effects — use `useCurrentFrame` instead

### Step E3: Produce Enhancement Plan

Output a prioritized list of improvements:

```
## Video Enhancement Report: [Composition ID]

### Critical (fix before publishing)
- STRUCT-01 ❌ Only 1 scene type used — all scenes are centered fade-in stacks
- STRUCT-03 ❌ Same background across all 4 scenes — no visual variety
- COPY-01 ❌ Hook is 12 words — reduce to: "Chaos." or "AI code. No guardrails."
- ANIM-06 ❌ All entries are fade_up — add at least 1 slam, scanline, or word_stagger

### Recommended (improves quality)
- STRUCT-02 ⚠️ No hard cuts — add 1-2 between counter_moment and case_study
- COPY-03 ⚠️ "Workflow Orchestration" → rewrite as "Prompt to prod. Governed."
- COPY-06 ⚠️ Stats scene uses generic copy — replace with real data (35+ businesses, 10× faster)
- ANIM-02 ⚠️ Mixing spring(damping:14) and spring(damping:200) — pick one damping range

### Optional (nice to have)
- ANIM-05 ℹ️ No exit animations — add fade_out or hard_cut_out before transitions
- STRUCT-05 ℹ️ All scenes same energy — alternate with an impact_word scene

PASSED: X/24 checks
CRITICAL ISSUES: N
```

### Step E4: Generate Enhanced video-brief.json

Write an updated `video-brief.json` incorporating all fixes:
- Replace generic scene types with specific types from the vocabulary
- Update copy with improved headlines using real product data
- Correct timing (duration_frames)
- Differentiate each scene's atmosphere
- Add at least 1 hard_cut transition
- Add `enhancement_notes` field documenting what changed

Also output **inline code snippets** for critical Remotion fixes:

```tsx
// ANIM-06 fix: Replace fade_up with word_stagger for hook scene
// Before:
<div style={{ opacity: fadeIn(frame, 0, 20), transform: `translateY(${slideY(frame, 0, 20)}px)` }}>
  AI agents without guardrails
</div>

// After (word_stagger — kinetic, energetic):
const words = ["Chaos."].flatMap(w => w.split(" "));
{words.map((word, i) => {
  const delay = i * 10;
  const prog = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 18, stiffness: 200 } });
  return (
    <span key={i} style={{
      opacity: prog,
      transform: `translateY(${interpolate(prog, [0,1], [32, 0])}px)`,
      display: "inline-block",
      marginRight: 16,
      fontSize: i === 0 ? 180 : 80,  // size variation for rhythm
    }}>{word}</span>
  );
})}
```

```tsx
// STRUCT-03 fix: Replace shared background with scene-specific atmospheres
// The Background component should accept a sceneType prop:
const Background: React.FC<{ sceneType: string; frame: number }> = ({ sceneType, frame }) => {
  if (sceneType === "impact_word") {
    return <AbsoluteFill style={{ background: "#000000" }} />;
  }
  if (sceneType === "pipeline_flow") {
    return (
      <AbsoluteFill>
        <AbsoluteFill style={{ background: BG }} />
        <AbsoluteFill style={{ backgroundImage: GRID_CSS, opacity: 0.4 }} />
        {/* flowing particles via noise2D */}
      </AbsoluteFill>
    );
  }
  // etc.
};
```

```tsx
// TECH-01 fix: Replace Math.random() with deterministic noise
import { noise2D } from '@remotion/noise';
const x = noise2D('particle-x', frame / 30, index) * 100;
```

---

## OUTPUT: video-brief.json

Write `./video-brief.json` (create or overwrite):

```json
{
  "$schema": "https://raw.githubusercontent.com/pixl-crew/schemas/main/video-brief.schema.json",
  "meta": {
    "generated_by": "intro-video-brief",
    "mode": "create|enhance",
    "version": "2.0"
  },
  "product": {
    "name": "...",
    "tagline": "...",
    "description": "...",
    "target_audience": "...",
    "key_features": [
      { "title": "...", "description": "..." }
    ],
    "comparison_rows": [
      { "without": "...", "with": "..." }
    ],
    "real_stats": [
      { "value": "...", "label": "...", "source": "..." }
    ],
    "case_studies": [
      { "name": "...", "outcome": "...", "key_stat": "...", "timeline": "..." }
    ],
    "cta_text": "...",
    "cta_url": "...",
    "github_url": "...",
    "website_url": "..."
  },
  "brand": {
    "colors": {
      "primary": "#HEX",
      "secondary": "#HEX",
      "accent": "#HEX",
      "background": "#HEX",
      "text": "#HEX",
      "text_muted": "#HEX"
    },
    "fonts": {
      "heading": "Google Font name",
      "body": "Google Font name"
    },
    "tone": "minimal|energetic|bold|corporate|playful"
  },
  "video": {
    "fps": 30,
    "width": 1920,
    "height": 1080,
    "total_frames": 900,
    "duration_seconds": 30,
    "aspect_ratio": "16:9"
  },
  "scenes": [
    {
      "id": "hook",
      "label": "Hook",
      "type": "impact_word|kinetic_text|comparison|product_slam|pipeline_flow|agent_formation|counter_moment|case_study|typewriter_terminal|feature_reveal|split_scene|product_reveal|social_proof|cta",
      "start_frame": 0,
      "duration_frames": 45,
      "transition_to_next": {
        "type": "hard_cut|crossfade|zoom_cut|directional_wipe|flash",
        "duration_frames": 0
      },
      "atmosphere": {
        "background": "pure_black|brand_gradient|dark_grid|split_dark|terminal_dark|scene_specific",
        "lighting": "none|center_glow|off_axis|accent_bloom|node_glow",
        "grain": false
      },
      "content": {
        "headline": "...",
        "words": ["word1", "word2"],
        "subheadline": null,
        "body": null,
        "cta": null,
        "comparison_rows": null,
        "stats": null,
        "terminal_lines": null
      },
      "animation": {
        "entry": "word_stagger|char_stagger|weight_morph|slam|scanline|orbit_in|count_up|hard_cut|diagonal_wipe|glitch_in|typewriter|fade_up|scale_in|slide_from_left|particle_burst",
        "entry_config": {
          "stagger_frames": 10,
          "spring_stiffness": 200,
          "spring_damping": 18
        },
        "exit": "hard_cut_out|fade_out|scale_out|slide_out_left|scanline_out|glitch_out",
        "easing": "spring|ease_in_out|linear"
      },
      "voiceover_line": "..."
    }
  ],
  "music": {
    "mood": "inspiring|energetic|calm|corporate|playful",
    "bpm": "slow|medium|fast",
    "note": "Recommended style suggestion"
  },
  "voiceover": {
    "enabled": false,
    "full_script": "...",
    "word_count": 0
  },
  "enhancement_notes": [],
  "remotion_hints": {
    "composition_id": "ProductIntro",
    "scene_components": {
      "impact_word": "Single element, no background elements, full black. Hard cut in and out.",
      "kinetic_text": "Words as individual spans with staggered spring. Size variation (large/small) creates rhythm.",
      "product_slam": "spring({ stiffness: 300, damping: 10 }) on scale. Glow pulse on settle.",
      "comparison": "Two-column layout. Left col: strikethrough animation (width 0→100%). Right col: accent color highlight.",
      "pipeline_flow": "Nodes appear with spring. SVG path connectors draw via stroke-dashoffset. Particles via noise2D.",
      "agent_formation": "Start positions off-screen or on circle. Spring each to final grid/radial position.",
      "counter_moment": "Math.floor(interpolate(frame, [0, dur], [0, target])) on the display number.",
      "case_study": "Left: company/project name. Right: key stat counts up. Timeline appears last.",
      "typewriter_terminal": "string.substring(0, Math.floor(frame/charsPerFrame)). Cursor blink via frame % 30 < 15.",
      "feature_reveal": "Title slides in from left (translateX). Detail fades in from right with slight delay.",
      "cta": "Button has pulsing box-shadow via sin(frame * 0.1). Domain appears with fade_up."
    },
    "key_imports": [
      "@remotion/google-fonts",
      "@remotion/noise (noise2D for deterministic particles)",
      "spring, interpolate, useCurrentFrame, AbsoluteFill, Sequence, Img, Audio, staticFile"
    ],
    "anti_patterns": [
      "Never Math.random() — use noise2D with a seed string",
      "Never same entry animation 3× in a row",
      "Never same background across all scenes",
      "Never useEffect for animation — use useCurrentFrame",
      "Never <img> — use <Img> from remotion"
    ]
  }
}
```

---

## Summary Output

After writing the file, print:

```
## [Mode: Create|Enhance] — [Product Name]

**Tone**: [tone] | **Platform**: [aspect ratio] | **Duration**: [Ns / Nf @ 30fps]

### Scene breakdown
| # | Type              | Duration | Entry        | Transition | Copy                           |
|---|-------------------|----------|--------------|------------|--------------------------------|
| 1 | impact_word       | 1.5s     | hard_cut     | hard_cut   | "Chaos."                       |
| 2 | comparison        | 5s       | word_stagger | crossfade  | "Babysitting AI vs. pipelines" |
| 3 | product_slam      | 2.5s     | slam         | zoom_cut   | "SYNQ"                         |
...

### Brand
- Colors: primary=[hex] accent=[hex] bg=[hex]
- Fonts: [heading] + [body]
- Tone: [tone]

### Motion design check
- Scene type variety: [N distinct types] ✓/✗
- Hard cuts used: [N] ✓/✗
- Real data used: ✓/✗
- Animation variety: ✓/✗

**Output**: `./video-brief.json` ✓

---
Next step: Run `/remotion` — reference `video-brief.json` for the composition spec.
Each scene type maps to a dedicated component. See `remotion_hints.scene_components`.
```

---

## Tips

- **Vary scene types aggressively** — same layout twice in a row = classic, boring. Switch type every scene.
- **Hard cuts are features** — 1–2 zero-frame cuts in a 30s video create rhythm and energy.
- **Use real data** — invented stats feel flat. `"35+ businesses"` hits harder than `"growing customer base"`.
- **Impact words need nothing else** — pure black, one word, 1.5s. Restraint is power.
- **Kinetic text reads like a manifesto** — pick words from the product's actual comparison/pain-point data.
- **Counter scenes need exit speed** — use `hard_cut_out` after the number lands. Don't linger.
- **Each scene is a distinct graphic** — different bg, different layout anchor, different entry direction.
- **Remotion determinism**: Never `Math.random()` — use `@remotion/noise` with a seed string.
- **Timing**: multiples of 30f for clean cuts (30f=1s, 45f=1.5s, 60f=2s, 75f=2.5s, 90f=3s).
- **Font loading**: `/remotion` handles Google Fonts via `@remotion/google-fonts` — just provide font name.
- **Color contrast**: Text-on-bg must meet WCAG AA (4.5:1). Adjust lightness if needed.

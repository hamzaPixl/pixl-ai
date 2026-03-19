# Video Vocabulary Reference

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

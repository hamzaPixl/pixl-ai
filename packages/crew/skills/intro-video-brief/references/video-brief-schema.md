# video-brief.json Schema

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

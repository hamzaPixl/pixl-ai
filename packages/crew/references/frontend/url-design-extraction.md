# URL-Based Design Extraction

Reference for extracting design tokens, layout structure, and component-level detail from a live website URL using agent-browser. Outputs a `design-spec.json` conforming to `references/frontend/design-spec-schema.md`.

> **RULES**
>
> 1. **One screenshot per state** — never retake the same screenshot.
> 2. **Read and analyze each screenshot before taking the next** — use the Read tool on the screenshot file immediately after capture.
> 3. **Navigate to at least 3 pages beyond the homepage** (or all nav links if fewer than 3).
> 4. **Extract component-level styles** — not just section types.
> 5. **Output design-spec.json** — not a markdown brief. Follow the schema in `references/frontend/design-spec-schema.md`.

## When to Use

Any design skill (`/website-theme`, `/website-layout`, `/design-extraction`, `/website`) receives a **live website URL** (not a Figma URL) as reference input. The URL becomes a visual source of truth to inform or drive the design.

## Extraction Pipeline

### Phase 1: Homepage Capture & Multi-Viewport Screenshots

Open the URL and capture at 3 viewports.

```
1. agent-browser open <url>
2. agent-browser set viewport 1440 900
3. agent-browser screenshot --full ./output/screenshots/home-desktop.png
4. Read the screenshot — identify sections, layout, nav links, overall mood
5. agent-browser set viewport 768 1024
6. agent-browser screenshot --full ./output/screenshots/home-tablet.png
7. agent-browser set viewport 375 812
8. agent-browser screenshot --full ./output/screenshots/home-mobile.png
9. agent-browser set viewport 1440 900
```

Extract nav links from the page (these become multi-page navigation targets in Phase 2):

```bash
agent-browser eval "(() => {
  const links = [...document.querySelectorAll('nav a, header a')];
  return JSON.stringify(links.map(a => ({
    text: a.textContent.trim(),
    href: a.href
  })).filter(l => l.text.length > 0 && l.text.length < 40 && l.href.startsWith('http')).slice(0, 10));
})()"
```

Then run CSS token extraction and layout structure extraction (see below) on the homepage before navigating away.

#### CSS Token Extraction

Use `agent-browser eval` to extract computed styles from the live DOM:

```bash
agent-browser eval "(() => {
  const root = getComputedStyle(document.documentElement);
  const styles = {};

  // CSS custom properties (shadcn, Tailwind, Framer)
  const colorProps = ['--primary', '--secondary', '--accent', '--background', '--foreground',
    '--muted', '--muted-foreground', '--border', '--ring', '--card', '--card-foreground',
    '--popover', '--popover-foreground', '--destructive'];
  colorProps.forEach(p => { styles[p] = root.getPropertyValue(p).trim(); });

  // Fallback: compute from elements if no CSS vars
  const body = getComputedStyle(document.body);
  styles.bodyBg = body.backgroundColor;
  styles.bodyColor = body.color;
  styles.bodyFont = body.fontFamily;

  // Typography
  const h1 = document.querySelector('h1');
  if (h1) {
    const cs = getComputedStyle(h1);
    styles.headingFont = cs.fontFamily;
    styles.h1Size = cs.fontSize;
    styles.h1Weight = cs.fontWeight;
    styles.h1LineHeight = cs.lineHeight;
    styles.h1LetterSpacing = cs.letterSpacing;
    styles.h1Color = cs.color;
  }
  const h2 = document.querySelector('h2');
  if (h2) {
    const cs = getComputedStyle(h2);
    styles.h2Size = cs.fontSize;
    styles.h2Weight = cs.fontWeight;
    styles.h2LineHeight = cs.lineHeight;
    styles.h2LetterSpacing = cs.letterSpacing;
  }
  const h3 = document.querySelector('h3');
  if (h3) {
    const cs = getComputedStyle(h3);
    styles.h3Size = cs.fontSize;
    styles.h3Weight = cs.fontWeight;
    styles.h3LineHeight = cs.lineHeight;
  }

  // Shape
  styles.radius = root.getPropertyValue('--radius').trim();

  // Shadows
  const card = document.querySelector('[class*=\"card\"], [class*=\"Card\"], article');
  if (card) styles.cardShadow = getComputedStyle(card).boxShadow;

  // Spacing
  const sections = document.querySelectorAll('section, [class*=\"section\"]');
  if (sections.length > 0) {
    const s = getComputedStyle(sections[0]);
    styles.sectionPaddingTop = s.paddingTop;
    styles.sectionPaddingBottom = s.paddingBottom;
  }

  // Max-width
  const container = document.querySelector('[class*=\"container\"], [class*=\"max-w\"]');
  if (container) styles.maxWidth = getComputedStyle(container).maxWidth;

  // Dark/light mode detection
  const bg = body.backgroundColor;
  const match = bg.match(/rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/);
  if (match) {
    const lum = (0.299 * +match[1] + 0.587 * +match[2] + 0.114 * +match[3]) / 255;
    styles.mode = lum < 0.5 ? 'dark' : 'light';
  }

  return JSON.stringify(styles, null, 2);
})()"
```

#### Font Inventory

```bash
agent-browser eval "(() => {
  const fonts = new Set();
  const links = document.querySelectorAll('link[href*=\"fonts.googleapis.com\"], link[href*=\"fonts.gstatic.com\"]');
  links.forEach(l => fonts.add(l.href));
  const styles = document.querySelectorAll('style');
  styles.forEach(s => {
    const matches = s.textContent.match(/@font-face\\s*\\{[^}]*font-family:\\s*['\"]?([^'\";}]+)/g);
    if (matches) matches.forEach(m => {
      const name = m.match(/font-family:\\s*['\"]?([^'\";}]+)/);
      if (name) fonts.add(name[1].trim());
    });
  });
  // Computed fonts from key elements
  const elements = { body: document.body, h1: document.querySelector('h1'), nav: document.querySelector('nav') };
  const computed = {};
  Object.entries(elements).forEach(([k, el]) => {
    if (el) computed[k] = getComputedStyle(el).fontFamily;
  });
  return JSON.stringify({ googleFontsUrls: [...fonts], computedFonts: computed }, null, 2);
})()"
```

#### Layout Structure Extraction

Use `agent-browser eval` to map the page structure. Uses **content-based detection** (not class names) so it works with Framer, Webflow, and other builders that obfuscate classes:

```bash
agent-browser eval "(() => {
  const sections = [];

  // Find top-level layout blocks: semantic elements first, then direct children of main/body
  let allSections = document.querySelectorAll('section, [role=\"region\"], [role=\"banner\"], [role=\"contentinfo\"]');
  if (allSections.length < 3) {
    const main = document.querySelector('main') || document.body;
    allSections = main.querySelectorAll(':scope > div, :scope > section, :scope > header, :scope > footer');
  }

  allSections.forEach((el, i) => {
    const rect = el.getBoundingClientRect();
    if (rect.height < 40) return;
    const cs = getComputedStyle(el);
    const classes = (el.className || '').toString();
    const id = (el.id || '').toLowerCase();
    const tag = el.tagName.toLowerCase();
    const innerText = el.textContent || '';
    const innerHtml = el.innerHTML || '';

    // --- Content-based section type detection ---
    let type = 'unknown';
    const classId = (classes + ' ' + id).toLowerCase();

    if (classId.match(/hero|banner/)) type = 'hero';
    else if (classId.match(/feature/)) type = 'features';
    else if (classId.match(/testimonial|review/)) type = 'testimonials';
    else if (classId.match(/pricing|plan/)) type = 'pricing';
    else if (classId.match(/faq/)) type = 'faq';
    else if (classId.match(/cta|call-to-action/)) type = 'cta';
    else if (classId.match(/footer/)) type = 'footer';
    else if (classId.match(/nav|header/)) type = 'nav';
    else if (classId.match(/logo|partner|client|trusted/)) type = 'logos';
    else if (classId.match(/stat|metric|number/)) type = 'stats';
    else if (classId.match(/team|people/)) type = 'team';
    else if (classId.match(/blog|article/)) type = 'blog';
    else if (classId.match(/contact|form/)) type = 'contact';
    else if (classId.match(/marquee|ticker/)) type = 'marquee';
    else if (classId.match(/project|work|portfolio|case/)) type = 'projects';

    if (type === 'unknown') {
      const h1 = el.querySelector('h1');
      const hasAccordion = el.querySelector('details, [class*=\"accordion\"], [class*=\"Accordion\"]')
        || (el.querySelectorAll('[role=\"button\"]').length >= 3 && innerText.toLowerCase().includes('?'));
      const hasPriceSymbol = innerText.match(/\\$\\d|\\u20ac\\d|\\d+\\/mo|per month|per year/i);
      const hasForm = el.querySelector('form, input[type=\"email\"], textarea');
      const imgCount = el.querySelectorAll('img').length;
      const hasSmallImgs = [...el.querySelectorAll('img')].filter(img => img.height < 60 && img.height > 16).length;
      const hasMarquee = el.querySelector('[class*=\"marquee\"], [class*=\"ticker\"]')
        || (cs.overflow === 'hidden' && el.querySelector('[style*=\"animation\"], [style*=\"transform\"]'));

      if (tag === 'nav' || tag === 'header') type = 'nav';
      else if (tag === 'footer') type = 'footer';
      else if (h1 && i <= 2) type = 'hero';
      else if (hasMarquee) type = 'marquee';
      else if (hasAccordion) type = 'faq';
      else if (hasPriceSymbol) type = 'pricing';
      else if (hasForm) type = 'contact';
      else if (hasSmallImgs >= 4 && rect.height < 200) type = 'logos';
      else if (imgCount >= 3 && el.querySelectorAll('h3, h4').length >= 3) type = 'blog';
      else if (el.querySelectorAll('blockquote, [class*=\"avatar\"]').length >= 2) type = 'testimonials';
      else if (el.querySelectorAll('h3, h4').length >= 3) type = 'features';
      else if (rect.height < 300 && el.querySelectorAll('a, button').length >= 1
        && el.querySelectorAll('h2').length === 1) type = 'cta';
      else if (innerText.match(/how it works|step \\d|step\\d/i)) type = 'steps';
    }

    // --- Component shape detection ---
    const gridCols = cs.gridTemplateColumns;
    const flexDir = cs.flexDirection;
    let shape = 'unknown';
    if (gridCols && gridCols !== 'none') {
      const colCount = gridCols.split(/\\s+/).filter(c => c !== '').length;
      if (colCount >= 3) shape = 'card-grid-' + colCount + 'col';
      else if (colCount === 2) shape = 'split-2col';
    } else if (flexDir === 'row' || cs.display === 'flex') {
      const kids = el.querySelectorAll(':scope > div, :scope > article');
      if (kids.length >= 3) shape = 'flex-row-' + kids.length;
      else if (kids.length === 2) shape = 'split-2col';
    }
    const nestedGrids = el.querySelectorAll('[style*=\"grid\"], [class*=\"grid\"]');
    if (nestedGrids.length > 0 && shape === 'unknown') {
      shape = 'nested-grid';
    }

    // --- Decorative elements ---
    const decorative = [];
    if (el.querySelector('svg:not([class*=\"icon\"])')) decorative.push('svg-decoration');
    if (cs.backgroundImage && cs.backgroundImage !== 'none') decorative.push('bg-image');
    if (innerHtml.match(/gradient|linear-gradient|radial-gradient/i)) decorative.push('gradient');
    if (el.querySelector('[class*=\"blob\"], [class*=\"orb\"], [class*=\"glow\"]')) decorative.push('blob/orb');

    sections.push({
      index: i,
      type,
      tag,
      height: Math.round(rect.height),
      shape,
      bgColor: cs.backgroundColor,
      padding: cs.paddingTop + ' / ' + cs.paddingBottom,
      display: cs.display,
      gridCols: gridCols || null,
      decorative: decorative.length ? decorative : null,
      headings: [...el.querySelectorAll('h1,h2,h3')].slice(0, 3).map(h => h.tagName + ': ' + h.textContent.trim().substring(0, 80)),
      cardCount: el.querySelectorAll('[class*=\"card\"], [class*=\"Card\"], article').length || null
    });
  });

  const nav = document.querySelector('nav, header, [role=\"banner\"]');
  const navStyle = nav ? {
    position: getComputedStyle(nav).position,
    bg: getComputedStyle(nav).backgroundColor,
    backdrop: getComputedStyle(nav).backdropFilter,
    borderBottom: getComputedStyle(nav).borderBottom,
    height: Math.round(nav.getBoundingClientRect().height),
    links: [...nav.querySelectorAll('a')].map(a => a.textContent.trim()).filter(t => t.length < 30).slice(0, 10),
    hasCta: !!nav.querySelector('button, a[class*=\"btn\"], a[class*=\"Button\"], a[class*=\"cta\"]')
  } : null;

  return JSON.stringify({ sections, navStyle }, null, 2);
})()"
```

**Visual fallback:** If >50% of sections come back as `type: "unknown"`, the DOM heuristics have failed (common with Framer, Webflow, Wix). In that case, **skip the eval output** and instead:

1. Scroll through the full page taking screenshots every ~800px viewport height
2. Analyze each screenshot visually to identify section types, component shapes, layout patterns, and decorative elements
3. Build the layout map from visual analysis instead

### Phase 2: Multi-Page Navigation

From the nav links extracted in Phase 1, visit up to **4 additional pages** (prioritize: About, Pricing, Features, Contact — or whatever nav links exist).

For each page:

```
1. agent-browser open <page-url>
2. agent-browser screenshot --full ./output/screenshots/<slug>-desktop.png
3. Read the screenshot — identify sections and components
4. Run layout structure extraction (same eval as Phase 1)
5. Note any unique sections/components NOT seen on the homepage
```

After visiting all pages, build a **cross-page component inventory**:

```
| Component        | Pages Found On         | Consistent? | Notes                        |
|-----------------|------------------------|-------------|------------------------------|
| nav             | all pages              | yes         | sticky, blur bg              |
| footer          | all pages              | yes         | 4-col dark                   |
| hero            | homepage only          | n/a         | centered with screenshot     |
| project cards   | homepage, /projects    | yes         | full-width rows              |
```

### Phase 3: Component-Level Deep Extraction

For each unique component type found across all pages, extract exact styles:

```bash
agent-browser eval "(() => {
  const components = {};

  // Buttons — primary and secondary
  const btns = [...document.querySelectorAll('a[class*=\"btn\"], button[class*=\"btn\"], a[class*=\"Button\"], button:not([class*=\"close\"]):not([class*=\"menu\"])')].slice(0, 3);
  components.buttons = btns.map(btn => {
    const cs = getComputedStyle(btn);
    return {
      text: btn.textContent.trim().substring(0, 30),
      bg: cs.backgroundColor, color: cs.color,
      border: cs.border, borderRadius: cs.borderRadius,
      padding: cs.padding, fontSize: cs.fontSize, fontWeight: cs.fontWeight,
      shadow: cs.boxShadow, transition: cs.transition,
      textTransform: cs.textTransform, letterSpacing: cs.letterSpacing
    };
  });

  // Cards
  const cards = [...document.querySelectorAll('[class*=\"card\"], [class*=\"Card\"], article')].slice(0, 2);
  components.cards = cards.map(card => {
    const cs = getComputedStyle(card);
    return {
      bg: cs.backgroundColor, border: cs.border,
      borderRadius: cs.borderRadius, shadow: cs.boxShadow,
      padding: cs.padding, overflow: cs.overflow
    };
  });

  // Headings
  ['h1','h2','h3','h4'].forEach(tag => {
    const el = document.querySelector(tag);
    if (el) {
      const cs = getComputedStyle(el);
      components[tag] = {
        fontSize: cs.fontSize, fontWeight: cs.fontWeight,
        lineHeight: cs.lineHeight, letterSpacing: cs.letterSpacing,
        color: cs.color, fontFamily: cs.fontFamily,
        textTransform: cs.textTransform
      };
    }
  });

  // Badges / tags
  const badge = document.querySelector('[class*=\"badge\"], [class*=\"tag\"], [class*=\"chip\"], [class*=\"label\"]');
  if (badge) {
    const cs = getComputedStyle(badge);
    components.badge = {
      bg: cs.backgroundColor, color: cs.color,
      borderRadius: cs.borderRadius, padding: cs.padding,
      fontSize: cs.fontSize, border: cs.border,
      textTransform: cs.textTransform
    };
  }

  // Input / form fields
  const input = document.querySelector('input[type=\"text\"], input[type=\"email\"], textarea');
  if (input) {
    const cs = getComputedStyle(input);
    components.input = {
      bg: cs.backgroundColor, border: cs.border,
      borderRadius: cs.borderRadius, padding: cs.padding,
      fontSize: cs.fontSize, color: cs.color
    };
  }

  return JSON.stringify(components, null, 2);
})()"
```

#### Motion & Animation Extraction

```bash
agent-browser eval "(() => {
  const motion = { transitions: [], animations: [], keyframes: [], scrollTriggers: [], marquees: [] };
  const seen = new Set();

  // Transitions and animations from all elements
  document.querySelectorAll('*').forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.transition && cs.transition !== 'all 0s ease 0s' && cs.transition !== 'none') {
      const key = cs.transition;
      if (!seen.has('t:'+key)) { seen.add('t:'+key); motion.transitions.push(key); }
    }
    if (cs.animationName && cs.animationName !== 'none') {
      const key = cs.animationName + ' ' + cs.animationDuration + ' ' + cs.animationTimingFunction + ' ' + cs.animationDelay + ' ' + cs.animationFillMode;
      if (!seen.has('a:'+key)) { seen.add('a:'+key); motion.animations.push(key); }
    }
  });

  // Extract @keyframes from stylesheets
  try {
    [...document.styleSheets].forEach(sheet => {
      try {
        [...sheet.cssRules].forEach(rule => {
          if (rule.type === CSSRule.KEYFRAMES_RULE) {
            const frames = [];
            [...rule.cssRules].forEach(fr => {
              frames.push({ offset: fr.keyText, style: fr.style.cssText });
            });
            motion.keyframes.push({ name: rule.name, frames });
          }
        });
      } catch(e) {} // CORS
    });
  } catch(e) {}

  // Detect scroll-triggered patterns
  const observers = [];
  const animatedEls = document.querySelectorAll('[data-framer-appear-id], [class*=\"reveal\"], [class*=\"animate\"], [class*=\"fade\"], [style*=\"opacity: 0\"], [style*=\"transform\"]');
  animatedEls.forEach(el => {
    const cs = getComputedStyle(el);
    observers.push({
      tag: el.tagName,
      classes: (el.className || '').toString().substring(0, 100),
      opacity: cs.opacity,
      transform: cs.transform !== 'none' ? cs.transform : null,
      dataAttrs: [...el.attributes].filter(a => a.name.startsWith('data-')).map(a => a.name + '=' + a.value.substring(0, 50)).slice(0, 5)
    });
  });
  motion.scrollTriggers = observers.slice(0, 15);

  // Detect marquee/ticker patterns
  document.querySelectorAll('[class*=\"marquee\"], [class*=\"ticker\"], [class*=\"scroll\"]').forEach(el => {
    const cs = getComputedStyle(el);
    const child = el.firstElementChild;
    const childCs = child ? getComputedStyle(child) : null;
    motion.marquees.push({
      width: el.offsetWidth,
      overflow: cs.overflow,
      childAnimation: childCs ? childCs.animationName + ' ' + childCs.animationDuration : null,
      text: el.textContent.trim().substring(0, 200)
    });
  });

  // Cap output
  motion.transitions = motion.transitions.slice(0, 10);
  motion.animations = motion.animations.slice(0, 10);
  motion.keyframes = motion.keyframes.slice(0, 10);
  return JSON.stringify(motion, null, 2);
})()"
```

#### Hover State Extraction

For buttons and interactive elements, capture hover effects:

```
1. agent-browser hover "button, a[class*='btn']"   → hover on primary CTA
2. agent-browser screenshot ./output/screenshots/hover-cta.png
3. Read screenshot — note color change, shadow change, scale, etc.
```

Compare with the non-hovered screenshot from Phase 1 to identify hover transitions.

#### Asset Inventory

```bash
agent-browser eval "(() => {
  const assets = { images: [], svgs: [], backgroundImages: [], externalStylesheets: [], externalScripts: [] };

  // Images
  document.querySelectorAll('img').forEach(img => {
    assets.images.push({
      src: img.src,
      alt: img.alt || '',
      width: img.naturalWidth,
      height: img.naturalHeight,
      loading: img.loading
    });
  });

  // SVGs (inline)
  document.querySelectorAll('svg').forEach((svg, i) => {
    if (i < 10) {
      assets.svgs.push({
        width: svg.getAttribute('width'),
        height: svg.getAttribute('height'),
        viewBox: svg.getAttribute('viewBox'),
        isIcon: (svg.closest('button, a, nav') !== null),
        pathCount: svg.querySelectorAll('path').length
      });
    }
  });

  // Background images
  document.querySelectorAll('*').forEach(el => {
    const bg = getComputedStyle(el).backgroundImage;
    if (bg && bg !== 'none' && !bg.startsWith('linear-gradient') && !bg.startsWith('radial-gradient')) {
      const urls = bg.match(/url\\(['\"]?([^'\"\\)]+)['\"]?\\)/g);
      if (urls) urls.forEach(u => assets.backgroundImages.push(u));
    }
  });
  assets.backgroundImages = [...new Set(assets.backgroundImages)].slice(0, 10);

  // External stylesheets
  document.querySelectorAll('link[rel=\"stylesheet\"]').forEach(l => {
    assets.externalStylesheets.push(l.href);
  });

  return JSON.stringify(assets, null, 2);
})()"
```

### Phase 4: Content Inventory

```bash
agent-browser eval "(() => {
  const content = { headings: [], ctas: [], navItems: [], footerLinks: [], paragraphs: [] };

  document.querySelectorAll('h1, h2, h3').forEach(h => {
    content.headings.push({ level: h.tagName, text: h.textContent.trim().substring(0, 200) });
  });

  document.querySelectorAll('a[class*=\"btn\"], button, a[class*=\"Button\"], [class*=\"cta\"]').forEach(el => {
    const text = el.textContent.trim();
    if (text && text.length < 50) content.ctas.push(text);
  });

  document.querySelectorAll('nav a, header nav a').forEach(a => {
    content.navItems.push(a.textContent.trim());
  });

  // First paragraph per section for tone analysis
  document.querySelectorAll('section p, [role=\"region\"] p').forEach((p, i) => {
    if (i < 10 && p.textContent.trim().length > 20) {
      content.paragraphs.push(p.textContent.trim().substring(0, 300));
    }
  });

  return JSON.stringify(content, null, 2);
})()"
```

### Phases 7-9: Mode C Only

> **Note:** Phases 7-9 are Mode C only. When running Mode C, execute Phases 1-4, then 7-9, then Phase 5 (compile), then Phase 6 (overlay). For non-Mode C, run Phases 1-6 as before.

### Phase 7: Firecrawl Content Scraping (Mode C)

Scrape the full page content using Firecrawl to ensure exact text reproduction — the LLM must NEVER guess or fabricate copy.

```bash
npx firecrawl scrape "<url>" --format markdown > ./output/firecrawl-content.md
```

Process the output:

1. Read the markdown output
2. Split by headings (`#`, `##`, `###`) → map each chunk to the corresponding `pages[].sections[].content` by matching headings to the section types identified in Phase 1
3. For each section, populate: `{headings, paragraphs, ctas, images, lists, raw_markdown}`
4. Store the full markdown in `meta.firecrawl_content.markdown`
5. Extract all links → `meta.firecrawl_content.links`
6. Extract title/description → `meta.firecrawl_content.metadata`

**Multi-page loop:** Repeat for each page URL from Phase 2 navigation. Run `npx firecrawl scrape` per page URL, map content to the corresponding `pages[i].sections[].content`.

**Non-headed section fallback:** For sections without matching headings (logos, stats, marquee), fall back to the DOM content inventory from Phase 4. Match by section index — `content.headings[i]`, `content.ctas`, and `content.paragraphs` that were extracted from the section's DOM subtree during Phase 1 layout detection.

**Fallback:** If `npx firecrawl` is not available or fails, use the Phase 4 DOM content inventory output instead. Map `content.headings`, `content.paragraphs`, and `content.ctas` to the per-section content objects.

**Rule:** The LLM must NEVER guess or fabricate copy. All text content in the replica MUST come from Firecrawl output or DOM extraction. If content for a section is missing, use `<!-- TODO: content not scraped -->` as a placeholder.

### Phase 8: Asset Download (Mode C)

Download all images, fonts, and background assets for local use in the replica.

**Multi-page loop:** Navigate to each page URL from Phase 2, extract and download assets per page.

1. Use `agent-browser eval` to extract all downloadable asset URLs:

```bash
agent-browser eval "(() => {
  const assets = [];
  // <img> src and srcset
  document.querySelectorAll('img').forEach(img => {
    if (img.src) assets.push({url: img.src, type: 'image'});
    if (img.srcset) img.srcset.split(',').forEach(s => {
      const u = s.trim().split(/\s+/)[0];
      if (u) assets.push({url: u, type: 'image'});
    });
  });
  // CSS background-image URLs
  document.querySelectorAll('*').forEach(el => {
    const bg = getComputedStyle(el).backgroundImage;
    if (bg && bg !== 'none') {
      const urls = bg.match(/url\(['\"]?([^'\"\\)]+)['\"]?\)/g);
      if (urls) urls.forEach(u => {
        const clean = u.replace(/url\(['\"]?/, '').replace(/['\"]?\)/, '');
        if (!clean.startsWith('data:')) assets.push({url: clean, type: 'background'});
      });
    }
  });
  // @font-face URLs from stylesheets
  try {
    [...document.styleSheets].forEach(sheet => {
      try {
        [...sheet.cssRules].forEach(rule => {
          if (rule.cssText && rule.cssText.includes('@font-face')) {
            const urls = rule.cssText.match(/url\(['\"]?([^'\"\\)]+)['\"]?\)/g);
            if (urls) urls.forEach(u => {
              const clean = u.replace(/url\(['\"]?/, '').replace(/['\"]?\)/, '');
              assets.push({url: clean, type: 'font'});
            });
          }
        });
      } catch(e) {}
    });
  } catch(e) {}
  // Deduplicate
  const seen = new Set();
  return JSON.stringify(assets.filter(a => {
    if (seen.has(a.url)) return false;
    seen.add(a.url);
    return true;
  }));
})()"
```

2. Save the URL list to `./output/asset-urls.json`
3. Run the download script:

```bash
bash scripts/download-assets.sh ./output/asset-urls.json ./output/assets/
```

4. Merge the resulting `./output/assets/asset-manifest.json` into `assets.local_manifest` in the design spec

### Phase 9: Per-Section Screenshots (Mode C)

Capture individual screenshots of each section for use as visual targets during section-by-section generation.

```bash
agent-browser eval "(() => {
  let allSections = document.querySelectorAll('section, [role=\"region\"], [role=\"banner\"], [role=\"contentinfo\"]');
  if (allSections.length < 3) {
    const main = document.querySelector('main') || document.body;
    allSections = main.querySelectorAll(':scope > div, :scope > section, :scope > header, :scope > footer');
  }
  return JSON.stringify([...allSections].map((el, i) => {
    const rect = el.getBoundingClientRect();
    return {index: i, top: Math.round(rect.top + window.scrollY), height: Math.round(rect.height), tag: el.tagName.toLowerCase()};
  }).filter(s => s.height >= 40));
})()"
```

For each section bounding rect:

1. Scroll to the section's top position
2. Set viewport to match section height: `agent-browser set viewport 1440 <height>`
3. Screenshot: `agent-browser screenshot ./output/screenshots/section-{i}-{type}.png`
4. Store path in `pages[].sections[].screenshot_path`
5. Reset viewport: `agent-browser set viewport 1440 900`

**Multi-page loop:** Repeat for each page URL from Phase 2 navigation. Navigate to the page, screenshot each section, store paths in the corresponding `pages[i].sections[].screenshot_path`.

**Multi-viewport:** Optionally repeat at 768px and 375px viewports for responsive regression targets. Store as `screenshot_path_tablet` and `screenshot_path_mobile`.

### Phase 5: Compile design-spec.json

Assemble all extracted data into a `design-spec.json` following the schema in `references/frontend/design-spec-schema.md`.

**Mapping from extraction to spec:**

| Extraction Output                 | Spec Field                                              |
| --------------------------------- | ------------------------------------------------------- |
| CSS Token: `bodyBg`, `mode`       | `theme.mode`                                            |
| CSS Token: color values           | `theme.colors.*` (convert RGB→HSL)                      |
| CSS Token: `radius`               | `theme.border_radius`                                   |
| CSS Token: `cardShadow`           | `theme.shadows.*`                                       |
| Font Inventory: computed fonts    | `typography.fonts.*`                                    |
| Font Inventory: Google Fonts URLs | `typography.google_fonts_import`                        |
| CSS Token: h1/h2/h3 sizes         | `typography.scale.*`                                    |
| Layout Structure: sections array  | `pages[0].sections`                                     |
| Layout Structure: navStyle        | `components.navbar`                                     |
| Component styles: buttons         | `components.buttons`                                    |
| Component styles: cards           | `components.cards`                                      |
| Motion: transitions/animations    | `motion.*`                                              |
| Motion: keyframes                 | `motion.special`                                        |
| Motion: marquees                  | `motion.special` + `components.special`                 |
| Asset Inventory                   | `assets.*`                                              |
| Content Inventory                 | Used for `pages[].sections[].content_summary`           |
| Firecrawl content                 | `pages[].sections[].content` + `meta.firecrawl_content` |
| Per-section screenshots           | `pages[].sections[].screenshot_path`                    |
| Asset manifest                    | `assets.local_manifest`                                 |

**Color conversion:** RGB `rgb(r, g, b)` → HSL `H S% L%`:

1. Normalize R, G, B to 0-1
2. Compute max, min, delta
3. H = sector-based hue, S = delta/(1 - |2L-1|), L = (max+min)/2
4. Output as `"H S% L%"` (no hsl() wrapper)

**Font identification:** Match computed `fontFamily` against the Google Fonts catalog in `references/frontend/design-resources.md`. If no exact match, find the closest visual equivalent.

**Archetype detection:** Compare extracted tokens against the 12 archetype profiles in `references/frontend/design-archetypes.md`. Match on: dark/light mode, border radius scale, shadow presence, font category, animation density.

Write the final spec to `./output/design-spec.json` (or `.context/design-spec.json` for multi-agent pipelines).

### Phase 6: Implementation Overlay Plan

After building the spec, produce a task list mapping each spec section to target files. This gives the implementing skill a concrete checklist.

```
## Implementation Overlay

| # | Spec Section | Target File | Changes Needed |
|---|---|---|---|
| 1 | theme.colors + theme.border_radius + theme.shadows | globals.css | Update CSS custom properties |
| 2 | typography.fonts + typography.scale | layout.tsx + globals.css | Import fonts, update type scale |
| 3 | components.navbar | components/nav.tsx | Match position, bg, blur, CTA |
| 4 | pages[0].sections (hero) | components/sections/hero.tsx | Match variant, elements, layout |
| 5 | pages[0].sections (features) | components/sections/features.tsx | Match grid, cards, icons |
| 6 | components.footer | components/footer.tsx | Match columns, style, links |
| 7 | components.buttons | components/ui/button.tsx | Match radius, padding, hover |
| 8 | components.cards | components/ui/card.tsx | Match border, shadow, radius |
| 9 | motion.* | lib/animations.ts | Timing, easing, stagger values |
| 10 | motion.special (marquee etc) | components/sections/marquee.tsx | Custom animation components |
```

Work through the overlay top-to-bottom: theme tokens first (they cascade), then layout components, then UI primitives, then animations.

## Usage in Skills

When a design skill receives a URL:

1. Run this extraction pipeline (all 6 phases)
2. The output is always `design-spec.json`
3. The consuming skill uses the spec as either:
   - **The target** (replicate mode — apply extracted spec directly, no propositions)
   - **Inspiration** (use spec data to inform the 3 propositions)
4. Always ask the user: "Should I match this design exactly, or use it as inspiration?"

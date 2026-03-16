# Component Variants Reference

> **Agents MUST select a variant matching the project's archetype. Do NOT default to centered hero + card-grid features + 4-column footer for every project.** Each archetype has a distinct structural fingerprint — the JSX bones below show exactly how they differ.

> **Mode C (Replicate):** When building a replica, do NOT select variants from this reference. Use `spec.variants.*` from the `design-spec.json` — these were extracted from the original site. This reference is for Mode A/B only.

Cross-reference `references/frontend/design-archetypes.md` for archetype definitions.

---

## 1. Hero Variants

### centered

**Archetypes:** Minimal, Corporate
**Differentiator:** Symmetrical, text stacked center, visual below the fold line.

```jsx
<section className="py-24 text-center">
  <div className="mx-auto max-w-3xl space-y-6">
    <p className="text-sm font-medium uppercase tracking-widest text-muted-foreground">
      Tagline
    </p>
    <h1 className="text-5xl font-bold tracking-tight">Headline</h1>
    <p className="text-lg text-muted-foreground">Subheadline</p>
    <div className="flex items-center justify-center gap-4">
      <Button size="lg">Primary CTA</Button>
      <Button variant="outline" size="lg">
        Secondary
      </Button>
    </div>
  </div>
  <div className="mx-auto mt-16 max-w-5xl">
    <Image /> {/* screenshot / product visual */}
  </div>
</section>
```

### split

**Archetypes:** Corporate, Organic
**Differentiator:** Two equal columns — content never overlaps the visual. Grounded, balanced.

```jsx
<section className="py-24">
  <div className="grid items-center gap-12 lg:grid-cols-2">
    <div className="space-y-6">
      <p className="text-sm font-medium text-primary">Tagline</p>
      <h1 className="text-5xl font-bold tracking-tight">Headline</h1>
      <p className="text-lg text-muted-foreground">Subheadline</p>
      <div className="flex gap-4">
        <Button size="lg">Primary CTA</Button>
        <Button variant="ghost" size="lg">
          Secondary
        </Button>
      </div>
    </div>
    <div className="relative aspect-[4/3] overflow-hidden rounded-xl">
      <Image className="object-cover" fill />
    </div>
  </div>
</section>
```

### fullscreen

**Archetypes:** Luxury, Bold
**Differentiator:** Viewport-filling visual, text floats on overlay. Immersive, cinematic.

```jsx
<section className="relative flex h-screen items-center justify-center">
  <Image className="absolute inset-0 object-cover" fill />
  <div className="absolute inset-0 bg-black/50" />
  <div className="relative z-10 text-center text-white">
    <h1 className="text-7xl font-light tracking-tight">Headline</h1>
    <p className="mt-4 text-xl font-light opacity-80">Subheadline</p>
    <Button size="lg" className="mt-8">
      CTA
    </Button>
  </div>
</section>
```

### bento

**Archetypes:** Aurora, Glassmorphism
**Differentiator:** Multi-cell grid where hero content and feature previews coexist. No single focal point — the grid IS the hero.

```jsx
<section className="py-24">
  <div className="grid gap-4 md:grid-cols-3 md:grid-rows-2">
    <div className="col-span-2 row-span-2 flex flex-col justify-center rounded-2xl bg-gradient-to-br from-primary/10 to-primary/5 p-12">
      <h1 className="text-5xl font-bold">Headline</h1>
      <p className="mt-4 text-lg text-muted-foreground">Subheadline</p>
      <Button size="lg" className="mt-8 w-fit">
        CTA
      </Button>
    </div>
    <div className="rounded-2xl border bg-card p-6">
      {/* Feature preview cell 1 */}
      <Icon />
      <p className="mt-2 font-medium">Feature A</p>
    </div>
    <div className="rounded-2xl border bg-card p-6">
      {/* Feature preview cell 2 */}
      <Icon />
      <p className="mt-2 font-medium">Feature B</p>
    </div>
  </div>
</section>
```

### statement

**Archetypes:** Brutalist, Editorial
**Differentiator:** Typography IS the design. Massive type, near-zero decoration.

```jsx
<section className="flex min-h-[80vh] items-end pb-24">
  <div className="space-y-8">
    <h1 className="text-[8vw] font-black uppercase leading-[0.9] tracking-tighter">
      Two or Three
      <br />
      Word Statement
    </h1>
    <div className="flex items-center gap-6">
      <Button size="lg" className="rounded-none uppercase">
        Enter
      </Button>
      <p className="max-w-xs text-sm text-muted-foreground">Brief descriptor</p>
    </div>
  </div>
</section>
```

### asymmetric

**Archetypes:** Neubrutalism, Bold
**Differentiator:** Broken grid — text and visual deliberately misaligned. Offset positions, elements overlap or float.

```jsx
<section className="relative py-32">
  <div className="ml-[5%] max-w-xl">
    <h1 className="text-6xl font-extrabold leading-tight">
      Headline That
      <br />
      Breaks Convention
    </h1>
    <p className="mt-6 text-lg text-muted-foreground">Subheadline</p>
    <Button
      size="lg"
      className="mt-8 rounded-full border-2 border-black shadow-[4px_4px_0_black]"
    >
      CTA
    </Button>
  </div>
  <div className="absolute -top-12 right-[8%] w-[40%] rotate-3">
    <div className="overflow-hidden rounded-2xl border-4 border-black shadow-[8px_8px_0_black]">
      <Image />
    </div>
  </div>
</section>
```

---

## 2. Navigation Variants

### bar

**Archetypes:** Minimal, Corporate, Editorial
**Differentiator:** Predictable, professional. Border-bottom anchors it.

```jsx
<header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur">
  <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
    <Logo />
    <div className="hidden items-center gap-8 md:flex">
      <NavLink>Product</NavLink>
      <NavLink>Pricing</NavLink>
      <NavLink>About</NavLink>
    </div>
    <Button size="sm">Get Started</Button>
  </nav>
</header>
```

### pill

**Archetypes:** Playful, Aurora
**Differentiator:** Floats detached from edges, rounded-full, appears on scroll. Feels lightweight.

```jsx
<header
  className={cn(
    "fixed left-1/2 top-6 z-50 -translate-x-1/2 transition-all duration-300",
    scrolled ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-4",
  )}
>
  <nav className="flex items-center gap-6 rounded-full border bg-background/80 px-6 py-2 shadow-lg backdrop-blur">
    <Logo className="h-6" />
    <NavLink>Features</NavLink>
    <NavLink>Pricing</NavLink>
    <Button size="sm" className="rounded-full">
      Start
    </Button>
  </nav>
</header>
```

### transparent

**Archetypes:** Luxury, Bold, Glassmorphism
**Differentiator:** Invisible on load (overlays hero), materializes on scroll. Hero feels uninterrupted.

```jsx
<header
  className={cn(
    "fixed top-0 z-50 w-full transition-colors duration-300",
    scrolled ? "bg-background/95 shadow-sm backdrop-blur" : "bg-transparent",
  )}
>
  <nav className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6">
    <Logo className={cn(scrolled ? "text-foreground" : "text-white")} />
    <div className="hidden items-center gap-8 md:flex">
      <NavLink className={cn(scrolled ? "text-foreground" : "text-white/90")}>
        About
      </NavLink>
      <NavLink className={cn(scrolled ? "text-foreground" : "text-white/90")}>
        Collection
      </NavLink>
    </div>
    <Button
      variant="outline"
      className={cn(scrolled ? "" : "border-white text-white")}
    >
      Contact
    </Button>
  </nav>
</header>
```

### sidebar

**Archetypes:** Brutalist, Editorial (blogs/magazines)
**Differentiator:** Vertical navigation on the left. Page content shifts right. Works for content-heavy sites.

```jsx
<aside className="fixed left-0 top-0 z-50 flex h-screen w-64 flex-col border-r bg-background p-8">
  <Logo className="mb-12" />
  <nav className="flex flex-1 flex-col gap-2">
    <NavLink className="rounded-md px-3 py-2 text-sm font-medium">Home</NavLink>
    <NavLink className="rounded-md px-3 py-2 text-sm font-medium">
      Archive
    </NavLink>
    <NavLink className="rounded-md px-3 py-2 text-sm font-medium">
      About
    </NavLink>
  </nav>
  <div className="text-xs text-muted-foreground">&copy; 2026</div>
</aside>;
{
  /* Main content uses ml-64 */
}
```

### split-bar

**Archetypes:** Neubrutalism, Cyberpunk
**Differentiator:** Thick borders, hard visual weight. Logo, links, and actions each in distinct zones.

```jsx
<header className="sticky top-0 z-50 border-b-4 border-black bg-background">
  <nav className="grid h-16 grid-cols-3">
    <div className="flex items-center border-r-4 border-black px-6">
      <Logo className="font-black uppercase" />
    </div>
    <div className="flex items-center justify-center gap-6 border-r-4 border-black">
      <NavLink className="font-bold uppercase">Work</NavLink>
      <NavLink className="font-bold uppercase">About</NavLink>
      <NavLink className="font-bold uppercase">Blog</NavLink>
    </div>
    <div className="flex items-center justify-end px-6">
      <Button className="rounded-none border-2 border-black font-bold uppercase shadow-[3px_3px_0_black]">
        Contact
      </Button>
    </div>
  </nav>
</header>
```

---

## 3. Footer Variants

### 4-column

**Archetypes:** Corporate, Minimal
**Differentiator:** Structured, informational. Logo column + 3 link groups + bottom legal bar.

```jsx
<footer className="border-t bg-background py-16">
  <div className="mx-auto grid max-w-7xl gap-8 px-6 md:grid-cols-4">
    <div className="space-y-4">
      <Logo />
      <p className="text-sm text-muted-foreground">Brief brand description.</p>
    </div>
    <div>
      <h4 className="mb-4 text-sm font-semibold">Product</h4>
      <ul className="space-y-2 text-sm text-muted-foreground">
        <li>
          <FooterLink>Features</FooterLink>
        </li>
        <li>
          <FooterLink>Pricing</FooterLink>
        </li>
      </ul>
    </div>
    <div>
      <h4 className="mb-4 text-sm font-semibold">Company</h4>
      <ul className="space-y-2 text-sm text-muted-foreground">
        <li>
          <FooterLink>About</FooterLink>
        </li>
        <li>
          <FooterLink>Blog</FooterLink>
        </li>
      </ul>
    </div>
    <div>
      <h4 className="mb-4 text-sm font-semibold">Legal</h4>
      <ul className="space-y-2 text-sm text-muted-foreground">
        <li>
          <FooterLink>Privacy</FooterLink>
        </li>
        <li>
          <FooterLink>Terms</FooterLink>
        </li>
      </ul>
    </div>
  </div>
  <div className="mx-auto mt-12 max-w-7xl border-t px-6 pt-6 text-xs text-muted-foreground">
    &copy; 2026 Brand. All rights reserved.
  </div>
</footer>
```

### minimal

**Archetypes:** Luxury, Brutalist
**Differentiator:** Single horizontal line. Nothing extra. Lets the content above be the final word.

```jsx
<footer className="border-t py-8">
  <div className="mx-auto flex max-w-7xl items-center justify-between px-6">
    <Logo className="h-5" />
    <nav className="flex gap-6 text-sm text-muted-foreground">
      <FooterLink>Privacy</FooterLink>
      <FooterLink>Terms</FooterLink>
      <FooterLink>Contact</FooterLink>
    </nav>
    <p className="text-xs text-muted-foreground">&copy; 2026</p>
  </div>
</footer>
```

### dark-inverted

**Archetypes:** Bold, Aurora
**Differentiator:** Contrasting dark background creates visual anchor at page bottom. Often includes a newsletter signup.

```jsx
<footer className="bg-foreground text-background">
  <div className="mx-auto max-w-7xl px-6 py-20">
    <div className="grid gap-12 md:grid-cols-2">
      <div className="space-y-6">
        <Logo className="text-background" />
        <p className="max-w-sm text-background/70">
          Brand description or tagline.
        </p>
        <div className="flex gap-4">
          <SocialIcon />
          <SocialIcon />
        </div>
      </div>
      <div className="space-y-4">
        <h4 className="text-lg font-semibold">Stay updated</h4>
        <div className="flex gap-2">
          <Input
            placeholder="Email"
            className="bg-background/10 border-background/20 text-background"
          />
          <Button variant="secondary">Subscribe</Button>
        </div>
      </div>
    </div>
    <div className="mt-16 border-t border-background/20 pt-6 text-sm text-background/50">
      &copy; 2026 Brand. All rights reserved.
    </div>
  </div>
</footer>
```

### split

**Archetypes:** Organic, Editorial
**Differentiator:** Two columns — narrative brand story on the left, links on the right. Warmer, editorial feel.

```jsx
<footer className="border-t bg-muted/30 py-16">
  <div className="mx-auto grid max-w-7xl gap-12 px-6 md:grid-cols-2">
    <div className="space-y-4">
      <Logo />
      <p className="max-w-md text-muted-foreground leading-relaxed">
        A longer brand narrative — who we are, what we care about. 2-3 sentences
        that feel human and warm.
      </p>
      <div className="flex gap-4 pt-2">
        <SocialIcon />
        <SocialIcon />
      </div>
    </div>
    <div className="grid grid-cols-2 gap-8">
      <div>
        <h4 className="mb-4 text-sm font-semibold">Navigate</h4>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>
            <FooterLink>Home</FooterLink>
          </li>
          <li>
            <FooterLink>About</FooterLink>
          </li>
          <li>
            <FooterLink>Blog</FooterLink>
          </li>
        </ul>
      </div>
      <div>
        <h4 className="mb-4 text-sm font-semibold">Connect</h4>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>
            <FooterLink>Contact</FooterLink>
          </li>
          <li>
            <FooterLink>Privacy</FooterLink>
          </li>
          <li>
            <FooterLink>Terms</FooterLink>
          </li>
        </ul>
      </div>
    </div>
  </div>
</footer>
```

---

## 4. Feature Section Variants

### card-grid

**Archetypes:** Minimal, Corporate
**Differentiator:** Equal-weight cards in a uniform grid. Clean, scannable.

```jsx
<section className="py-24">
  <div className="mx-auto max-w-3xl text-center">
    <h2 className="text-3xl font-bold">Section Title</h2>
    <p className="mt-4 text-muted-foreground">Section description</p>
  </div>
  <div className="mx-auto mt-16 grid max-w-7xl gap-8 px-6 md:grid-cols-3">
    {features.map((f) => (
      <div key={f.title} className="rounded-xl border bg-card p-8">
        <Icon className="h-10 w-10 text-primary" />
        <h3 className="mt-4 text-lg font-semibold">{f.title}</h3>
        <p className="mt-2 text-sm text-muted-foreground">{f.description}</p>
      </div>
    ))}
  </div>
</section>
```

### bento

**Archetypes:** Aurora, Glassmorphism
**Differentiator:** Asymmetric grid — cards have different spans and sizes. Visual hierarchy through size, not just order.

```jsx
<section className="py-24">
  <h2 className="text-center text-3xl font-bold">Section Title</h2>
  <div className="mx-auto mt-16 grid max-w-7xl gap-4 px-6 md:grid-cols-3 md:grid-rows-2">
    <div className="col-span-2 rounded-2xl bg-gradient-to-br from-primary/10 to-transparent p-8">
      <Icon />
      <h3 className="mt-4 text-xl font-semibold">Primary Feature</h3>
      <p className="mt-2 text-muted-foreground">
        Longer description for the hero feature.
      </p>
    </div>
    <div className="rounded-2xl border p-8">
      <Icon />
      <h3 className="mt-4 font-semibold">Feature B</h3>
      <p className="mt-2 text-sm text-muted-foreground">Short desc</p>
    </div>
    <div className="rounded-2xl border p-8">
      <Icon />
      <h3 className="mt-4 font-semibold">Feature C</h3>
      <p className="mt-2 text-sm text-muted-foreground">Short desc</p>
    </div>
    <div className="col-span-2 rounded-2xl border p-8">
      <Icon />
      <h3 className="mt-4 text-xl font-semibold">Secondary Feature</h3>
      <p className="mt-2 text-muted-foreground">Medium description.</p>
    </div>
  </div>
</section>
```

### alternating-rows

**Archetypes:** Organic, Editorial
**Differentiator:** Each feature is a full-width row alternating image side. Narrative pacing — reads like a story.

```jsx
<section className="space-y-24 py-24">
  {features.map((f, i) => (
    <div
      key={f.title}
      className={cn(
        "mx-auto grid max-w-7xl items-center gap-16 px-6 md:grid-cols-2",
        i % 2 === 1 && "md:[&>*:first-child]:order-2",
      )}
    >
      <div className="space-y-4">
        <p className="text-sm font-medium text-primary">{f.label}</p>
        <h3 className="text-3xl font-bold">{f.title}</h3>
        <p className="text-muted-foreground leading-relaxed">{f.description}</p>
      </div>
      <div className="aspect-[4/3] overflow-hidden rounded-xl bg-muted">
        <Image />
      </div>
    </div>
  ))}
</section>
```

### icon-list

**Archetypes:** Brutalist, Cyberpunk
**Differentiator:** Vertical stack, no cards. Large icon paired with text. Raw, direct.

```jsx
<section className="py-24">
  <h2 className="text-4xl font-black uppercase tracking-tighter">Features</h2>
  <div className="mt-16 space-y-12">
    {features.map((f) => (
      <div
        key={f.title}
        className="flex gap-8 border-b border-foreground/20 pb-12"
      >
        <Icon className="h-16 w-16 shrink-0" />
        <div>
          <h3 className="text-2xl font-bold">{f.title}</h3>
          <p className="mt-2 text-muted-foreground">{f.description}</p>
        </div>
      </div>
    ))}
  </div>
</section>
```

### stacked-full

**Archetypes:** Bold, Luxury
**Differentiator:** Each feature takes full viewport width with alternating backgrounds. Grand, spacious.

```jsx
<div>
  {features.map((f, i) => (
    <section
      key={f.title}
      className={cn("py-32", i % 2 === 0 ? "bg-background" : "bg-muted/50")}
    >
      <div className="mx-auto max-w-4xl px-6 text-center">
        <Icon className="mx-auto h-12 w-12 text-primary" />
        <h3 className="mt-6 text-4xl font-bold">{f.title}</h3>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
          {f.description}
        </p>
        <div className="mx-auto mt-12 max-w-5xl">
          <Image /> {/* large visual / screenshot */}
        </div>
      </div>
    </section>
  ))}
</div>
```

---

## 5. Testimonial Variants

### card-carousel

**Archetypes:** Playful, Bold
**Differentiator:** Horizontal scroll with visible overflow hinting at more cards. Energetic, social-proof rich.

```jsx
<section className="py-24">
  <h2 className="text-center text-3xl font-bold">What People Say</h2>
  <div className="mt-16 flex gap-6 overflow-x-auto px-6 pb-4 snap-x">
    {testimonials.map((t) => (
      <div
        key={t.name}
        className="w-[350px] shrink-0 snap-center rounded-xl border bg-card p-8"
      >
        <p className="text-muted-foreground">&ldquo;{t.quote}&rdquo;</p>
        <div className="mt-6 flex items-center gap-3">
          <Avatar src={t.avatar} />
          <div>
            <p className="text-sm font-semibold">{t.name}</p>
            <p className="text-xs text-muted-foreground">{t.role}</p>
          </div>
        </div>
      </div>
    ))}
  </div>
</section>
```

### single-spotlight

**Archetypes:** Luxury, Minimal
**Differentiator:** One quote at a time, large and centered. Restraint signals quality.

```jsx
<section className="py-32">
  <div className="mx-auto max-w-3xl text-center">
    <blockquote className="text-2xl font-light leading-relaxed text-foreground/90">
      &ldquo;{testimonial.quote}&rdquo;
    </blockquote>
    <div className="mt-8 flex flex-col items-center gap-3">
      <Avatar src={testimonial.avatar} className="h-14 w-14" />
      <div>
        <p className="font-semibold">{testimonial.name}</p>
        <p className="text-sm text-muted-foreground">{testimonial.role}</p>
      </div>
    </div>
  </div>
</section>
```

### grid-mosaic

**Archetypes:** Aurora, Neubrutalism
**Differentiator:** Masonry-style grid with varying card heights. Feels curated, not templated.

```jsx
<section className="py-24">
  <h2 className="text-center text-3xl font-bold">Testimonials</h2>
  <div className="mx-auto mt-16 max-w-7xl columns-1 gap-6 px-6 sm:columns-2 lg:columns-3">
    {testimonials.map((t) => (
      <div
        key={t.name}
        className="mb-6 break-inside-avoid rounded-xl border bg-card p-6"
      >
        <p className="text-sm text-muted-foreground">&ldquo;{t.quote}&rdquo;</p>
        <div className="mt-4 flex items-center gap-3">
          <Avatar src={t.avatar} className="h-8 w-8" />
          <p className="text-sm font-medium">{t.name}</p>
        </div>
      </div>
    ))}
  </div>
</section>
```

### inline-quotes

**Archetypes:** Editorial, Brutalist
**Differentiator:** No cards, no avatars. Just text. Typography carries the weight.

```jsx
<section className="py-24">
  <div className="mx-auto max-w-4xl space-y-16 px-6">
    {testimonials.map((t) => (
      <div key={t.name} className="border-l-4 border-foreground pl-8">
        <p className="text-xl leading-relaxed">&ldquo;{t.quote}&rdquo;</p>
        <p className="mt-4 text-sm font-semibold">
          {t.name}{" "}
          <span className="font-normal text-muted-foreground">
            &mdash; {t.role}
          </span>
        </p>
      </div>
    ))}
  </div>
</section>
```

---

## 6. CTA Section Variants

### banner

**Archetypes:** Minimal, Corporate
**Differentiator:** Full-width colored band. Simple, unmissable.

```jsx
<section className="bg-primary py-16 text-primary-foreground">
  <div className="mx-auto max-w-3xl text-center">
    <h2 className="text-3xl font-bold">Ready to get started?</h2>
    <p className="mt-4 opacity-90">Brief supporting text.</p>
    <Button size="lg" variant="secondary" className="mt-8">
      Get Started
    </Button>
  </div>
</section>
```

### card

**Archetypes:** Playful, Aurora
**Differentiator:** Contained card floating in the page with its own background. Feels like an object, not a section.

```jsx
<section className="py-24">
  <div className="mx-auto max-w-4xl rounded-2xl bg-gradient-to-br from-primary to-primary/80 p-16 text-center text-primary-foreground">
    <h2 className="text-3xl font-bold">Start building today</h2>
    <p className="mt-4 opacity-90">Supporting description.</p>
    <div className="mt-8 flex items-center justify-center gap-4">
      <Button size="lg" variant="secondary">
        Primary CTA
      </Button>
      <Button
        size="lg"
        variant="outline"
        className="border-primary-foreground text-primary-foreground"
      >
        Secondary
      </Button>
    </div>
  </div>
</section>
```

### split-visual

**Archetypes:** Organic, Bold
**Differentiator:** Half text + CTA, half image. The visual reinforces the action.

```jsx
<section className="py-24">
  <div className="mx-auto grid max-w-7xl items-center gap-16 px-6 md:grid-cols-2">
    <div className="space-y-6">
      <h2 className="text-4xl font-bold">Take the next step</h2>
      <p className="text-lg text-muted-foreground">
        Supporting text that motivates action.
      </p>
      <Button size="lg">Get Started</Button>
    </div>
    <div className="aspect-[4/3] overflow-hidden rounded-xl bg-muted">
      <Image className="object-cover" fill />
    </div>
  </div>
</section>
```

---

## 7. Pricing Variants

### tier-cards

**Archetypes:** Minimal, SaaS
**Differentiator:** Side-by-side cards, one highlighted. Scannable comparison.

```jsx
<section className="py-24">
  <h2 className="text-center text-3xl font-bold">Pricing</h2>
  <div className="mx-auto mt-16 grid max-w-5xl gap-8 px-6 md:grid-cols-3">
    {plans.map((plan) => (
      <div
        key={plan.name}
        className={cn(
          "rounded-xl border p-8",
          plan.featured && "border-primary bg-primary/5 shadow-lg",
        )}
      >
        <h3 className="text-lg font-semibold">{plan.name}</h3>
        <p className="mt-2 text-sm text-muted-foreground">{plan.description}</p>
        <p className="mt-6 text-4xl font-bold">
          {plan.price}
          <span className="text-base font-normal text-muted-foreground">
            /mo
          </span>
        </p>
        <Button
          className={cn("mt-8 w-full", plan.featured ? "" : "variant-outline")}
        >
          Choose {plan.name}
        </Button>
        <ul className="mt-8 space-y-3 text-sm">
          {plan.features.map((f) => (
            <li key={f} className="flex items-center gap-2">
              <CheckIcon className="h-4 w-4 text-primary" /> {f}
            </li>
          ))}
        </ul>
      </div>
    ))}
  </div>
</section>
```

### comparison-table

**Archetypes:** Corporate, Enterprise
**Differentiator:** Feature matrix table. Dense information for serious buyers.

```jsx
<section className="py-24">
  <h2 className="text-center text-3xl font-bold">Compare Plans</h2>
  <div className="mx-auto mt-16 max-w-5xl overflow-x-auto px-6">
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b">
          <th className="pb-4 font-medium text-muted-foreground">Feature</th>
          {plans.map((p) => (
            <th key={p.name} className="pb-4 text-center font-semibold">
              {p.name}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {featureRows.map((row) => (
          <tr key={row.label} className="border-b">
            <td className="py-4">{row.label}</td>
            {plans.map((p) => (
              <td key={p.name} className="py-4 text-center">
                {row.values[p.name] === true ? (
                  <CheckIcon className="mx-auto h-4 w-4 text-primary" />
                ) : row.values[p.name] === false ? (
                  <span className="text-muted-foreground">&mdash;</span>
                ) : (
                  row.values[p.name]
                )}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
</section>
```

### toggle-plans

**Archetypes:** Playful, Bold
**Differentiator:** Interactive toggle between billing periods. Cards animate on switch.

```jsx
<section className="py-24">
  <h2 className="text-center text-3xl font-bold">Pricing</h2>
  <div className="mt-8 flex items-center justify-center gap-3">
    <span className={cn("text-sm", !annual && "font-semibold")}>Monthly</span>
    <Switch checked={annual} onCheckedChange={setAnnual} />
    <span className={cn("text-sm", annual && "font-semibold")}>
      Annual <span className="text-xs text-primary">Save 20%</span>
    </span>
  </div>
  <div className="mx-auto mt-12 grid max-w-5xl gap-8 px-6 md:grid-cols-3">
    {plans.map((plan) => (
      <div
        key={plan.name}
        className="rounded-2xl border bg-card p-8 transition-all duration-300"
      >
        <h3 className="text-lg font-semibold">{plan.name}</h3>
        <p className="mt-6 text-4xl font-bold">
          {annual ? plan.annualPrice : plan.monthlyPrice}
          <span className="text-base font-normal text-muted-foreground">
            /mo
          </span>
        </p>
        <Button className="mt-8 w-full">Get Started</Button>
        <ul className="mt-6 space-y-3 text-sm">
          {plan.features.map((f) => (
            <li key={f} className="flex items-center gap-2">
              <CheckIcon className="h-4 w-4 text-primary" /> {f}
            </li>
          ))}
        </ul>
      </div>
    ))}
  </div>
</section>
```

---

## Quick Archetype-to-Variant Map

| Archetype     | Hero                  | Nav         | Footer        | Features         | Testimonials     | CTA          | Pricing          |
| ------------- | --------------------- | ----------- | ------------- | ---------------- | ---------------- | ------------ | ---------------- |
| Minimal       | centered              | bar         | 4-column      | card-grid        | single-spotlight | banner       | tier-cards       |
| Corporate     | centered/split        | bar         | 4-column      | card-grid        | card-carousel    | banner       | comparison-table |
| Luxury        | fullscreen            | transparent | minimal       | stacked-full     | single-spotlight | banner       | tier-cards       |
| Bold          | fullscreen/asymmetric | transparent | dark-inverted | stacked-full     | card-carousel    | split-visual | toggle-plans     |
| Organic       | split                 | bar         | split         | alternating-rows | single-spotlight | split-visual | tier-cards       |
| Editorial     | statement             | bar/sidebar | split         | alternating-rows | inline-quotes    | banner       | tier-cards       |
| Brutalist     | statement             | split-bar   | minimal       | icon-list        | inline-quotes    | banner       | tier-cards       |
| Neubrutalism  | asymmetric            | split-bar   | dark-inverted | icon-list        | grid-mosaic      | card         | toggle-plans     |
| Aurora        | bento                 | pill        | dark-inverted | bento            | grid-mosaic      | card         | toggle-plans     |
| Glassmorphism | bento                 | transparent | dark-inverted | bento            | grid-mosaic      | card         | tier-cards       |
| Playful       | asymmetric            | pill        | dark-inverted | card-grid        | card-carousel    | card         | toggle-plans     |
| Cyberpunk     | statement             | split-bar   | dark-inverted | icon-list        | inline-quotes    | banner       | toggle-plans     |

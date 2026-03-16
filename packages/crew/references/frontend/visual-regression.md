# Visual Regression Loop

After all sections are built, run a visual regression loop (max 3 iterations per viewport):

1. **Screenshot the replica** at 1440px:
   ```
   agent-browser open http://localhost:3000
   agent-browser set viewport 1440 900
   agent-browser screenshot --full ./output/screenshots/replica-desktop.png
   ```
2. **Use the archived full-page screenshot** from Phase 1 (`./output/screenshots/home-desktop.png`) as the comparison baseline. This avoids dynamic content drift (cookie banners, A/B tests, live content changes). Only fall back to re-screenshotting `<source_url>` if the archived screenshot is missing.
3. **Run pixel diff:**
   ```bash
   node scripts/visual-diff.mjs ./output/screenshots/original-desktop.png ./output/screenshots/replica-desktop.png ./output/screenshots/diff-desktop.png
   ```
4. **Evaluate:** If `diffPercent > 15%`, read the diff image, identify the top 3 mismatch regions, fix the corresponding section components, and iterate
5. **Repeat** at 768px (threshold 20%) and 375px (threshold 25%)

Exit the loop when all viewports pass their thresholds or max iterations reached.

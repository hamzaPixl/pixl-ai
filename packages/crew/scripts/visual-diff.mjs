#!/usr/bin/env node
// Visual diff between two PNG screenshots using pixelmatch.
// Usage: node scripts/visual-diff.mjs <original.png> <replica.png> [diff-output.png]
// Output: JSON to stdout with {width, height, diffPixels, totalPixels, diffPercent, diffPath}
//
// Dependencies are installed on-demand if missing.

import { execSync } from "child_process";
import { readFileSync, writeFileSync, existsSync } from "fs";
import { resolve } from "path";

// On-demand install
try {
  await import("pixelmatch");
} catch {
  console.error("Installing pixelmatch and pngjs...");
  execSync("npm install --no-save pixelmatch pngjs", { stdio: "inherit" });
}

const { default: pixelmatch } = await import("pixelmatch");
const { PNG } = await import("pngjs");

const [, , origPath, replicaPath, diffPath] = process.argv;

if (!origPath || !replicaPath) {
  console.error(
    "Usage: node scripts/visual-diff.mjs <original.png> <replica.png> [diff-output.png]"
  );
  process.exit(1);
}

const origPng = PNG.sync.read(readFileSync(resolve(origPath)));
const replicaPng = PNG.sync.read(readFileSync(resolve(replicaPath)));

// Use the smaller dimensions to handle size mismatches
const width = Math.min(origPng.width, replicaPng.width);
const height = Math.min(origPng.height, replicaPng.height);

// Crop both images to the common dimensions
function cropData(png, w, h) {
  if (png.width === w && png.height === h) return png.data;
  const cropped = Buffer.alloc(w * h * 4);
  for (let y = 0; y < h; y++) {
    png.data.copy(cropped, y * w * 4, y * png.width * 4, y * png.width * 4 + w * 4);
  }
  return cropped;
}

const origData = cropData(origPng, width, height);
const replicaData = cropData(replicaPng, width, height);

const diff = new PNG({ width, height });
const diffPixels = pixelmatch(origData, replicaData, diff.data, width, height, {
  threshold: 0.1,
});

const totalPixels = width * height;
const diffPercent = +((diffPixels / totalPixels) * 100).toFixed(2);

let outputDiffPath = null;
if (diffPath) {
  outputDiffPath = resolve(diffPath);
  writeFileSync(outputDiffPath, PNG.sync.write(diff));
}

const result = {
  width,
  height,
  diffPixels,
  totalPixels,
  diffPercent,
  diffPath: outputDiffPath,
};

console.log(JSON.stringify(result, null, 2));

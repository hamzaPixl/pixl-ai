import { describe, it, expect } from "vitest";
import { validateSessionImportBundle } from "../src/types";

describe("smoke", () => {
  it("validateSessionImportBundle rejects null body", () => {
    const errors = validateSessionImportBundle(null);
    expect(errors.length).toBeGreaterThan(0);
  });

  it("validateSessionImportBundle rejects non-object body", () => {
    const errors = validateSessionImportBundle("bad");
    expect(errors.length).toBeGreaterThan(0);
  });

  it("validateSessionImportBundle rejects missing session fields", () => {
    const errors = validateSessionImportBundle({ session: {} });
    expect(errors.length).toBeGreaterThan(0);
  });

  it("validateSessionImportBundle accepts a valid minimal bundle", () => {
    const errors = validateSessionImportBundle({
      session: { id: "s-1", feature_id: "f-1" },
    });
    expect(errors.length).toBe(0);
  });
});

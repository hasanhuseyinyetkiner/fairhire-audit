import { describe, expect, it } from "vitest";

import { formatCount, formatInterval, formatRate } from "./format";

describe("formatRate", () => {
  it("renders a real zero and withholds a missing rate", () => {
    expect(formatRate(0)).toBe("0.0%");
    expect(formatRate(0.8)).toBe("80.0%");
    expect(formatRate(null)).toBe("—");
    expect(formatRate(undefined)).toBe("—");
  });
});

describe("formatCount", () => {
  it("keeps integers exact and blanks missing values", () => {
    expect(formatCount(100)).toBe("100");
    expect(formatCount(0.25)).toBe("0.25");
    expect(formatCount(null)).toBe("—");
  });
});

describe("formatInterval", () => {
  it("does not draw a missing bound as zero", () => {
    expect(formatInterval(0, 0.2)).toBe("0.0% – 20.0%");
    expect(formatInterval(null, null)).toBe("—");
  });
});

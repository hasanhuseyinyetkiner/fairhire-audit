import { describe, expect, it } from "vitest";

/** Mirrors ThresholdPage request-id gating for rapid slider changes. */
function acceptResponse(activeId: number, responseId: number): boolean {
  return responseId === activeId;
}

type LabState = { error: string | null; liveResult: string | null };

/** Mirrors onMutate: clear error when a new mutate starts. */
function onMutateClear(state: LabState): void {
  state.error = null;
}

/**
 * Mirrors ThresholdPage success/error handlers after onMutate moved off MutateOptions.
 * Only the latest request id may set liveResult or error.
 */
function applyNetworkOutcome(
  state: LabState,
  activeId: number,
  responseId: number,
  outcome: { ok: true; data: string } | { ok: false; message: string },
): void {
  if (responseId !== activeId) return;
  if (outcome.ok) {
    state.liveResult = outcome.data;
    state.error = null;
    return;
  }
  state.error = outcome.message;
}

describe("threshold stale response gate", () => {
  it("accepts only the latest request id", () => {
    let active = 0;
    active += 1;
    const first = active;
    active += 1;
    const second = active;
    expect(acceptResponse(active, first)).toBe(false);
    expect(acceptResponse(active, second)).toBe(true);
  });

  it("rejects network-late responses after a newer mutate", () => {
    const active = 3;
    expect(acceptResponse(active, 1)).toBe(false);
    expect(acceptResponse(active, 2)).toBe(false);
    expect(acceptResponse(active, 3)).toBe(true);
  });
});

describe("threshold network error path after onMutate", () => {
  it("clears a prior error when onMutate runs for a new attempt", () => {
    const state: LabState = { error: "The scenario failed.", liveResult: "old" };
    onMutateClear(state);
    expect(state.error).toBeNull();
    expect(state.liveResult).toBe("old");
  });

  it("sets error when the latest request fails", () => {
    const state: LabState = { error: null, liveResult: null };
    onMutateClear(state);
    applyNetworkOutcome(state, 2, 2, { ok: false, message: "Network down" });
    expect(state.error).toBe("Network down");
    expect(state.liveResult).toBeNull();
  });

  it("clears error when the latest request succeeds", () => {
    const state: LabState = { error: "stale", liveResult: null };
    applyNetworkOutcome(state, 4, 4, { ok: true, data: "metrics@0.5" });
    expect(state.error).toBeNull();
    expect(state.liveResult).toBe("metrics@0.5");
  });

  it("ignores a stale failure after a newer success", () => {
    const state: LabState = { error: null, liveResult: null };
    onMutateClear(state);
    applyNetworkOutcome(state, 5, 5, { ok: true, data: "metrics@0.7" });
    applyNetworkOutcome(state, 5, 4, { ok: false, message: "late failure" });
    expect(state.error).toBeNull();
    expect(state.liveResult).toBe("metrics@0.7");
  });

  it("ignores a stale success after a newer failure", () => {
    const state: LabState = { error: null, liveResult: "kept" };
    onMutateClear(state);
    applyNetworkOutcome(state, 6, 6, { ok: false, message: "latest failed" });
    applyNetworkOutcome(state, 6, 5, { ok: true, data: "stale metrics" });
    expect(state.error).toBe("latest failed");
    expect(state.liveResult).toBe("kept");
  });
});

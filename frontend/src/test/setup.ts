import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import { createMatchMedia } from "./match-media";

if (typeof window !== "undefined" && typeof window.matchMedia !== "function") {
  window.matchMedia = createMatchMedia(false);
}

// Recharts' ResponsiveContainer needs ResizeObserver, which jsdom does not
// implement. The stub is enough for layout-free component tests.
class ResizeObserverMock implements ResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = ResizeObserverMock;
}

afterEach(() => {
  cleanup();
});

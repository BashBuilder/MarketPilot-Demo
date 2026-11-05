import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import { createMatchMedia } from "./match-media";

if (typeof window !== "undefined" && typeof window.matchMedia !== "function") {
  window.matchMedia = createMatchMedia(false);
}

afterEach(() => {
  cleanup();
});

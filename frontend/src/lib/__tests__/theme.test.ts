import { beforeEach, describe, expect, it } from "vitest";
import {
  applyTheme,
  getThemeSnapshot,
  readStoredTheme,
  setTheme,
  THEME_INIT_SCRIPT,
  THEME_STORAGE_KEY,
} from "../theme";

beforeEach(() => {
  window.localStorage.clear();
  document.documentElement.classList.remove("dark");
  document.documentElement.style.colorScheme = "";
});

describe("applyTheme", () => {
  it("adds the dark class and colour scheme", () => {
    applyTheme("dark");

    expect(document.documentElement).toHaveClass("dark");
    expect(document.documentElement.style.colorScheme).toBe("dark");
  });

  it("removes the dark class when switching back", () => {
    applyTheme("dark");
    applyTheme("light");

    expect(document.documentElement).not.toHaveClass("dark");
    expect(document.documentElement.style.colorScheme).toBe("light");
  });
});

describe("storage", () => {
  it("reads valid stored preferences only", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "dark");
    expect(readStoredTheme()).toBe("dark");

    window.localStorage.setItem(THEME_STORAGE_KEY, "sepia");
    expect(readStoredTheme()).toBeNull();
  });

  it("persists an explicit choice and updates the document", () => {
    setTheme("dark");

    expect(readStoredTheme()).toBe("dark");
    expect(getThemeSnapshot()).toBe("dark");
  });
});

describe("init script", () => {
  it("references the shared storage key and system preference", () => {
    expect(THEME_INIT_SCRIPT).toContain(THEME_STORAGE_KEY);
    expect(THEME_INIT_SCRIPT).toContain("prefers-color-scheme: dark");
    expect(THEME_INIT_SCRIPT).not.toContain("</script>");
  });
});

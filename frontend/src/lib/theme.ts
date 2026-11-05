export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "marketpilot-theme";
export const THEME_CHANGE_EVENT = "marketpilot-theme-change";

function isTheme(value: string | null): value is Theme {
  return value === "light" || value === "dark";
}

export function getSystemTheme(): Theme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function readStoredTheme(): Theme | null {
  if (typeof window === "undefined") return null;

  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isTheme(value) ? value : null;
  } catch {
    // Storage can be unavailable in private or restricted browsing contexts.
    return null;
  }
}

export function getThemeSnapshot(): Theme {
  if (typeof document === "undefined") return "light";
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

export function getServerThemeSnapshot(): Theme {
  return "light";
}

export function applyTheme(theme: Theme): void {
  if (typeof document === "undefined") return;

  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.style.colorScheme = theme;
}

export function setTheme(theme: Theme): void {
  applyTheme(theme);

  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // The visual change still applies when persistence is unavailable.
  }

  window.dispatchEvent(new Event(THEME_CHANGE_EVENT));
}

/**
 * Keeps the toggle in sync with explicit choices (including other tabs) and
 * with the OS preference while the visitor has not chosen a theme yet.
 */
export function subscribeToTheme(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") return () => undefined;

  const media = window.matchMedia("(prefers-color-scheme: dark)");

  const handleSystemChange = (event: MediaQueryListEvent): void => {
    if (readStoredTheme() !== null) return;
    applyTheme(event.matches ? "dark" : "light");
    onStoreChange();
  };

  const handleStorage = (event: StorageEvent): void => {
    if (event.key !== THEME_STORAGE_KEY) return;
    applyTheme(isTheme(event.newValue) ? event.newValue : getSystemTheme());
    onStoreChange();
  };

  window.addEventListener(THEME_CHANGE_EVENT, onStoreChange);
  window.addEventListener("storage", handleStorage);
  media.addEventListener("change", handleSystemChange);

  return () => {
    window.removeEventListener(THEME_CHANGE_EVENT, onStoreChange);
    window.removeEventListener("storage", handleStorage);
    media.removeEventListener("change", handleSystemChange);
  };
}

/**
 * Runs before first paint so a stored preference never flashes the wrong theme.
 * Kept as a static string: no user input is interpolated into it.
 */
export const THEME_INIT_SCRIPT = `(function(){var stored=null;try{stored=window.localStorage.getItem(${JSON.stringify(
  THEME_STORAGE_KEY,
)});}catch(error){}var isDark=stored==="dark"||(stored!=="light"&&window.matchMedia("(prefers-color-scheme: dark)").matches);var root=document.documentElement;root.classList.toggle("dark",isDark);root.style.colorScheme=isDark?"dark":"light";})();`;

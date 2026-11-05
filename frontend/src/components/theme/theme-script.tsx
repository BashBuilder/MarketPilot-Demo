import { THEME_INIT_SCRIPT } from "@/lib/theme";

/**
 * Inlined before hydration to apply the visitor's theme without a flash.
 * The script is a static constant, so no untrusted value reaches the DOM.
 */
export function ThemeScript() {
  return <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />;
}

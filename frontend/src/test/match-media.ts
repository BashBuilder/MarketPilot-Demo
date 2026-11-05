/**
 * jsdom does not implement matchMedia. Tests can pass `matches` to simulate an
 * OS dark-mode preference; listeners are no-ops unless a test needs to drive
 * them, in which case it can override window.matchMedia locally.
 */
export function createMatchMedia(
  matches: boolean,
): (query: string) => MediaQueryList {
  return (query: string) =>
    ({
      matches,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}

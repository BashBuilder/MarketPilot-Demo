/**
 * Starts MSW for server-side fetches (Server Components, route handlers) when
 * mocking is enabled. The browser side is started by MockProvider.
 */
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  if (process.env.NEXT_PUBLIC_API_MOCKING !== "enabled") return;

  const { server } = await import("./mocks/server");
  server.listen({ onUnhandledFrame: "bypass" });
}

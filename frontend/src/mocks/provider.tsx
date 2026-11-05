"use client";

import { useEffect, useState, type ReactNode } from "react";

type WorkerState = "starting" | "ready" | "error";

// React Strict Mode runs effects twice; share one start call so MSW does not
// report that its network is already enabled.
let workerStart: Promise<void> | undefined;

function startMockWorker(): Promise<void> {
  workerStart ??= import("./browser")
    .then(({ worker }) => worker.start({ onUnhandledFrame: "bypass" }))
    .then(() => undefined)
    .catch((error: unknown) => {
      workerStart = undefined;
      throw error;
    });
  return workerStart;
}

/**
 * Starts the MSW browser worker after hydration. Only mounted when
 * NEXT_PUBLIC_API_MOCKING is enabled.
 */
export function MockProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<WorkerState>("starting");

  useEffect(() => {
    let cancelled = false;

    startMockWorker()
      .then(() => {
        if (!cancelled) setState("ready");
      })
      .catch((error: unknown) => {
        console.error("Failed to start the mock service worker", error);
        if (!cancelled) setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      {state === "error" ? (
        <div
          role="alert"
          className="border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-center text-sm text-destructive"
        >
          The mock API could not start. Reload the page to try again.
        </div>
      ) : null}
      {children}
    </>
  );
}

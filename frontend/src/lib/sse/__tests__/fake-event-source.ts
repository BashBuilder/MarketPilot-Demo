import type { SseEvent } from "@/lib/schemas";

type Listener = (event: Event) => void;

/** Minimal EventSource stand-in: named-event dispatch, open and drop control. */
export class FakeEventSource {
  static instances: FakeEventSource[] = [];

  readonly url: string;
  closed = false;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;

  private readonly listeners = new Map<string, Set<Listener>>();

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: Listener): void {
    const listeners = this.listeners.get(type) ?? new Set<Listener>();
    listeners.add(listener);
    this.listeners.set(type, listeners);
  }

  removeEventListener(type: string, listener: Listener): void {
    this.listeners.get(type)?.delete(listener);
  }

  close(): void {
    this.closed = true;
  }

  open(): void {
    this.onopen?.();
  }

  fail(): void {
    this.onerror?.();
  }

  emitEvent(event: SseEvent): void {
    this.emitRaw(event.event, JSON.stringify(event.data), event.id);
  }

  emitRaw(type: string, data: string, lastEventId: string): void {
    const message = new MessageEvent(type, { data, lastEventId });
    for (const listener of this.listeners.get(type) ?? []) {
      listener(message);
    }
  }
}

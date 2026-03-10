import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { WebSocketManager, ConnectionState } from "../../static/websocket-manager";
import { WEBSOCKET_CHECK_INTERVAL } from "../../static/constants";

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSED = 3;
  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  sent: any[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  constructor(url: string) {
    this.url = url;
  }
  close(_code?: number, _reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
  }
  send(data: any) {
    this.sent.push(data);
  }
  triggerOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }
  triggerMessage(data: any) {
    const ev = { data: JSON.stringify(data) } as MessageEvent;
    this.onmessage?.(ev);
  }
  triggerClose(code: number) {
    const ev = { code } as unknown as CloseEvent;
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(ev);
  }
}

describe("WebSocketManager", () => {
  let originalWebSocket: typeof WebSocket;

  beforeEach(() => {
    originalWebSocket = globalThis.WebSocket;
    globalThis.WebSocket = MockWebSocket as unknown as typeof WebSocket;
  });

  afterEach(() => {
    globalThis.WebSocket = originalWebSocket;
  });

  it("should connect and report connected state, and dispatch messages to handlers", async () => {
    const wsManager = new WebSocketManager("example.com", 1234, "token-123");
    const received: any[] = [];
    let connectedCalled = false;

    wsManager.on("synctex", (data) => {
      received.push(data);
    });
    wsManager.onConnect(() => {
      connectedCalled = true;
    });

    wsManager.connect();

    const mockSocket = (wsManager as any).socket as MockWebSocket;
    expect(mockSocket).toBeTruthy();
    mockSocket.triggerOpen();

    expect(wsManager.connectionState).toBe(ConnectionState.CONNECTED);
    expect(wsManager.isConnected).toBe(true);
    expect(connectedCalled).toBe(true);

    const msg = { action: "synctex", page: 2, x: 10, y: 20, timestamp: Date.now() };
    mockSocket.triggerMessage(msg);
    expect(received).toContainEqual(msg);

    mockSocket.triggerMessage({ action: "ping" });
    expect(mockSocket.sent.length).toBeGreaterThan(0);
    const lastSent = mockSocket.sent[mockSocket.sent.length - 1];
    expect(typeof lastSent).toBe("string");
    expect(JSON.parse(lastSent)).toEqual({ action: "pong" });
  });

  it("should handle close with various codes and invoke disconnect callback accordingly", () => {
    const wsManager = new WebSocketManager("host", 5678, null);
    let disconnectCode: number | null = null;
    wsManager.onDisconnect((code) => {
      disconnectCode = code;
    });

    wsManager.connect();
    const mockSocket = (wsManager as any).socket as MockWebSocket;
    mockSocket.triggerOpen();

    mockSocket.triggerClose(1000);
    expect(disconnectCode).toBeNull();

    mockSocket.triggerClose(4000);
    expect(disconnectCode).toBe(4000);
  });

  it("should trigger error callback on error event", () => {
    const wsManager = new WebSocketManager("host", 1111, null);
    let errorCalled = false;
    wsManager.onError(() => {
      errorCalled = true;
    });
    wsManager.connect();
    const mockSocket = (wsManager as any).socket as MockWebSocket;
    mockSocket.triggerOpen();
    mockSocket.onerror?.(new Event("error"));
    expect(errorCalled).toBe(true);
  });

  it("should return true from ensureConnected when connection succeeds", async () => {
    vi.useFakeTimers();
    const wsManager = new WebSocketManager("host", 2222, null);
    wsManager.connect();
    const mockSocket = (wsManager as any).socket as MockWebSocket;
    mockSocket.triggerOpen();

    const p = wsManager.ensureConnected();
    vi.advanceTimersByTime(WEBSOCKET_CHECK_INTERVAL);
    const result = await p;
    expect(result).toBe(true);
    vi.useRealTimers();
  });
});

/**
 * EntangledPdf Viewer - WebSocket Manager
 *
 * Manages WebSocket connection, reconnection, and message dispatch.
 */

import { ACTION_SYNCTEX, ACTION_RELOAD } from './constants';
import type { WebSocketMessage, WebSocketAction } from './types';
import {
  WEBSOCKET_CHECK_INTERVAL,
  WEBSOCKET_CONNECT_TIMEOUT,
  MAX_RECONNECT_DELAY,
  WEBSOCKET_PING_INTERVAL,
} from './constants';

/**
 * Handler function type for WebSocket messages
 */
export type MessageHandler = (data: WebSocketMessage) => void;

/**
 * WebSocket connection state
 */
export enum ConnectionState {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  CLOSING = 'closing',
}

/**
 * WebSocket manager with message dispatch and reconnection
 */
export class WebSocketManager {
  private socket: WebSocket | null = null;
  private state: ConnectionState = ConnectionState.DISCONNECTED;
  private currentConnectionId: number = 0;
  private handlers: Map<WebSocketAction, MessageHandler[]> = new Map();
  private reconnectAttempts = 0;
  private onErrorCallback: ((message: string) => void) | null = null;
  private onConnectCallback: (() => void) | null = null;
  private onDisconnectCallback: ((code: number) => void) | null = null;
  private host: string;
  private port: number;
  private token: string | null;
  private pingIntervalId: number | null = null;
  private lastPingTime: number = 0;
  private reconnectTimeoutId: number | null = null;
  private onInvalidTokenCallback: (() => void) | null = null;

  constructor(host: string, port: number, token: string | null = null) {
    this.host = host;
    this.port = port;
    this.token = token;
  }

  /**
   * Register a handler for a specific message action
   * @param action - The message action to handle
   * @param handler - The handler function
   * @returns Unregister function
   */
  on(action: WebSocketAction, handler: MessageHandler): () => void {
    if (!this.handlers.has(action)) {
      this.handlers.set(action, []);
    }
    this.handlers.get(action)!.push(handler);

    // Return unregister function
    return () => {
      const handlers = this.handlers.get(action);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }

  /**
   * Set error callback
   */
  onError(callback: (message: string) => void): void {
    this.onErrorCallback = callback;
  }

  /**
   * Set connect callback
   */
  onConnect(callback: () => void): void {
    this.onConnectCallback = callback;
  }

  /**
   * Set disconnect callback
   */
  onDisconnect(callback: (code: number) => void): void {
    this.onDisconnectCallback = callback;
  }

  /**
   * Set invalid token callback (server restarted)
   */
  onInvalidToken(callback: () => void): void {
    this.onInvalidTokenCallback = callback;
  }

  /**
   * Get current connection state
   */
  get connectionState(): ConnectionState {
    return this.state;
  }

  /**
   * Check if connected
   */
  get isConnected(): boolean {
    return this.state === ConnectionState.CONNECTED && 
           this.socket !== null && 
           this.socket.readyState === WebSocket.OPEN;
  }

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    // Prevent duplicate connections
    if (this.socket && 
        (this.socket.readyState === WebSocket.CONNECTING || 
         this.socket.readyState === WebSocket.OPEN)) {
      console.log('WebSocket already connecting or connected');
      return;
    }

    // Clear any pending auto-reconnect since we're manually connecting
    this.stopAutoReconnect();

    // Clean up existing socket
    if (this.socket) {
      try {
        this.socket.close();
      } catch {
        // Ignore errors on close
      }
      this.socket = null;
    }

    // Increment connection ID to track current connection
    // This prevents race conditions where old socket close overwrites new connection state
    this.currentConnectionId++;
    const connectionId = this.currentConnectionId;

    this.state = ConnectionState.CONNECTING;
    console.log('Connecting to WebSocket...');
    console.log('WebSocket token:', this.token ? `${this.token.substring(0, 8)}...` : 'null/undefined');

    // Build WebSocket URL
    let wsUrl = `wss://${this.host}:${this.port}/ws`;
    if (this.token) {
      wsUrl += `?token=${encodeURIComponent(this.token)}`;
      console.log('WebSocket URL with token:', wsUrl.replace(this.token, '***TOKEN***'));
    } else {
      console.log('WebSocket URL (no token):', wsUrl);
    }

    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      this.state = ConnectionState.CONNECTED;
      this.reconnectAttempts = 0;
      console.log('WebSocket connected');
      this.startKeepalive();
      this.onConnectCallback?.();
    };

    this.socket.onmessage = (event: MessageEvent) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data);
        console.log('WebSocket message received:', data);
        this.dispatchMessage(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    this.socket.onclose = (event: CloseEvent) => {
      // Only update state if this is still the current connection
      // Prevents race condition where old socket close overwrites new connection
      if (this.currentConnectionId !== connectionId) {
        return;
      }
      this.state = ConnectionState.DISCONNECTED;
      this.socket = null;
      this.stopKeepalive();
      const reason = event.reason ? `: ${event.reason}` : '';
      console.log(`WebSocket closed (code: ${event.code}${reason})`);
      
      // Handle invalid token (server restarted with new token)
      if (event.code === 4002) {
        console.log('WebSocket closed: Invalid token - server may have restarted');
        this.onInvalidTokenCallback?.();
        return;
      }
      
      // Handle token required (not authenticated)
      if (event.code === 4001) {
        console.log('WebSocket closed: Token required - user not authenticated');
        this.onInvalidTokenCallback?.();
        return;
      }
      
      // Don't show error for clean closures
      if (event.code !== 1000 && event.code !== 1001) {
        this.onDisconnectCallback?.(event.code);
        // Start auto-reconnect with exponential backoff
        this.startAutoReconnect();
      }
    };

    this.socket.onerror = (error: Event) => {
      // Only update state if this is still the current connection
      if (this.currentConnectionId !== connectionId) {
        return;
      }
      console.error('WebSocket error:', error);
      this.socket = null;
      this.state = ConnectionState.DISCONNECTED;
      this.onErrorCallback?.('WebSocket connection error');
    };
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.stopKeepalive();
    this.stopAutoReconnect(); // Stop auto-reconnect on manual disconnect
    if (this.socket) {
      this.state = ConnectionState.CLOSING;
      try {
        this.socket.close(1000, 'Client disconnect');
      } catch {
        // Ignore
      }
      this.socket = null;
    }
    this.state = ConnectionState.DISCONNECTED;
  }

  /**
   * Send a message to the server
   * @param message - The message to send
   * @returns true if sent successfully
   */
  send(message: WebSocketMessage): boolean {
    if (!this.isConnected) {
      console.warn('WebSocket not connected, cannot send message');
      return false;
    }

    try {
      this.socket!.send(JSON.stringify(message));
      return true;
    } catch (e) {
      console.error('Failed to send WebSocket message:', e);
      return false;
    }
  }

  /**
   * Ensure connection is established, with timeout
   * @param timeoutMs - Timeout in milliseconds
   * @returns Promise resolving to connection status
   */
  async ensureConnected(timeoutMs: number = WEBSOCKET_CONNECT_TIMEOUT): Promise<boolean> {
    if (this.isConnected) {
      return true;
    }

    this.connect();

    return new Promise((resolve) => {
      let elapsed = 0;

      const check = () => {
        if (this.isConnected) {
          resolve(true);
          return;
        }

        elapsed += WEBSOCKET_CHECK_INTERVAL;
        if (elapsed >= timeoutMs) {
          resolve(false);
          return;
        }

        setTimeout(check, WEBSOCKET_CHECK_INTERVAL);
      };

      setTimeout(check, WEBSOCKET_CHECK_INTERVAL);
    });
  }

  /**
   * Send inverse search request
   * @param page - Page number
   * @param x - X coordinate in PDF points
   * @param y - Y coordinate in PDF points
   * @returns true if sent successfully
   */
  async sendInverseSearch(page: number, x: number, y: number): Promise<boolean> {
    const connected = await this.ensureConnected();
    if (!connected) {
      return false;
    }

    return this.send({
      action: 'inverse_search',
      page,
      x,
      y,
    });
  }

  /**
   * Dispatch message to registered handlers
   */
  private dispatchMessage(data: WebSocketMessage): void {
    // Handle pong for connection keepalive (client-authoritative)
    if (data.action === 'pong') {
      const rtt = Date.now() - (data.timestamp || this.lastPingTime);
      console.log(`WebSocket pong received (RTT: ${rtt}ms)`);
      return;
    }

    // Dispatch to registered handlers
    const handlers = this.handlers.get(data.action);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data);
        } catch (e) {
          console.error(`Error in handler for ${data.action}:`, e);
        }
      });
    }
  }

  /**
   * Start keepalive ping interval (client-authoritative)
   * Client pings every 25 seconds before server's 30s timeout
   */
  private startKeepalive(): void {
    this.stopKeepalive(); // Clear any existing interval
    
    this.pingIntervalId = window.setInterval(() => {
      if (this.isConnected) {
        this.lastPingTime = Date.now();
        this.send({ action: 'ping', timestamp: this.lastPingTime });
      }
    }, WEBSOCKET_PING_INTERVAL);
  }

  /**
   * Stop keepalive ping interval
   */
  private stopKeepalive(): void {
    if (this.pingIntervalId !== null) {
      window.clearInterval(this.pingIntervalId);
      this.pingIntervalId = null;
    }
  }

  /**
   * Calculate reconnection delay with exponential backoff
   */
  private calculateReconnectDelay(): number {
    return Math.min(
      1000 * Math.pow(2, this.reconnectAttempts),
      MAX_RECONNECT_DELAY
    );
  }

  /**
   * Start automatic reconnection with exponential backoff
   */
  private startAutoReconnect(): void {
    // Don't start if already reconnecting or connected
    if (this.reconnectTimeoutId !== null || this.isConnected) {
      return;
    }

    const delay = this.calculateReconnectDelay();
    this.reconnectAttempts++;
    
    console.log(`Auto-reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    this.reconnectTimeoutId = window.setTimeout(() => {
      this.reconnectTimeoutId = null;
      if (!this.isConnected) {
        this.connect();
      }
    }, delay);
  }

  /**
   * Stop auto-reconnect timeout
   */
  private stopAutoReconnect(): void {
    if (this.reconnectTimeoutId !== null) {
      window.clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
  }
}

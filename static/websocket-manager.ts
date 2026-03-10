/**
 * PdfServer Viewer - WebSocket Manager
 *
 * Manages WebSocket connection, reconnection, and message dispatch.
 */

import { ACTION_SYNCTEX, ACTION_RELOAD } from './constants';
import type { WebSocketMessage, WebSocketAction } from './types';
import {
  WEBSOCKET_CHECK_INTERVAL,
  WEBSOCKET_CONNECT_TIMEOUT,
  MAX_RECONNECT_DELAY,
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

    // Build WebSocket URL
    let wsUrl = `wss://${this.host}:${this.port}/ws`;
    if (this.token) {
      wsUrl += `?token=${encodeURIComponent(this.token)}`;
    }

    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      this.state = ConnectionState.CONNECTED;
      this.reconnectAttempts = 0;
      console.log('WebSocket connected');
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
      console.log(`WebSocket closed (code: ${event.code})`);
      
      // Don't show error for clean closures
      if (event.code !== 1000 && event.code !== 1001) {
        this.onDisconnectCallback?.(event.code);
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
    // Handle ping/pong for connection keepalive
    if (data.action === 'ping') {
      this.send({ action: 'pong' });
      return;
    }
    
    if (data.action === 'pong') {
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
   * Calculate reconnection delay with exponential backoff
   */
  private calculateReconnectDelay(): number {
    return Math.min(
      1000 * Math.pow(2, this.reconnectAttempts),
      MAX_RECONNECT_DELAY
    );
  }
}

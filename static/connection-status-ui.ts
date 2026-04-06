/**
 * Connection Status UI Component
 *
 * Pure UI functions for rendering connection status indicator and details panel.
 * No business logic - only view rendering.
 */

/**
 * Connection status states
 */
export type ConnectionStatus = 'connected' | 'disconnected' | 'reload-needed';

/**
 * WebSocket connection state
 */
export type WebSocketConnectionState = 'connecting' | 'connected' | 'disconnected';

/**
 * State for connection status UI
 */
export interface ConnectionStatusState {
  status: ConnectionStatus;
  filename: string;
  mtime: number;
  connectionState: WebSocketConnectionState;
}

/**
 * Get display text for status
 */
export function getStatusText(status: ConnectionStatus): string {
  const texts: Record<ConnectionStatus, string> = {
    'connected': 'Connected',
    'disconnected': 'Reconnect',
    'reload-needed': 'Reload',
  };
  return texts[status];
}

/**
 * Get CSS class for status
 */
export function getStatusClass(status: ConnectionStatus): string {
  return `connection-status-${status}`;
}

/**
 * Get display text for connection state
 */
export function getConnectionStateText(state: WebSocketConnectionState): string {
  const texts: Record<WebSocketConnectionState, string> = {
    'connecting': 'Connecting...',
    'connected': 'Connected',
    'disconnected': 'Disconnected',
  };
  return texts[state];
}

/**
 * Get CSS class for connection state
 */
export function getConnectionStateClass(state: WebSocketConnectionState): string {
  return `status-${state}`;
}

/**
 * Format mtime as locale string
 */
export function formatMtime(mtime: number): string {
  if (!mtime || mtime <= 0) {
    return '-';
  }
  const date = new Date(mtime * 1000);
  return date.toLocaleString();
}

/**
 * Render status indicator HTML
 */
export function renderStatusIndicator(state: ConnectionStatusState): string {
  const statusText = getStatusText(state.status);
  
  return `
    <span class="status-dot"></span>
    <span class="status-text">${statusText}</span>
  `;
}

/**
 * Render connection details panel HTML
 */
export function renderDetailsPanel(state: ConnectionStatusState): string {
  const stateText = getConnectionStateText(state.connectionState);
  const stateClass = getConnectionStateClass(state.connectionState);
  const filename = state.filename || '-';
  const modified = formatMtime(state.mtime);
  
  return `
    <h4>Connection Details</h4>
    <div class="detail-row">
      <span class="detail-label">Status</span>
      <span class="detail-value ${stateClass}">${stateText}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">PDF File</span>
      <span class="detail-value" title="${filename}">${filename}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">PDF Modified</span>
      <span class="detail-value">${modified}</span>
    </div>
  `;
}

/**
 * Determine status from connection and pending reload state
 */
export function determineStatus(
  isConnected: boolean,
  hasPendingReload: boolean
): ConnectionStatus {
  if (!isConnected) {
    return 'disconnected';
  }
  if (hasPendingReload) {
    return 'reload-needed';
  }
  return 'connected';
}

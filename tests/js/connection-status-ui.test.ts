import { describe, it, expect } from 'vitest';
import {
  getStatusText,
  getStatusClass,
  getConnectionStateText,
  getConnectionStateClass,
  formatMtime,
  renderStatusIndicator,
  renderDetailsPanel,
  determineStatus,
  type ConnectionStatusState,
} from '../../static/connection-status-ui';

describe('Connection Status UI', () => {
  describe('getStatusText()', () => {
    it('should return "Connected" for connected status', () => {
      expect(getStatusText('connected')).toBe('Connected');
    });

    it('should return "Reconnect" for disconnected status', () => {
      expect(getStatusText('disconnected')).toBe('Reconnect');
    });

    it('should return "Reload" for reload-needed status', () => {
      expect(getStatusText('reload-needed')).toBe('Reload');
    });
  });

  describe('getStatusClass()', () => {
    it('should return correct CSS class for connected', () => {
      expect(getStatusClass('connected')).toBe('connection-status-connected');
    });

    it('should return correct CSS class for disconnected', () => {
      expect(getStatusClass('disconnected')).toBe('connection-status-disconnected');
    });

    it('should return correct CSS class for reload-needed', () => {
      expect(getStatusClass('reload-needed')).toBe('connection-status-reload-needed');
    });
  });

  describe('getConnectionStateText()', () => {
    it('should return "Connecting..." for connecting state', () => {
      expect(getConnectionStateText('connecting')).toBe('Connecting...');
    });

    it('should return "Connected" for connected state', () => {
      expect(getConnectionStateText('connected')).toBe('Connected');
    });

    it('should return "Disconnected" for disconnected state', () => {
      expect(getConnectionStateText('disconnected')).toBe('Disconnected');
    });
  });

  describe('getConnectionStateClass()', () => {
    it('should return correct CSS class for connecting', () => {
      expect(getConnectionStateClass('connecting')).toBe('status-connecting');
    });

    it('should return correct CSS class for connected', () => {
      expect(getConnectionStateClass('connected')).toBe('status-connected');
    });

    it('should return correct CSS class for disconnected', () => {
      expect(getConnectionStateClass('disconnected')).toBe('status-disconnected');
    });
  });

  describe('formatMtime()', () => {
    it('should format valid mtime as locale string', () => {
      // March 15, 2024 12:30:00 UTC
      const mtime = 1710508200;
      const result = formatMtime(mtime);
      
      // Result should be a date string, not just a number
      expect(result).not.toBe('-');
      expect(typeof result).toBe('string');
      expect(result.length).toBeGreaterThan(0);
    });

    it('should return "-" for zero mtime', () => {
      expect(formatMtime(0)).toBe('-');
    });

    it('should return "-" for negative mtime', () => {
      expect(formatMtime(-1)).toBe('-');
    });

    it('should return "-" for undefined mtime', () => {
      expect(formatMtime(undefined as any)).toBe('-');
    });
  });

  describe('renderStatusIndicator()', () => {
    it('should render status indicator with connected state', () => {
      const state: ConnectionStatusState = {
        status: 'connected',
        filename: 'test.pdf',
        mtime: 1710508200,
        connectionState: 'connected',
      };

      const html = renderStatusIndicator(state);
      
      expect(html).toContain('status-dot');
      expect(html).toContain('status-text');
      expect(html).toContain('Connected');
    });

    it('should render status indicator with disconnected state', () => {
      const state: ConnectionStatusState = {
        status: 'disconnected',
        filename: 'test.pdf',
        mtime: 1710508200,
        connectionState: 'disconnected',
      };

      const html = renderStatusIndicator(state);
      
      expect(html).toContain('Reconnect');
    });

    it('should render status indicator with reload-needed state', () => {
      const state: ConnectionStatusState = {
        status: 'reload-needed',
        filename: 'test.pdf',
        mtime: 1710508200,
        connectionState: 'connected',
      };

      const html = renderStatusIndicator(state);
      
      expect(html).toContain('Reload');
    });
  });

  describe('renderDetailsPanel()', () => {
    it('should render details panel with all information', () => {
      const state: ConnectionStatusState = {
        status: 'connected',
        filename: 'test.pdf',
        mtime: 1710508200,
        connectionState: 'connected',
      };

      const html = renderDetailsPanel(state);
      
      expect(html).toContain('Connection Details');
      expect(html).toContain('Status');
      expect(html).toContain('PDF File');
      expect(html).toContain('PDF Modified');
      expect(html).toContain('Connected');
      expect(html).toContain('test.pdf');
    });

    it('should include status CSS class for connection state', () => {
      const state: ConnectionStatusState = {
        status: 'disconnected',
        filename: 'test.pdf',
        mtime: 1710508200,
        connectionState: 'disconnected',
      };

      const html = renderDetailsPanel(state);
      
      expect(html).toContain('status-disconnected');
      expect(html).toContain('Disconnected');
    });

    it('should include status CSS class for connecting state', () => {
      const state: ConnectionStatusState = {
        status: 'disconnected',
        filename: 'test.pdf',
        mtime: 1710508200,
        connectionState: 'connecting',
      };

      const html = renderDetailsPanel(state);
      
      expect(html).toContain('status-connecting');
      expect(html).toContain('Connecting...');
    });

    it('should handle empty filename gracefully', () => {
      const state: ConnectionStatusState = {
        status: 'connected',
        filename: '',
        mtime: 1710508200,
        connectionState: 'connected',
      };

      const html = renderDetailsPanel(state);
      
      expect(html).toContain('-');
    });

    it('should include title attribute for filename truncation', () => {
      const state: ConnectionStatusState = {
        status: 'connected',
        filename: 'very-long-filename-that-might-be-truncated.pdf',
        mtime: 1710508200,
        connectionState: 'connected',
      };

      const html = renderDetailsPanel(state);
      
      expect(html).toContain('title="very-long-filename-that-might-be-truncated.pdf"');
    });
  });

  describe('determineStatus()', () => {
    it('should return connected when connected and no pending reload', () => {
      expect(determineStatus(true, false)).toBe('connected');
    });

    it('should return disconnected when not connected', () => {
      expect(determineStatus(false, false)).toBe('disconnected');
      expect(determineStatus(false, true)).toBe('disconnected');
    });

    it('should return reload-needed when connected and has pending reload', () => {
      expect(determineStatus(true, true)).toBe('reload-needed');
    });
  });

  describe('Integration: renderStatusIndicator with determineStatus', () => {
    it('should render correct indicator for each combined state', () => {
      const scenarios = [
        { connected: true, pending: false, expected: 'Connected' },
        { connected: false, pending: false, expected: 'Reconnect' },
        { connected: false, pending: true, expected: 'Reconnect' },
        { connected: true, pending: true, expected: 'Reload' },
      ];

      scenarios.forEach(({ connected, pending, expected }) => {
        const status = determineStatus(connected, pending);
        const state: ConnectionStatusState = {
          status,
          filename: 'test.pdf',
          mtime: 1710508200,
          connectionState: connected ? 'connected' : 'disconnected',
        };

        const html = renderStatusIndicator(state);
        expect(html).toContain(expected);
      });
    });
  });
});

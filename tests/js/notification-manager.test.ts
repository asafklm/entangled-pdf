import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  NotificationManager,
  NotificationConfig,
  createErrorBanner,
  getNotificationManager,
} from '../../static/notification-manager';
import { TOOLTIP_AUTO_HIDE_DELAY } from '../../static/constants';

describe('Notification Manager', () => {
  let manager: NotificationManager;

  beforeEach(() => {
    // Clean up document body
    document.body.innerHTML = '';
    vi.useFakeTimers();
    // Create fresh manager for each test
    manager = new NotificationManager();
  });

  afterEach(() => {
    // Clean up any remaining notifications
    manager.hideAll();
    vi.runAllTimers();
    vi.useRealTimers();
    vi.clearAllTimers();
    document.body.innerHTML = '';
  });

  describe('API: show()', () => {
    it('should create and display a notification element', () => {
      const config: NotificationConfig = {
        severity: 'info',
        message: 'Test notification',
      };

      const element = manager.show(config);

      // Verify element exists in DOM
      expect(document.body.contains(element)).toBe(true);
      expect(element.className).toContain('notification');
      expect(element.className).toContain('notification-info');
      expect(element.textContent).toBe('Test notification');
    });

    it('should apply correct CSS classes for each severity level', () => {
      const severities = ['error', 'warning', 'info', 'success'] as const;

      severities.forEach((severity) => {
        document.body.innerHTML = ''; // Clean up between tests
        const config: NotificationConfig = {
          severity,
          message: `Test ${severity}`,
          autoHide: false,
        };

        const element = manager.show(config);
        expect(element.className).toContain(`notification-${severity}`);
      });
    });

    it('should position notification at center by default', () => {
      const config: NotificationConfig = {
        severity: 'info',
        message: 'Center positioned',
      };

      const element = manager.show(config);
      // Currently uses inline styles (will be CSS classes after refactoring)
      // Default position is 'center' (when position is undefined)
      expect(element.style.position).toBe('fixed');
      expect(element.style.top).toBe('50%');
      expect(element.style.transform).toBe('translate(-50%, -50%)');
    });

    it('should auto-hide after default delay by default', () => {
      const config: NotificationConfig = {
        severity: 'info',
        message: 'Auto-hide test',
      };

      manager.show(config);
      expect(document.querySelector('.notification')).toBeTruthy();

      // Fast forward past auto-hide delay
      vi.advanceTimersByTime(TOOLTIP_AUTO_HIDE_DELAY);

      expect(document.querySelector('.notification')).toBeNull();
    });

    it('should not auto-hide when autoHide is false', () => {
      const config: NotificationConfig = {
        severity: 'error',
        message: 'Persistent notification',
        autoHide: false,
      };

      manager.show(config);

      // Fast forward well past auto-hide delay
      vi.advanceTimersByTime(TOOLTIP_AUTO_HIDE_DELAY + 10000);

      expect(document.querySelector('.notification')).toBeTruthy();
    });

    it('should use custom hide delay when provided', () => {
      const config: NotificationConfig = {
        severity: 'info',
        message: 'Custom delay',
        hideDelay: 1000,
      };

      manager.show(config);

      // Should still be visible before custom delay
      vi.advanceTimersByTime(500);
      expect(document.querySelector('.notification')).toBeTruthy();

      // Should be hidden after custom delay
      vi.advanceTimersByTime(600);
      expect(document.querySelector('.notification')).toBeNull();
    });

    it('should call onClick callback when notification is clicked', () => {
      const onClick = vi.fn();
      const config: NotificationConfig = {
        severity: 'info',
        message: 'Clickable notification',
        onClick,
        autoHide: false,
      };

      const element = manager.show(config);
      element.click();

      expect(onClick).toHaveBeenCalledTimes(1);
      expect(document.querySelector('.notification')).toBeNull(); // Should auto-hide after click
    });

    it('should hide on click even without onClick callback', () => {
      const config: NotificationConfig = {
        severity: 'info',
        message: 'Click to dismiss',
        autoHide: false,
      };

      const element = manager.show(config);
      expect(document.querySelector('.notification')).toBeTruthy();

      element.click();

      expect(document.querySelector('.notification')).toBeNull();
    });

    it('should support different positions', () => {
      const positions: Array<'top' | 'bottom' | 'center'> = ['top', 'bottom', 'center'];

      positions.forEach((position) => {
        document.body.innerHTML = '';
        const config: NotificationConfig = {
          severity: 'info',
          message: `Position: ${position}`,
          position,
          autoHide: false,
        };

        const element = manager.show(config);
        // Should have CSS class for position
        // Note: actual styling comes from CSS, but we verify element is created
        expect(element).toBeTruthy();
        expect(element.className).toContain('notification');
      });
    });
  });

  describe('API: Convenience methods', () => {
    it('error() should create error notification', () => {
      manager.error('Something went wrong');

      const notification = document.querySelector('.notification-error');
      expect(notification).toBeTruthy();
      expect(notification?.textContent).toBe('Something went wrong');
    });

    it('warning() should create warning notification', () => {
      manager.warning('Please check your input');

      const notification = document.querySelector('.notification-warning');
      expect(notification).toBeTruthy();
      expect(notification?.textContent).toBe('Please check your input');
    });

    it('info() should create info notification', () => {
      manager.info('Did you know?');

      const notification = document.querySelector('.notification-info');
      expect(notification).toBeTruthy();
      expect(notification?.textContent).toBe('Did you know?');
    });

    it('success() should create success notification', () => {
      manager.success('Operation completed!');

      const notification = document.querySelector('.notification-success');
      expect(notification).toBeTruthy();
      expect(notification?.textContent).toBe('Operation completed!');
    });

    it('convenience methods should respect autoHide parameter', () => {
      manager.error('Persistent error', false);

      vi.advanceTimersByTime(TOOLTIP_AUTO_HIDE_DELAY + 1000);

      expect(document.querySelector('.notification-error')).toBeTruthy();
    });
  });

  describe('API: hide()', () => {
    it('should hide a specific notification', () => {
      const element = manager.info('To be hidden');

      expect(document.querySelector('.notification')).toBeTruthy();

      manager.hide(element);

      expect(document.querySelector('.notification')).toBeNull();
    });

    it('should remove element from active notifications tracking', () => {
      const element1 = manager.info('First', false);
      const element2 = manager.info('Second', false);

      expect(document.querySelectorAll('.notification').length).toBe(2);

      manager.hide(element1);

      expect(document.querySelectorAll('.notification').length).toBe(1);
      expect(document.body.contains(element2)).toBe(true);
    });
  });

  describe('API: hideAll()', () => {
    it('should hide all active notifications', () => {
      manager.info('First', false);
      manager.error('Second', false);
      manager.warning('Third', false);

      expect(document.querySelectorAll('.notification').length).toBe(3);

      manager.hideAll();

      expect(document.querySelectorAll('.notification').length).toBe(0);
    });

    it('should handle hideAll when no notifications are active', () => {
      // Should not throw
      expect(() => manager.hideAll()).not.toThrow();
    });
  });

  describe('Functionality: Multiple notifications', () => {
    it('should support multiple simultaneous notifications', () => {
      const notification1 = manager.info('First message', false);
      const notification2 = manager.error('Second message', false);
      const notification3 = manager.success('Third message', false);

      const notifications = document.querySelectorAll('.notification');
      expect(notifications.length).toBe(3);

      // Verify each notification exists
      expect(document.body.contains(notification1)).toBe(true);
      expect(document.body.contains(notification2)).toBe(true);
      expect(document.body.contains(notification3)).toBe(true);
    });

    it('should independently auto-hide multiple notifications', () => {
      manager.info('First'); // Uses default delay
      
      // Wait a bit, then create second notification
      vi.advanceTimersByTime(1000);
      manager.error('Second');

      // Fast forward to when first should be hidden
      vi.advanceTimersByTime(TOOLTIP_AUTO_HIDE_DELAY - 1000);
      
      // First should be gone, second still visible
      const remaining = document.querySelectorAll('.notification');
      expect(remaining.length).toBe(1);
      expect(remaining[0].textContent).toBe('Second');

      // Fast forward more to hide second
      vi.advanceTimersByTime(TOOLTIP_AUTO_HIDE_DELAY);
      expect(document.querySelectorAll('.notification').length).toBe(0);
    });
  });

  describe('Functionality: Notification lifecycle', () => {
    it('should properly clean up after auto-hide', () => {
      manager.info('Temporary');

      vi.advanceTimersByTime(TOOLTIP_AUTO_HIDE_DELAY);

      // Element should be removed from DOM
      expect(document.querySelector('.notification')).toBeNull();
      // Internal tracking should be cleaned up
      manager.hideAll(); // Should not throw or affect anything
      expect(document.querySelector('.notification')).toBeNull();
    });

    it('should handle rapid successive notifications', () => {
      // Create multiple notifications rapidly
      for (let i = 0; i < 5; i++) {
        manager.info(`Message ${i + 1}`, false);
      }

      expect(document.querySelectorAll('.notification').length).toBe(5);

      // Hide them one by one
      const notifications = document.querySelectorAll('.notification');
      notifications.forEach((notification) => {
        manager.hide(notification as HTMLElement);
      });

      expect(document.querySelectorAll('.notification').length).toBe(0);
    });
  });

  describe('Functionality: createErrorBanner()', () => {
    it('should create banner controller with show/hide methods', () => {
      const bannerElement = document.createElement('div');
      bannerElement.style.display = 'none';
      document.body.appendChild(bannerElement);

      const banner = createErrorBanner(bannerElement);

      expect(banner.show).toBeInstanceOf(Function);
      expect(banner.hide).toBeInstanceOf(Function);
    });

    it('should show banner with text content', () => {
      const bannerElement = document.createElement('div');
      bannerElement.style.display = 'none';
      document.body.appendChild(bannerElement);

      const banner = createErrorBanner(bannerElement);
      banner.show('Error occurred');

      expect(bannerElement.style.display).toBe('block');
      expect(bannerElement.textContent).toBe('Error occurred');
    });

    it('should show banner with HTML content when specified', () => {
      const bannerElement = document.createElement('div');
      bannerElement.style.display = 'none';
      document.body.appendChild(bannerElement);

      const banner = createErrorBanner(bannerElement);
      banner.show('<strong>Error</strong>', true);

      expect(bannerElement.style.display).toBe('block');
      expect(bannerElement.innerHTML).toBe('<strong>Error</strong>');
    });

    it('should hide banner', () => {
      const bannerElement = document.createElement('div');
      bannerElement.style.display = 'block';
      document.body.appendChild(bannerElement);

      const banner = createErrorBanner(bannerElement);
      banner.hide();

      expect(bannerElement.style.display).toBe('none');
    });

    it('should handle null banner element gracefully', () => {
      const banner = createErrorBanner(null);

      // Should not throw when calling methods
      expect(() => banner.show('Test')).not.toThrow();
      expect(() => banner.hide()).not.toThrow();
    });
  });

  describe('Functionality: Singleton pattern', () => {
    it('getNotificationManager should return same instance', () => {
      const manager1 = getNotificationManager();
      const manager2 = getNotificationManager();

      expect(manager1).toBe(manager2);
    });

    it('singleton should maintain state across calls', () => {
      const singleton = getNotificationManager();
      
      singleton.info('Test', false);
      
      const sameSingleton = getNotificationManager();
      sameSingleton.hideAll();
      
      expect(document.querySelector('.notification')).toBeNull();
    });
  });

  describe('Functionality: Default container support', () => {
    it('should use default container when provided', () => {
      const container = document.createElement('div');
      document.body.appendChild(container);

      const customManager = new NotificationManager(container);
      
      // Create notification - implementation may vary
      // This test verifies the constructor accepts container
      expect(customManager).toBeInstanceOf(NotificationManager);
    });
  });

  describe('Edge cases and error handling', () => {
    it('should handle hide() on already-removed element gracefully', () => {
      const element = manager.info('Test', false);
      
      // Manually remove from DOM (simulating external removal)
      element.remove();

      // Should not throw
      expect(() => manager.hide(element)).not.toThrow();
    });

    it('should handle empty message', () => {
      const element = manager.info('', false);
      
      expect(element.textContent).toBe('');
      expect(document.querySelector('.notification')).toBeTruthy();
    });

    it('should handle very long messages', () => {
      const longMessage = 'A'.repeat(1000);
      const element = manager.info(longMessage, false);
      
      expect(element.textContent).toBe(longMessage);
    });

    it('should handle special characters in messages', () => {
      const specialMessage = '<script>alert("xss")</script>';
      const element = manager.info(specialMessage, false);
      
      // Should be treated as text, not HTML
      expect(element.textContent).toBe(specialMessage);
      expect(element.innerHTML).toContain('&lt;'); // Should be escaped or treated as text
    });
  });
});

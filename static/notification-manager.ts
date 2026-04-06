/**
 * EntangledPdf Viewer - Notification Manager
 *
 * Centralized error and notification display system.
 * Refactored to use declarative CSS classes instead of inline styles.
 */

import { TOOLTIP_AUTO_HIDE_DELAY } from './constants';
import type { ErrorSeverity } from './types';

/**
 * Notification configuration
 */
export interface NotificationConfig {
  severity: ErrorSeverity;
  message: string;
  autoHide?: boolean;
  hideDelay?: number;
  position?: 'top' | 'bottom' | 'center';
  onClick?: () => void;
}

/**
 * Generate CSS class names for notification based on configuration
 * This follows a declarative pattern that maps easily to Lit's classMap directive
 */
function getNotificationClasses(config: NotificationConfig): string {
  const classes = ['notification', `notification-${config.severity}`];
  
  const position = config.position || 'center';
  classes.push(`notification-position-${position}`);
  
  return classes.join(' ');
}

/**
 * Create notification element from configuration
 * Pure function: transforms state (config) into DOM element
 */
function createNotificationElement(config: NotificationConfig): HTMLElement {
  const element = document.createElement('div');
  element.className = getNotificationClasses(config);
  element.textContent = config.message;
  
  // Click handler (preserved behavior)
  element.addEventListener('click', () => {
    config.onClick?.();
    element.remove();
  });
  
  return element;
}

/**
 * Notification manager for displaying messages to the user
 * Handles lifecycle (show, hide, auto-hide) while delegating rendering to pure functions
 */
export class NotificationManager {
  private activeNotifications: Set<HTMLElement> = new Set();
  private defaultContainer: HTMLElement | null = null;

  constructor(defaultContainer?: HTMLElement) {
    if (defaultContainer) {
      this.defaultContainer = defaultContainer;
    }
  }

  /**
   * Show a notification
   */
  show(config: NotificationConfig): HTMLElement {
    const element = createNotificationElement(config);
    
    const container = this.defaultContainer || document.body;
    container.appendChild(element);
    this.activeNotifications.add(element);

    if (config.autoHide !== false) {
      const delay = config.hideDelay ?? TOOLTIP_AUTO_HIDE_DELAY;
      setTimeout(() => {
        this.hide(element);
      }, delay);
    }

    return element;
  }

  /**
   * Hide a specific notification
   */
  hide(element: HTMLElement): void {
    element.remove();
    this.activeNotifications.delete(element);
  }

  /**
   * Hide all active notifications
   */
  hideAll(): void {
    this.activeNotifications.forEach(el => el.remove());
    this.activeNotifications.clear();
  }

  /**
   * Show an error message
   */
  error(message: string, autoHide = true): HTMLElement {
    return this.show({
      severity: 'error',
      message,
      autoHide,
      position: 'top',
    });
  }

  /**
   * Show a warning message
   */
  warning(message: string, autoHide = true): HTMLElement {
    return this.show({
      severity: 'warning',
      message,
      autoHide,
      position: 'top',
    });
  }

  /**
   * Show an info message
   */
  info(message: string, autoHide = true): HTMLElement {
    return this.show({
      severity: 'info',
      message,
      autoHide,
      position: 'top',
    });
  }

  /**
   * Show a success message
   */
  success(message: string, autoHide = true): HTMLElement {
    return this.show({
      severity: 'success',
      message,
      autoHide,
      position: 'top',
    });
  }
}

/**
 * Create error banner functionality
 * @param bannerElement - The error banner DOM element
 */
export function createErrorBanner(bannerElement: HTMLElement | null): {
  show: (message: string, isHtml?: boolean) => void;
  hide: () => void;
} {
  return {
    show: (message: string, isHtml = false) => {
      if (bannerElement) {
        if (isHtml) {
          bannerElement.innerHTML = message;
        } else {
          bannerElement.textContent = message;
        }
        bannerElement.style.display = 'block';
      }
    },
    hide: () => {
      if (bannerElement) {
        bannerElement.style.display = 'none';
      }
    },
  };
}

// Singleton instance for global notifications
let globalNotificationManager: NotificationManager | null = null;

/**
 * Get or create the global notification manager
 */
export function getNotificationManager(): NotificationManager {
  if (!globalNotificationManager) {
    globalNotificationManager = new NotificationManager();
  }
  return globalNotificationManager;
}

/**
 * PdfServer Viewer - Notification Manager
 *
 * Centralized error and notification display system.
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
 * Notification manager for displaying messages to the user
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
    const element = this.createNotificationElement(config);
    document.body.appendChild(element);
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

  /**
   * Create the notification DOM element
   */
  private createNotificationElement(config: NotificationConfig): HTMLElement {
    const element = document.createElement('div');
    element.className = `notification notification-${config.severity}`;
    element.textContent = config.message;

    // Base styles
    const baseStyles: Record<string, string> = {
      position: 'fixed',
      left: '50%',
      transform: 'translateX(-50%)',
      padding: '12px 20px',
      borderRadius: '6px',
      fontSize: '14px',
      fontFamily: 'sans-serif',
      zIndex: '10001',
      boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
      textAlign: 'center',
      maxWidth: '400px',
      userSelect: 'none',
      webkitUserSelect: 'none',
      cursor: config.onClick ? 'pointer' : 'default',
    };

    // Position
    if (config.position === 'top') {
      baseStyles.top = '20px';
    } else if (config.position === 'bottom') {
      baseStyles.bottom = '20px';
    } else {
      baseStyles.top = '50%';
      baseStyles.transform = 'translate(-50%, -50%)';
    }

    // Severity-specific styles
    const severityStyles: Record<ErrorSeverity, Record<string, string>> = {
      error: {
        background: 'rgba(239, 68, 68, 0.95)',
        color: 'white',
      },
      warning: {
        background: 'rgba(234, 179, 8, 0.95)',
        color: 'rgb(66, 32, 6)',
      },
      info: {
        background: 'rgba(59, 130, 246, 0.95)',
        color: 'white',
      },
      success: {
        background: 'rgba(34, 197, 94, 0.95)',
        color: 'white',
      },
    };

    // Apply styles
    Object.assign(element.style, baseStyles, severityStyles[config.severity]);

    // Click handler
    if (config.onClick) {
      element.addEventListener('click', () => {
        config.onClick!();
        this.hide(element);
      });
    } else {
      element.addEventListener('click', () => {
        this.hide(element);
      });
    }

    return element;
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

import { defineConfig } from 'vitest/config';
import { playwright } from '@vitest/browser-playwright';

export default defineConfig({
  test: {
    projects: [
      {
        test: {
          name: 'unit',
          environment: 'happy-dom',
          globals: true,
          setupFiles: ['./tests/js/setup.ts'],
          include: ['tests/js/**/*.test.ts'],
          exclude: ['tests/js/browser/**'],
          coverage: {
            reporter: ['text', 'json', 'html'],
            include: ['static/*.ts'],
            exclude: ['static/viewer.ts']
          }
        },
        resolve: {
          alias: {
            '@static': '/static'
          }
        }
      },
      {
        test: {
          name: 'browser',
          browser: {
            enabled: true,
            provider: playwright(),
            instances: [
              { browser: 'chromium', headless: true }
            ]
          },
          include: ['tests/js/browser/**/*.test.ts'],
          testTimeout: 30000
        }
      }
    ]
  }
});

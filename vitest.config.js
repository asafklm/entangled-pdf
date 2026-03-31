import { defineConfig } from 'vitest/config';

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
          exclude: ['tests/js/browser/**', 'tests/e2e/**'],
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
      }
    ]
  }
});

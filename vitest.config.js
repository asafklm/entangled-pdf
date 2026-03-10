/** @type {import('vitest/config').UserConfig} */
export default {
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./tests/js/setup.ts'],
    include: ['tests/js/**/*.test.ts'],
    coverage: {
      reporter: ['text', 'json', 'html'],
      include: ['static/*.ts'],
      exclude: ['static/viewer.ts'] // Exclude main file - requires complex pdfjs mock
    }
  },
  resolve: {
    alias: {
      '@static': '/static'
    }
  }
};

/** @type {import('vitest/config').UserConfig} */
export default {
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./tests/js/setup.js'],
    include: ['tests/js/**/*.test.js'],
    coverage: {
      reporter: ['text', 'json', 'html'],
      include: ['static/*.js'],
      exclude: ['static/viewer.js'] // Exclude main file until refactored
    }
  },
  resolve: {
    alias: {
      '@static': '/static'
    }
  }
};

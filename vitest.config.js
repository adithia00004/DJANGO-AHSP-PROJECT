import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'happy-dom',
    include: [
      'detail_project/static/detail_project/js/**/*.test.js',
    ],
    coverage: {
      reporter: ['text', 'lcov'],
    },
  },
});

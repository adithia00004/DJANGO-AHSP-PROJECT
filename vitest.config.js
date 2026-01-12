import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  resolve: {
    alias: {
      '@modules': path.resolve(__dirname, 'detail_project/static/detail_project/js/src/modules'),
    },
  },
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

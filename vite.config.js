import { defineConfig } from 'vite';
import path from 'path';
import { visualizer } from 'rollup-plugin-visualizer';

const dropConsoleLogs = process.env.DROP_JADWAL_CONSOLE_LOGS === 'true';

export default defineConfig({
  // Base public path
  base: '/static/detail_project/dist/',

  // Build configuration
  build: {
    // Output directory (Django static files)
    outDir: './detail_project/static/detail_project/dist',

    // Generate manifest for Django integration
    manifest: true,

    // Clean output directory before build
    emptyOutDir: true,

    // Rollup options
    rollupOptions: {
      input: {
        // Main entry point for jadwal kegiatan
        'jadwal-kegiatan': path.resolve(
          __dirname,
          'detail_project/static/detail_project/js/src/jadwal_kegiatan_app.js'
        ),
      },

      output: {
        // Manual chunks for better caching
        manualChunks: {
          // AG Grid vendor chunk
          'vendor-ag-grid': ['ag-grid-community'],

          // Export libraries chunk
          'vendor-export': ['xlsx', 'jspdf', 'html2canvas'],

          // App-specific chunks
          'grid-modules': [
            path.resolve(
              __dirname,
              'detail_project/static/detail_project/js/src/modules/grid/ag-grid-setup.js'
            ),
            path.resolve(
              __dirname,
              'detail_project/static/detail_project/js/src/modules/grid/column-definitions.js'
            ),
            path.resolve(
              __dirname,
              'detail_project/static/detail_project/js/src/modules/grid/grid-event-handlers.js'
            ),
          ],
          'chart-modules': [
            path.resolve(
              __dirname,
              'detail_project/static/detail_project/js/src/modules/gantt/frappe-gantt-setup.js'
            ),
            path.resolve(
              __dirname,
              'detail_project/static/detail_project/js/src/modules/kurva-s/echarts-setup.js'
            ),
          ],
        },

        // Asset file names
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name.split('.');
          const ext = info[info.length - 1];
          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(ext)) {
            return `assets/images/[name]-[hash][extname]`;
          } else if (/woff2?|ttf|eot/i.test(ext)) {
            return `assets/fonts/[name]-[hash][extname]`;
          }
          return `assets/[name]-[hash][extname]`;
        },

        // Chunk file names
        chunkFileNames: 'assets/js/[name]-[hash].js',

        // Entry file names
        entryFileNames: 'assets/js/[name]-[hash].js',
      },
    },

    // Minification
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: dropConsoleLogs,
        drop_debugger: dropConsoleLogs,
      },
    },

    // Source maps for production debugging
    sourcemap: true,

    // Target modern browsers
    target: 'es2015',

    // CSS code splitting
    cssCodeSplit: true,
  },

  // Dev server configuration
  server: {
    host: 'localhost',
    port: 5173,
    strictPort: false,

    // CORS for Django dev server
    cors: true,

    // Proxy API requests to Django
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },

    // Watch options
    watch: {
      usePolling: false,
    },
  },

  // Resolve aliases
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './detail_project/static/detail_project/js/src'),
      '@modules': path.resolve(__dirname, './detail_project/static/detail_project/js/src/modules'),
      '@shared': path.resolve(__dirname, './detail_project/static/detail_project/js/src/modules/shared'),
      '@core': path.resolve(__dirname, './detail_project/static/detail_project/js/core'),
    },
  },

  // Optimizations
  optimizeDeps: {
    include: ['ag-grid-community', 'xlsx', 'jspdf', 'html2canvas'],
  },

  // Define environment variables
  define: {
    __DEV__: JSON.stringify(process.env.NODE_ENV !== 'production'),
  },

  plugins: [
    visualizer({
      filename: './detail_project/static/detail_project/dist/stats.html',
      open: false,
      gzipSize: true,
    }),
  ],
});

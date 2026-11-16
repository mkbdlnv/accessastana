import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// The backend (FastAPI) serves its routes at the root ("/cities", ...).
// The browser always talks to "/api/..."; in development Vite forwards these
// requests to the API on port 8000 and strips the "/api" prefix
// (in production nginx does the same, see nginx.conf).
export default defineConfig({
  plugins: [react()],
  build: {
    // MapLibre + deck.gl are ~2 MB minified; a single chunk is acceptable here.
    chunkSizeWarningLimit: 3000,
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});

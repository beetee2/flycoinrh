import { defineConfig } from 'vitest/config';

const apiPort = process.env.FLYJAM_API_PORT ?? '8765';
if (!/^\d{4,5}$/.test(apiPort) || Number(apiPort) > 65535 || Number(apiPort) < 1024) {
  throw new Error('FLYJAM_API_PORT must be a local port between 1024 and 65535.');
}
// Keep the browser Host header: the API compares it with Origin for control
// requests, including CSRF bootstrap/leases. Never rewrite or allow all origins.
const liveProxy = { target: `http://127.0.0.1:${apiPort}`, changeOrigin: false };

export default defineConfig({
  plugins: [{
    name: 'flyjam-application-route',
    configureServer(server) {
      // Vite otherwise resolves /live to the unrelated upstream live.html.
      // Rewrite only the application entry, retaining the browser route.
      server.middlewares.use((request, _response, next) => {
        if (request.url === '/live' || request.url?.startsWith('/live?')) request.url = '/index.html';
        next();
      });
    },
  }],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': liveProxy,
      '/health': liveProxy,
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.{ts,tsx}'],
    passWithNoTests: false,
    reporters: ['default', 'junit'],
    outputFile: { junit: process.env.VITEST_JUNIT_PATH ?? '../artifacts/milestones/01/ui-junit.xml' },
  },
});

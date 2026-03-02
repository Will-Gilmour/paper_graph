import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: 'https://mylitsearch-api.loca.lt',        // already needed for external access
    port: 3000,
    strictPort: true,       // fail if 3000 is busy
    cors: true,
    // allow your tunnel hostname (or '*' for any)
    allowedHosts: [
      'mylitsearch.loca.lt',
      "monkey.tail847ee7.ts.net"
      // you can add more, e.g. 'abcd.loca.lt'
    ],
    proxy: {
      // any request starting with /export or /find etc
      '/api': 'http://backend:8000',      // NEW: Pipeline API routes
      '/export': 'http://backend:8000',
      '/find':   'http://backend:8000',
      '/ego':    'http://backend:8000',
      '/clusters': 'http://backend:8000',
      '/labels': 'http://backend:8000',
      '/paper': 'http://backend:8000',
      '/reading_list': 'http://backend:8000',
    }
  },
});

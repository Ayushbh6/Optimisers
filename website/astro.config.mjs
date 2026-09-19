import { defineConfig } from 'astro/config';
const vercelHost = process.env.VERCEL_PROJECT_PRODUCTION_URL || process.env.VERCEL_URL;
const site = process.env.PUBLIC_SITE_URL || (vercelHost ? `https://${vercelHost}` : undefined);
export default defineConfig({
  site,
  output: 'static',
  devToolbar: { enabled: false },
  vite: {
    server: {
      proxy: {
        '/api/basket': {
          target: 'http://127.0.0.1:8765',
          rewrite: path => path.replace(/^\/api\/basket/, ''),
        },
        '/api/stock': {
          target: 'http://127.0.0.1:8767',
          rewrite: path => path.replace(/^\/api\/stock/, ''),
        },
      },
    },
  },
});

import { cp, mkdir, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const website = fileURLToPath(new URL('../', import.meta.url));
const repo = fileURLToPath(new URL('../../', import.meta.url));
const destination = `${website}public/demos`;

await rm(destination, { recursive: true, force: true });
await mkdir(`${destination}/basket/assets`, { recursive: true });
await mkdir(`${destination}/stock/assets`, { recursive: true });

for (const [source, target] of [
  ['src/supplier_basket/web/index.html', 'basket/index.html'],
  ['src/supplier_basket/web/style.css', 'basket/assets/style.css'],
  ['src/supplier_basket/web/app.js', 'basket/assets/app.js'],
  ['src/stock_watch/web/index.html', 'stock/index.html'],
  ['src/stock_watch/web/style.css', 'stock/assets/style.css'],
  ['src/stock_watch/web/app.js', 'stock/assets/app.js'],
]) {
  await cp(`${repo}${source}`, `${destination}/${target}`);
}

console.log('Prepared same-origin demo assets.');

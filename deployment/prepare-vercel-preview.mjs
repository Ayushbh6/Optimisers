import { cp, mkdir, readFile, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const repo = fileURLToPath(new URL('../', import.meta.url));
const stage = `${repo}.vercel-preview`;
const keep = source => !source.includes('__pycache__') && !source.endsWith('.pyc');

await rm(stage, { recursive: true, force: true });
await mkdir(stage, { recursive: true });

for (const [source, target] of [
  ['website/dist', 'public'],
  ['api', 'api'],
  ['src/supplier_basket', 'src/supplier_basket'],
  ['src/stock_watch', 'src/stock_watch'],
  ['artifacts/supplier-basket-showcase', 'artifacts/supplier-basket-showcase'],
  ['artifacts/stock-watch-showcase', 'artifacts/stock-watch-showcase'],
]) {
  await cp(`${repo}${source}`, `${stage}/${target}`, { recursive: true, filter: keep });
}

await cp(`${repo}deployment/vercel-preview.json`, `${stage}/vercel.json`);
await cp(`${repo}deployment/vercel-preview.pyproject.toml`, `${stage}/pyproject.toml`);

const config = JSON.parse(await readFile(`${stage}/vercel.json`, 'utf8'));
if (!config.headers?.length) throw new Error('Preview security headers are missing');

console.log(`Prepared minimal Vercel preview bundle at ${stage}`);

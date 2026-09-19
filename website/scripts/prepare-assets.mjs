import sharp from 'sharp';
import { mkdir, copyFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../', import.meta.url));
await mkdir(`${root}public/images`, { recursive: true });
await mkdir(`${root}public/fonts`, { recursive: true });
const images = [
  ['../docs/references/main-hero.png', 'hero', 1920],
  ['../docs/references/Me.png', 'ayush', 800],
  ['../docs/references/Max-image.jpeg', 'max', 800],
  ['../docs/references/basket-demo.png', 'basket', 1200],
  ['../docs/references/stock-demo.png', 'stock', 1200],
];
for (const [source, name, width] of images) {
  await sharp(`${root}${source}`).rotate().resize({ width, withoutEnlargement: true }).webp({ quality: 86 }).toFile(`${root}public/images/${name}.webp`);
}
await copyFile(`${root}node_modules/@fontsource-variable/manrope/files/manrope-latin-wght-normal.woff2`, `${root}public/fonts/manrope-latin.woff2`);
await copyFile(`${root}node_modules/@fontsource-variable/manrope/LICENSE`, `${root}public/fonts/LICENSE-Manrope.txt`);
console.log('Prepared website derivatives; source images unchanged.');

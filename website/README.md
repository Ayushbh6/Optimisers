# Axis studio website

Astro, TypeScript, custom CSS and locally hosted Manrope (OFL). Static output, no database, analytics, paid dependencies or external font requests.

## Run

From this directory: `npm ci`, `npm run dev`. Opens on port 4321, leaving port 3000 alone.

Run the two demos from the repository root in separate terminals:

```sh
python3 -m src.supplier_basket.webapp --port 8765
python3 -m src.stock_watch.webapp --port 8767
```

`npm run check` checks Astro/TypeScript; `npm run build` produces `dist/`; `npm run preview` serves that build. Image derivatives can be regenerated with `node scripts/prepare-assets.mjs`. Original image assets remain in `docs/references`. Private CV source files are local-only, Git-ignored, and never published in the site.

## Content and design

Latest user direction supersedes the original scrolling page: four routes, Home / Work / About / Contact, in a fixed header/footer frame. Desktop composition fits a normal laptop viewport; smaller screens and text zoom can scroll the middle. Native links support history, deep links, keyboards and disabled JavaScript. Reduced-motion preferences are respected.

Working studio title: **Axis**. The name is provisional until availability and legal checks are complete. Founder descriptions, GitHub profiles and email addresses derive from the supplied CVs and project records. Both hold an MSc in Quantitative Finance; unsupported degree claims in older website documents are not repeated.

The hero uses `docs/references/main-hero.png`; `Idea.png` is the visual composition reference. All colours originate in the website: charcoal, ivory, restrained amber. Both demo styles are aligned with it without changing geometry or numerical rules. Screenshots must be refreshed after demo visual changes.

## Hosting boundary

This version is deployment-ready but remains local. A single Vercel preview project can serve the Astro site and the two Python demo adapters in `/api`. The demos are copied under `/demos/` at build time and remain same-origin, so navigation, downloads and the return-to-work path do not depend on localhost ports. `deployment/prepare-vercel-preview.mjs` creates a minimal `.vercel-preview/` bundle without the repository's heavy research dependencies; deploy that directory, not the repository root. Set `PUBLIC_SITE_URL` to the preview URL before the final build (Vercel system URL variables are also supported). The Vercel Hobby plan is suitable only for the short, non-commercial review agreed by the founders; move to a compliant plan before client promotion. Final name availability and publication review remain open.

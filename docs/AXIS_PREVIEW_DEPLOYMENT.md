# Axis preview deployment

Status: ready for a short internal Vercel preview; nothing has been uploaded.

## Visitor journey

1. Home, Work, About and Contact are static Astro pages.
2. Work opens each demo in the same tab under `/demos/`.
3. Each demo keeps a visible `Axis / Work` return action; the browser Back action also works.
4. Demo requests stay on the same origin under `/api/basket/` and `/api/stock/`.
5. CSV downloads are regenerated from the selected synthetic case and its explicitly confirmed issue.

## Backend boundary

The preview has no account, database, uploaded customer data, cookies or analytics. One dependency-free WSGI entrypoint exposes both demo APIs, and both demos rebuild their small synthetic case on every request. This is deliberate: Vercel may execute consecutive requests on different function instances, so correctness does not depend on server memory.

The generated preview bundle excludes the repository's research dependency file entirely. The two demo APIs use the Python standard library and include only their source code plus the two compact synthetic case-study directories.

## Prepare—but do not deploy

```sh
cd website
npm ci
PUBLIC_SITE_URL=https://YOUR-PREVIEW-URL.vercel.app npm run build
cd ..
node deployment/prepare-vercel-preview.mjs
```

Inspect `.vercel-preview/`, then deploy that directory only when approved. The preview publishes `robots.txt` with `Disallow: /`; remove that restriction during a later public launch review.

The bundle can be tested without linking or uploading a Vercel project:

```sh
cd .vercel-preview
npx --yes vercel@latest dev -L --listen 127.0.0.1:4322
```

## Before client promotion

- clear the Axis name and any eventual domain;
- replace the internal-preview hosting arrangement with a commercially compliant plan;
- change `robots.txt` only after the publication review;
- rerun the website, API, download and phone checks against the deployed URL.

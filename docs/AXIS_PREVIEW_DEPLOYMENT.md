# Axis preview deployment

Status: deployed as the short internal showcase at <https://axis-software-demo.vercel.app> on 19 September 2026.

## Visitor journey

1. Home, Work, About and Contact are static Astro pages.
2. Work opens each demo in the same tab under `/demos/`.
3. Each demo keeps a visible `Axis / Work` return action; the browser Back action also works.
4. Demo requests stay on the same origin under `/api/basket/` and `/api/stock/`.
5. CSV downloads are regenerated from the selected synthetic case and its explicitly confirmed issue.

## Backend boundary

The preview has no account, database, uploaded customer data, cookies or analytics. One dependency-free WSGI entrypoint exposes both demo APIs, and both demos rebuild their small synthetic case on every request. This is deliberate: Vercel may execute consecutive requests on different function instances, so correctness does not depend on server memory.

The generated preview bundle excludes the repository's research dependency file entirely. The two demo APIs use the Python standard library and include only their source code plus the two compact synthetic case-study directories.

## Repeat the manual deployment

```sh
cd website
npm ci
PUBLIC_SITE_URL=https://axis-software-demo.vercel.app npm run build
cd ..
node deployment/prepare-vercel-preview.mjs
```

Inspect `.vercel-preview/`, link it only to the `axis-software-demo` Vercel project, then deploy that directory. The preview publishes `robots.txt` with `Disallow: /`; remove that restriction during a later public launch review.

The bundle can be tested without uploading a Vercel deployment:

```sh
cd .vercel-preview
npx --yes vercel@latest dev -L --listen 127.0.0.1:4322
```

## Before client promotion

- clear the Axis name and any eventual domain;
- replace the internal-preview hosting arrangement with a commercially compliant plan;
- change `robots.txt` only after the publication review;
- rerun the website, API, download and phone checks against the deployed URL.

## Live verification

The production smoke on 19 September 2026 verified Home, Work, About, Contact, both embedded demos, both API health/example routes, both complete recommendation journeys, all three CSV exports, the branded 404 and the security headers. The project is not connected for automatic Git deployments; releases remain explicit through the minimal staging directory.

The later iPhone contact-arrow patch replaced the Unicode northeast arrow with a shared SVG so Safari cannot substitute emoji artwork. After the manual production redeployment, 390×844 checks passed on About and Contact with no horizontal overflow; the static routes, both demo entries, both API health routes, branded 404, `nosniff` header and blocking `robots.txt` were rechecked live.

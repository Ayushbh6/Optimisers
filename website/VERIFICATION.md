# Axis preview verification — 19 September 2026

- `npm run check`: 0 errors, warnings or hints.
- `npm run build`: 5 static routes built, including the branded 404 page.
- `npm audit`: 0 reported vulnerabilities.
- Full Python suite: 207 tests and 9 subtests passed, including both showcase engines and the stateless preview adapters.
- iPhone QA: 375×667, 390×844 and 430×932 across Home, Work, About, Contact, Supplier Basket Review and Stock Watch. No horizontal overflow on any checked route.
- Phone interaction: fixed header and footer remain pinned; only the middle workspace scrolls. Primary mobile navigation and demo controls provide 44px touch height/minimum targets.
- Complete Supplier Basket flow: example loaded, source issue confirmed, recommendation calculated, supplier CSV returned, and `Axis / Work` returned to the portfolio.
- Complete Stock Watch flow: example loaded, source issue confirmed, recommendation calculated, both CSVs returned, and fixed-screen behaviour retained.
- Backend preflight: both Vercel Python handlers answered example and review requests from fresh processes. Calculations do not rely on a previous function instance retaining memory.
- Minimal preview bundle: `.vercel-preview/` generated at approximately 3MB with no research-library requirements. Vercel CLI 59.23.2 served the site, both APIs, both recommendation flows and all three CSV exports locally with no project link or upload.
- Working name: Axis. It remains provisional pending availability/legal checks. Private CV PDFs and phone numbers are not published.
- Visual evidence was inspected at all declared phone sizes during the release pass. Reproducible browser captures were removed during the 19 September workspace cleanup; this compact verification record is retained instead.
- Remaining publication work: approve the preview deployment, build once with the final preview URL, deploy `.vercel-preview/`, and repeat smoke tests against that URL. Before client promotion, use commercially compliant hosting and complete the name/publication review.

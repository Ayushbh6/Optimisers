# Storage cleanup — 19 September 2026

## Outcome

The working copy was reduced from approximately **301 MB to 66 MB**, including approximately **55 MB of Git history**. The removable local material therefore released approximately **235 MB** without deleting source, tests, retained evidence or required website assets.

## Removed

- `website/node_modules/` — reproducible from `website/package-lock.json`;
- `website/dist/`, `website/.astro/` and generated `website/public/demos/`;
- `.vercel/` and `.vercel-preview/` — local runtime and reproducible preview staging;
- `.playwright-cli/`, `output/`, pytest caches, Python bytecode and macOS metadata;
- redundant browser screenshots after the final phone and end-to-end checks passed.

The three development servers were stopped before their local dependency and preview files were removed.

## Retained

- all application, API, demo, research and test source;
- the compact synthetic showcase records and release contracts under `artifacts/`;
- the retained negative distributor-research evidence;
- the original hero and founder images plus two compact demo-thumbnail sources;
- all authoritative implementation, claim-boundary and deployment documents;
- Git history.

The two private CV PDFs remain local-only and are explicitly ignored. They are not part of the commit or website build.

## Dependency contracts

- `requirements.in` lists the direct Python dependencies;
- `requirements.txt` is regenerated as a Python 3.12 lock with `uv pip compile`;
- `website/package.json` declares every direct website dependency, including `sharp` for asset preparation;
- `website/package-lock.json` reproduces the verified Node install;
- the Vercel preview API remains dependency-free through `deployment/vercel-preview.pyproject.toml`.

## Verification before cleanup

- Python: **207 tests and 9 subtests passed**;
- Astro check: **0 errors, 0 warnings, 0 hints**;
- Astro production build: **5 routes built**;
- npm audit: **0 reported vulnerabilities**;
- the preview staging script regenerated the approximately 3 MB Vercel bundle and the bundle contained no CV, environment or key files.

Generated installs and outputs were removed only after these checks passed. Recreate them from the retained locks and scripts when development resumes.

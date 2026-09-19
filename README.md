# Axis inventory decision demos

Axis is a provisional studio website with two working, synthetic inventory-management demonstrations:

- **Supplier Basket Review** asks whether this week's supplier order can use less cash without reducing booked customer deliveries.
- **Stock Watch** identifies what may run out, what may expire, and what the buyer should change this week.

Both demos start from deliberately messy example exports, reconcile the records, replay physical inventory movements, and explain the resulting action. They are technical case studies—not client results or realised-savings claims.

## Repository map

```text
website/                    Astro portfolio and generated static site
api/                        dependency-free preview API entrypoint
src/supplier_basket/        supplier-basket import, replay and decision logic
src/stock_watch/            lot-level expiry and purchasing logic
artifacts/*-showcase/       compact synthetic inputs, contracts and evidence
docs/showcase/              Supplier Basket phase records
docs/slow-stock-expiry/     Stock Watch phase records
src/replenishment/          retained exact-replay purchasing research
src/distributor_research/   retained negative research and safeguards
tests/                      behavioural and release-contract tests
```

The earlier retail-optimiser research remains in the repository as honest historical evidence. Its large raw CSVs and generated tables are intentionally not retained in the working tree; see `docs/STORAGE_CLEANUP_2026-09-18.md`.

## Run the website

```sh
cd website
npm ci
npm run dev
```

Open <http://127.0.0.1:4321/>. The Astro development server proxies the two local demo APIs when they are running separately.

## Run the demos directly

```sh
python -m src.supplier_basket.webapp --host 127.0.0.1 --port 8765
python -m src.stock_watch.webapp --host 127.0.0.1 --port 8767
```

Both demo engines use the Python standard library. The broader research and test suite uses the pinned environment below.

## Verify the repository

```sh
uv run --python 3.12 --with-requirements requirements.txt python -m pytest -q
cd website
npm ci
npm run check
npm run build
npm audit
```

`requirements.in` records the direct Python dependencies; `requirements.txt` is the reproducible compiled lock. `website/package.json` and `website/package-lock.json` are the corresponding Node contracts.

## Preview deployment

The Vercel preview is prepared but not deployed. Follow `docs/AXIS_PREVIEW_DEPLOYMENT.md` only after approval. The generated `.vercel-preview/` directory, dependency installs, browser screenshots, caches and private CV source files are deliberately excluded from Git.

## Honest boundary

- All showcase records are labelled synthetic examples.
- The site makes no realised-savings claim.
- Fresh evaluation seeds from the stopped optimiser research remain unopened.
- Axis is a working name pending availability and legal review.

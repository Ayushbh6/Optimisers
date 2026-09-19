# Distributor demo: controlled iteration protocol

Authorised 15 September 2026. The end-to-end goal is a defensible purchasing product, including the approved buyer workflow after its numerical gate passes. This supplements the approved implementation plan; its thresholds and original retail plan remain unchanged.

## Preserve the evidence

Frozen v1 failed. Its exact numerical sources are retained in `artifacts/distributor-demo/iteration-v2/frozen-v1-source.tar.gz`, with original hashes; previous databases, reports and negative outcomes are preserved. Current source revisions belong to v2 and cannot be described as the original frozen implementation. The original generator recipe and retained default data remain unchanged.

## Development loop

Diagnose an observed failure → write a test or measurable hypothesis → make one coherent revision → pass correctness checks → run all 18 development cases → inspect all outcomes and customer/product harm → choose the next justified revision.

Initial batch: correct the baseline fallback/projection inconsistency. Saved v1 journals show that 13 of 30 cases first diverged while selecting the baseline fallback. The nested projection treated estimated demand as bookings and regenerated fractional forecast remainders. A separate safeguard excludes past estimated due dates; the review distinguishes that boundary check from the two reproduced defects. Correct the common comparison implementation and rerun both methods; do not weaken the comparison to improve a score.

Further candidates require evidence from that corrected batch. Two hypotheses to investigate are inadequate protection against demand variability and moving purchases into the future to reduce projected inventory while failing to protect today's uncertain deliveries. Neither is yet established as the cause of all observed losses. Do not implement arbitrary parameter sweeps or choose by scenario name, seed or future records.

Each batch records source hashes, hypothesis, settings, all cases and input manifests. A restart resumes identical unfinished work only; changed code or settings require a new output directory. Completed database copies are deleted only after retaining regeneration and outcome evidence. Keep at most four isolated workers. No unattended code-writing process or automatically repeated final examinations.

After at most three coherent development batches, review progress explicitly. Continue if there is a supported next correction; otherwise record the unresolved modelling decision rather than silently loop without limit. This review does not mark the end-to-end goal achieved.

## Evaluation boundary

Original 18 development cases are for iteration. The 30 formerly reserved cases are now known regression evidence, never unseen proof. Do not tune on a newly opened final examination.

Reserve these new seeds now, before generating outcomes: **91301, 91302, 91303, 91304, 91305**, across the same six families. They use the unchanged business recipe. No regeneration or replacement because a result is unfavourable. The private evaluator must enforce the new version's frozen source/settings contract before materialisation. Merely selecting seed numbers does not authorise generating them now.

Open the new 30-case examination only after a selected candidate is frozen and all development and known-case correctness/regression reviews are complete. Apply the original numerical thresholds and evaluate the same claimed families under supplier-delay and freshness sensitivities. Record every opening and failure. A failed final examination requires an explicit research review; the runner must not draw another set automatically.

## Product completion

After the numerical gate, implement the already approved FastAPI and React purchasing workflow, imports and correction trails, explainable proposals, locked edits, checked exports, evidence page and portable local/container launch. Verify browser interaction, accessibility and declared concurrent capacity. Deployment and external outreach remain separate actions.

A synthetic evaluation can establish bounded decision capability. The goal cannot guarantee that a customer will pay; buyer validation remains a separate real-world outcome.

## Third development candidate: historical order patterns

The third candidate retains the shared eight-week mean forecast and adds four fixed, nonoverlapping 28-day historical request patterns as stress views. Each uses the original requested quantity, customer and weekday, including requests that were not fulfilled. Historical requests booked before the analogous decision boundary are omitted from the hypothetical future stream; today's actual bookings remain separate. Bookings replace the product/date forecast remainder rather than being added twice. Only declared complete history windows are eligible; covered empty windows remain empty. No pattern is selected because it gives a favourable purchasing result, and no probability weights or hidden future demand are used.

A joint model chooses the same dated purchase schedule across the nominal view and these patterns, requiring at least the baseline's projected service in each. Whole-line customer rules are represented for the historical patterns. Shared physical replay remains authoritative: one bounded model correction is allowed, and a proposal that still misses a target is rejected. Existing lower/higher historical-error checks and booked-fulfilment checks remain part of recommendation selection. This is a development hypothesis about request structure, not evidence that replaying history predicts the future.

The 60-day incoming freshness assumption, baseline safety cover, three-second per-solve allowance, data recipe and release thresholds remain unchanged. The first ordinary operational snapshot retained the baseline after rejecting the joint proposal; it took 11.5 seconds for the complete planning call. The five-second initial-response target remains a separate unresolved product requirement.

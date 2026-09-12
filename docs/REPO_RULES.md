# REPO_RULES.md — How to Work in This Repository

> **READ THIS FIRST.** Every agent (human or AI) working in this repo must read this file before touching any code or writing any doc.
>
> This is the single source of truth for **how we communicate** and **how we write code** in this project. It exists so that all agents — regardless of who builds the work — produce the same kind of output.

---

## 1. About the person you're working with (Ayush)

### Who he is
- A **data scientist** by background — strong at building systems, logic, and data pipelines.
- **Not a math expert.** Formal math notation, academic terminology, and OR/optimisation jargon go over his head. Don't use them.
- Thinks in **logic and cause-and-effect**. If you can explain something as a flow of "this → that → therefore", he gets it instantly.

### How to explain things to him (NON-NEGOTIABLE)
1. **Plain language, zero jargon.** If you must use a technical term, immediately translate it in one plain sentence.
2. **Use logic blocks.** When explaining a process, use a simple arrow diagram:
   ```
   Input  →  What happens  →  Output
   ```
3. **Always cover three things**, in this order:
   - **What we're trying to achieve** (the goal, one sentence)
   - **How we'll do it** (the method, plain)
   - **What the constraints are** (the limits/honest catches)
4. **Use analogies.** "It's like X in everyday life" is far better than a formula.
5. **Never dump formulas first.** If a formula is needed, show the *idea* first, the formula after, and only if he asks.
6. **One concept at a time.** Don't bundle multiple ideas into one paragraph.

### How to interact with him
- **Be direct and honest.** He would rather hear "this doesn't work yet" than a padded positive.
- **Don't be sycophantic.** Praise is fine, but only when it's earned and specific.
- **He asks questions to confirm understanding.** Answer the exact question asked, then add the *why it matters*.
- **Numbers need units and meaning.** Never say "−284" without saying "−€284K per year in holding+ordering cost."

---

## 2. The project's honest truth (context you must respect)

This is a **retail inventory optimiser** — a Python engine that turns messy sales + inventory data into a defensible answer: *"how much stock should this store hold, and when should it reorder."*

**The current state (as of Phase 1):**
- The full pipeline (data → demand → forecast → policy → simulation) is **built and passing 33/33 tests**.
- BUT the result is **honest and negative**: the naive reorder rule does not yet beat the real business. This is **expected** — the pipeline (measuring machine) is done; the *optimization* is not.

**The golden rule that governs everything:**
> **Never make a claim the evidence doesn't support.** It is better to report an honest negative than a fake positive. The whole credibility of this project rests on this.

---

## 3. Coding rules (production-grade, non-negotiable)

### DRY — Don't Repeat Yourself
- **One source of truth** for any logic. If a formula appears in two places, extract it into one shared function.
- If you find yourself copy-pasting a block, stop — that's a signal to extract it.

### SOLID (applied practically)
- **S — Single responsibility:** each module/file/function does ONE thing.
- **O — Open/closed:** you can add new behaviour without rewriting existing working code (e.g. add a new policy candidate without touching the simulator core).
- **L — Liskov:** subclasses/implementations must be swappable with their base without breaking callers.
- **I — Interface segregation:** don't force a function to take 15 params it doesn't need.
- **D — Dependency inversion:** high-level code depends on abstractions/interfaces, not concrete details.

### Structure & style
- **Modular.** One clear folder per concern (the repo already has `src/data`, `src/demand`, `src/forecast`, `src/policy`, `src/simulation`). Respect and extend this — don't create spaghetti.
- **No spaghetti code.** No 300-line functions. No God classes. No magic numbers hidden in code — every assumption lives in a config or is explicitly labelled.
- **Every number traceable.** Any output figure must be traceable back to (a) raw data or (b) an explicitly-labelled assumption.
- **Config over hardcode.** Assumptions (lead time, service level, holding cost, MOQ) live in config dataclasses, never as raw literals buried in logic.
- **Type hints + docstrings.** Every public function has a clear docstring explaining "what it does" and "why".

### Testing rules
- **Every phase gets tests.** Tests must assert *behaviour* and *invariants*, not the answer we *want*.
- **Never write a test that demands a specific good result.** A test that says "assert savings > 15%" is circular and worthless — it proves nothing. Tests prove *correctness*, not *success*.
- **Tests are not proof of "no cheating".** A test that "counts days processed" does NOT prove future data was inaccessible. Anti-leakage must be proven **by construction** (how the code is written), not by assertion.

---

## 4. The anti-cheating rules (most important for this project)

The whole point of the optimiser is a **historical replay**: "if we'd used our rules, what would have happened." This is only meaningful if it's a **fair test**.

### The one rule that governs all of it
> **The simulator must never peek at the future.**

This means, concretely:
1. A decision made for day `t` can only use information available **on or before day `t`**.
2. **Forecasts must be rebuilt using only past data** at each simulated day — not trained once on the full 11 months and then replayed. (This is the known gap in the current code.)
3. The simulator must not know "when a product was discontinued" ahead of time.
4. **Comparing policies must use identical accounting on both sides** — same holding-cost rate, same service metric, same scope. Never change the rules for one side.

### Why this matters (one line)
If the simulator peeks at the future, the number it produces — good or bad — is **meaningless**. We fix the cheating before we trust any number.

---

## 5. How to write docs in this repo

- **`CURRENT_STATUS.md`** = the honest "where we are" log. Update it whenever a meaningful milestone happens.
- **`PLAN_phase_2.md`** = the active plan. This is what's being worked on *now*.
- **`docs/archive/`** = frozen records of completed phases. Don't edit these after the fact.
- **`docs/OPTIMISER_LOGIC.md`** = plain-language "why" notes. This is where we record shared understanding.

Docs are written **in the same plain, logic-block style** this repo uses — not academic prose.

---

## 6. The definition of "done" for any task

A piece of work is done only when **all** of these are true:
1. The code runs without error.
2. Tests pass (and the tests are *meaningful*, not circular).
3. The result is **honest** — even if it's negative.
4. Every number is traceable to data or a labelled assumption.
5. No future-peeking anywhere in the decision logic.
6. The code follows DRY/SOLID and is not spaghetti.
7. A short note is added to the relevant README/status doc explaining what changed and why.

---

## 7. TL;DR for any agent

- **Talk plainly.** Logic blocks, analogies, no math jargon. Goal → method → constraints.
- **Be honest.** Negative results are fine; fake positives are not.
- **No cheating.** The simulator must never see the future.
- **Code clean.** DRY + SOLID + modular + config-over-hardcode + traceable numbers.
- **Test meaningfully.** Tests prove correctness, not the answer we want.

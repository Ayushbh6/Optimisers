# Studio Website Specification

> Status: Primary website content and product specification
>
> This document defines what the studio website represents, what it should communicate, its current content structure, and the boundaries between what exists today and what is planned.
>
> For visual decisions, always refer to:
>
> `docs/DESIGN_SYSTEM.md`

---

# 1. Purpose of the Website

This website is the public-facing home of an early-stage software studio founded by Ayush and Max.

The website has three primary purposes:

1. Introduce the studio and its philosophy.
2. Showcase real software, experiments, and projects as they are built.
3. Give potential collaborators and businesses a simple way to understand who is behind the studio and contact us.

This is NOT currently a mature SaaS product website.

It is NOT intended to create the illusion of a large established company.

The website should feel like the beginning of a technically ambitious studio.

The underlying message should be:

> Here are two technically capable people.
>
> Here is how they think.
>
> Here is what they are building.
>
> If you have an interesting problem, talk to them.

---

# 2. Studio Positioning

The studio is a broad software and AI studio.

Its identity should NOT be tied to any single:

- product
- industry
- technology
- business vertical

The studio is interested in difficult problems that can be improved through combinations of:

- software engineering
- artificial intelligence
- data
- mathematics
- quantitative modelling
- optimization
- automation

The studio's first major project happens to involve inventory and sales optimization.

That does NOT make the studio an inventory-management company.

Future projects may operate in completely different domains.

The website architecture must support this.

---

# 3. Core Studio Philosophy

The current primary expression of the studio philosophy is:

> **Complex problems. Thoughtful software.**

This is also the homepage hero headline.

This sentence should influence the rest of the website.

The studio should communicate:

- curiosity about difficult problems
- technical depth
- thoughtful engineering
- pragmatic use of technology
- willingness to combine disciplines
- preference for useful systems over technology demonstrations

AI should be treated as a tool, not the studio's entire identity.

Mathematics should be treated as a capability, not intellectual decoration.

Software should ultimately solve something useful.

---

# 4. Founders

The studio is currently founded by two people:

## Ayush

Primary orientation:

- software engineering
- artificial intelligence
- data science
- applied AI systems

Academic background includes:

- MSc Data Science
- MSc Quantitative Finance

Ayush represents the software, AI, and data side of the studio.

Final biography copy should be written separately and approved before publication.

Do not invent employers, accomplishments, titles, statistics, clients, or experience that has not been explicitly provided.

---

## Max

Primary orientation:

- mathematics
- quantitative modelling
- analytical problem solving

Academic background includes:

- Bachelor's degree in Mathematics
- MSc Quantitative Finance

Max represents the mathematical and quantitative side of the studio.

Final biography copy should be written separately and approved before publication.

Do not invent employers, accomplishments, titles, statistics, clients, or experience that has not been explicitly provided.

---

# 5. Founder Positioning

Ayush and Max should NOT be presented as identical generic "software founders."

Their complementary skill sets are part of the studio's identity.

Conceptually:

Ayush
→ software + AI + data

Max
→ mathematics + quantitative modelling

Shared foundation
→ quantitative finance + analytical problem solving

This combination helps explain why the studio is interested in technically and mathematically difficult business problems.

Do not over-explain this on the homepage.

The design and concise founder descriptions should communicate it naturally.

---

# 6. Current Reality

The studio is early-stage.

At the current stage:

- the studio website is being created
- the first optimizer MVP is planned / under development separately
- additional AI experiments may be added
- the company/studio name is not finalized
- the final logo is not finalized
- the complete project portfolio does not yet exist

This must be respected throughout implementation.

---

# 7. Truthfulness Rule

Never fabricate maturity.

Until explicitly provided, do NOT create:

- fake clients
- fake testimonials
- fake partnerships
- fake case studies
- fake usage statistics
- fake revenue
- fake user numbers
- fake enterprise deployments
- fake customer logos
- fake awards
- fake team members
- fake offices
- fake product screenshots
- fake performance claims

The studio should look excellent because the work and presentation are excellent.

It should not look established because information has been invented.

---

# 8. Homepage Architecture

The current homepage structure is:

1. Hero
2. Studio / Approach
3. Project 01 — Inventory & Sales Optimizer
4. Lab / Experiments
5. Studio / Founders
6. Contact / Closing

This architecture may evolve as real projects are added.

The homepage should feel like one continuous editorial experience rather than six isolated website modules.

---

# 9. Section 01 — Hero

## Purpose

Create the first impression of the studio.

The visitor should immediately perceive:

- technical seriousness
- taste
- confidence
- curiosity
- modern software capability

The hero should NOT attempt to explain the entire company.

---

## Primary Copy

Locked headline:

> **Complex problems. Thoughtful software.**

No explanatory paragraph underneath.

The lack of additional explanation is intentional.

---

## Navigation

Current conceptual navigation:

- Work
- Studio
- Contact

The studio/company name or logo appears separately.

Because the final company name has not yet been chosen, use a clearly identifiable placeholder during development.

Do not allow the placeholder name to accidentally become treated as final branding.

---

## Hero CTA

A restrained interaction such as:

> Explore our work →

may be used.

Avoid multiple hero CTAs.

There should be no:

- Start Free Trial
- Book Demo
- Learn More
- Get Started

cluster of buttons.

---

## Hero Visual

Use:

`/design-references/hero-image.png`

as the primary art-direction reference.

The current preferred visual concept is cinematic computational / data-centre infrastructure.

See `DESIGN_SYSTEM.md` for full visual rules.

---

# 10. Section 02 — Studio / Approach

## Purpose

After the intentionally minimal hero, this section gives the visitor slightly more context.

It should answer:

> What kind of studio is this?

without becoming a traditional "Our Services" section.

The studio works across:

- software
- AI
- data
- mathematics
- optimization
- quantitative problem solving

These should not automatically become six service cards.

---

## Communication Direction

The message should broadly communicate:

> We approach problems first and technologies second.

The exact copy is NOT locked.

Potential conceptual territory includes:

- understanding difficult systems
- turning messy problems into structured ones
- building software around those insights
- combining engineering with mathematical thinking

Do not use generic consulting language.

Avoid phrases such as:

- digital transformation
- cutting-edge solutions
- leverage AI
- unlock value
- next-generation technology
- end-to-end solutions
- revolutionary platform
- industry-leading

Final copy should remain short.

---

# 11. Section 03 — Project 01

## Current Project

Working description:

**Inventory & Sales Optimizer**

This is currently the studio's first major product/project.

The optimizer itself is being developed separately from the marketing website.

Relevant existing project documentation may include:

- `docs/BUSINESS_CONTEXT...`
- `docs/PLATFORM_SPECIFICATION...`

Those documents define the optimizer itself.

This website specification does NOT override them.

---

## Purpose of Project 01 Section

This section should demonstrate that the studio builds real things.

Eventually it should showcase:

- the actual optimizer
- its real interface
- the problem being solved
- potentially an interactive demo

The project should be presented as:

> **Project 01**

rather than as the entire identity of the company.

---

## Current Development State

Until the optimizer MVP exists:

DO NOT fabricate a finished optimizer interface.

DO NOT generate fake analytics dashboards and present them as the real product.

Instead, implementation may use a clearly temporary project presentation or placeholder.

The section should be designed so the real MVP can later replace the placeholder cleanly.

---

## Future Project CTA

Once available, likely interactions may include:

> Explore project →

or:

> Try the demo →

Exact CTA is not yet locked.

---

# 12. Section 04 — Lab / Experiments

## Purpose

The Lab gives the studio somewhere to publish smaller technical experiments without pretending every experiment is a commercial product.

This may include:

- AI prototypes
- software experiments
- data tools
- mathematical experiments
- internal tools
- small interactive demos

This is especially important because the studio's interests are broader than the first optimizer project.

---

## Philosophy

Projects in the Lab may be:

- unfinished
- experimental
- narrow
- playful
- technical

They do not need to be presented as businesses.

The Lab communicates:

> We build and experiment.

rather than:

> Here are all the enterprise products we sell.

---

## Initial State

One small AI demo may eventually be included.

Until that demo exists, do not fabricate one.

The Lab section may initially be minimal, marked as work in progress, or omitted from the first production version if there is nothing meaningful to show.

An empty section should not exist merely to satisfy the sitemap.

---

# 13. Section 05 — Studio / Founders

## Purpose

Introduce the humans behind the work.

This is particularly important at the current early stage because credibility comes substantially from:

- who the founders are
- their backgrounds
- how their capabilities complement each other
- the quality of the work being demonstrated

---

## Presentation

Current founders:

**Ayush**

Software / AI / Data

**Max**

Mathematics / Quantitative Modelling

Both have backgrounds in quantitative finance.

The final presentation should be concise.

Prefer:

- strong photography
- names
- short descriptions
- selected relevant background

over long CV-style biographies.

---

## Founder Photography

Final founder photographs are not yet locked.

The section should eventually use high-quality portraits consistent with the overall editorial art direction.

Avoid:

- generic circular LinkedIn headshots
- employee-directory layouts
- corporate team grids

The founders should feel like part of the visual story of the studio.

---

# 14. Section 06 — Contact / Closing

## Purpose

Give someone who likes the studio or has an interesting problem an obvious next action.

The tone should be open rather than sales-heavy.

Conceptually:

> Have an interesting problem?
>
> Talk to us.

Exact wording is not locked.

---

## Potential Contact Methods

Likely initial contact method:

- email

Additional methods may be added later if useful.

Do not build complex:

- CRM flows
- sales qualification forms
- booking funnels

unless they become genuinely necessary.

A simple contact interaction is sufficient for the initial studio.

---

# 15. Work / Project Architecture

The website should be built with future growth in mind.

Today:

Project 01
→ Inventory & Sales Optimizer

Future:

Project 02
→ unknown

Project 03
→ unknown

etc.

Projects should therefore use a reusable content structure.

However:

Do NOT over-engineer a CMS or complex project management system simply because more projects may exist someday.

Build for the current reality while avoiding obvious architectural dead ends.

---

# 16. Website vs Product Applications

The studio website and the applications it showcases are separate concepts.

The website is:

> the studio's public identity and portfolio.

The optimizer is:

> an actual software product/project.

Future AI demos are:

> applications or experiments showcased by the studio.

Do not tightly couple the marketing website to the optimizer codebase unless there is a clear technical reason.

A visitor should eventually be able to move naturally from:

Studio website

→ Project

→ Interactive demo/application

without those systems needing to share the same UI architecture.

---

# 17. Content Philosophy

The website should communicate through:

- strong statements
- real work
- imagery
- composition
- concise explanations

Avoid explaining everything.

Visitors should be allowed to infer competence from the work.

The writing style should be:

- short
- precise
- calm
- confident
- intelligent
- human

Avoid:

- hype
- excessive technical jargon
- corporate jargon
- startup clichés
- AI marketing language

---

# 18. AI Positioning

AI is part of the studio's capabilities.

It is NOT the studio's entire identity.

Do not structure the website around statements such as:

> We are an AI company.

Prefer the broader idea:

> We build software to solve difficult problems.

AI may be the correct tool for some problems.

Optimization, conventional software engineering, statistics, mathematical modelling, or other techniques may be better for others.

The website should reflect that technical flexibility.

---

# 19. FMCG Positioning

The studio currently has interest and potential opportunities in FMCG and operational problems.

The first optimizer project relates strongly to this area.

However:

FMCG should NOT define the overall studio identity.

Do not make the homepage hero specifically about:

- supermarkets
- warehouses
- retail shelves
- inventory
- logistics
- supply chains

Those visual and content themes belong inside the relevant project sections.

This keeps the studio open to problems in other industries.

---

# 20. Initial Website Scope

The first implementation should prioritize quality over completeness.

A sensible initial build may include:

- global page structure
- typography foundation
- navigation
- hero
- transition into the first light section
- basic section architecture
- responsive foundation

It is acceptable for later sections to remain structurally incomplete while the visual foundation is being validated.

Do NOT rush to populate the entire homepage with mediocre placeholder content.

The hero and foundational design system should be approved before extensive page expansion.

---

# 21. Implementation Philosophy

Implementation agents should work iteratively.

Recommended sequence:

### Phase 1 — Research

Read:

- `docs/DESIGN_SYSTEM.md`
- `docs/WEBSITE_SPEC.md`
- all files in `/design-references/`

Inspect the existing repository.

Research appropriate implementation techniques where useful.

---

### Phase 2 — Foundation

Establish:

- frontend architecture
- typography
- spacing system
- base colors
- responsive breakpoints
- image handling
- motion foundation

Do not over-engineer.

---

### Phase 3 — Hero

Build the hero first.

Validate:

- composition
- typography
- image treatment
- navigation
- desktop behavior
- mobile behavior

The hero establishes the visual language for the rest of the website.

---

### Phase 4 — Homepage Expansion

Only after the hero direction works, expand into:

- Studio / Approach
- Project 01
- Lab
- Founders
- Contact

Reuse the established design language.

---

# 22. Placeholder Policy

Some information is intentionally unresolved.

These include:

- company name
- logo
- final fonts
- final founder copy
- final founder photography
- optimizer screenshots
- AI demo
- contact details
- final project copy

Use clean, explicit placeholders where necessary.

Do not silently make permanent decisions for unresolved items.

If a placeholder materially affects design direction, surface the decision for review.

---

# 23. Current Locked Content

The following is currently considered established.

## Studio Type

Broad software + AI studio.

## Founders

Ayush + Max.

## Core Headline

> **Complex problems. Thoughtful software.**

## Initial Major Project

Inventory & Sales Optimizer.

## Broader Direction

Solve interesting and difficult problems using the appropriate combination of:

- software
- AI
- data
- mathematics
- quantitative modelling
- optimization

## Homepage Concept

Hero

→ Studio / Approach

→ Project 01

→ Lab / Experiments

→ Founders

→ Contact

---

# 24. Current Open Decisions

Do not assume final answers for:

- studio/company name
- logo
- domain
- exact typography
- exact color palette
- final Studio section copy
- final Project 01 copy
- Lab demo
- founder biographies
- founder images
- contact details
- final animations
- final optimizer UI
- hosting/deployment architecture

These should be resolved as the project develops.

---

# 25. Success Criteria

The first version of the website succeeds if someone unfamiliar with Ayush and Max visits it and comes away thinking:

> These are technically capable people who build thoughtful software and are working on interesting problems.

They should NOT leave thinking:

> This is an inventory company.

They should NOT leave thinking:

> This is another generic AI agency.

They should NOT leave thinking:

> This looks like two people pretending to be a 100-person enterprise company.

The website should create curiosity about:

> **What are these guys building?**

That curiosity is the desired outcome.
# Website Design System

> Status: Authoritative design source
>
> This document defines the visual direction, design principles, and UI constraints for the studio website.
>
> Any implementation work should treat this document and the files inside `/design-references/` as the primary source of truth for visual decisions.

---

# 1. Design Objective

The website represents an early-stage software studio founded by two technically and mathematically oriented founders.

The studio is broad by design.

It is not:

- an inventory optimization company
- a warehouse software company
- an AI consultancy
- a generic SaaS startup
- a corporate IT services company

The studio builds thoughtful software for difficult real-world problems using software engineering, AI, data, mathematics, and quantitative thinking.

The website should therefore feel:

- intelligent
- technically serious
- modern
- calm
- premium
- editorial
- confident
- intentionally designed

It should NOT feel:

- flashy
- over-marketed
- template-driven
- overly corporate
- futuristic for the sake of being futuristic
- like a generic AI startup landing page

The guiding idea is:

> **Less interface. More composition.**

Whitespace, typography, photography, scale, and movement should do more of the work than decorative UI components.

---

# 2. Core Visual Philosophy

The visual direction combines two primary sources of inspiration.

## Godly: Structure and Web Layout

The Godly references define the structural inspiration for the website.

See:

- `/design-references/godly-layout-1.png`
- `/design-references/godly-layout-2.png`

Study these references primarily for:

- page composition
- typography scale
- whitespace
- section proportions
- information hierarchy
- restrained navigation
- product presentation
- responsive layout thinking
- clean B2B communication

Do NOT simply reproduce these websites.

They are structural references, not templates.

---

## Dribbble: Imagery and Art Direction

The Dribbble references define the stronger visual/artistic direction.

See:

- `/design-references/dribble-image-1.png`
- `/design-references/dribble-image-2.png`
- `/design-references/dribble-image-3.png`

Study these primarily for:

- cinematic imagery
- photographic composition
- editorial presentation
- use of physical environments
- device/product presentation
- contrast between imagery and typography
- premium visual atmosphere
- image cropping and scale
- restrained visual storytelling

The final website should combine:

> **Godly-like structural clarity + Dribbble-like visual personality.**

---

# 3. Hero Section

The hero is currently the strongest locked visual direction.

Reference:

`/design-references/hero-image.png`

The reference image is a concept and art-direction reference. It does not need to be reproduced pixel-for-pixel.

## Hero Copy

The primary headline is:

> **Complex problems. Thoughtful software.**

This is intentionally sufficient on its own.

Do NOT add a paragraph underneath explaining what the company does.

Do NOT add language such as:

> "We leverage cutting-edge AI and machine learning to transform businesses..."

The hero should trust the visitor to continue exploring.

---

## Hero Composition

The desired feeling is:

- cinematic
- large scale
- minimal
- architectural
- technical
- slightly mysterious
- premium

The hero should strongly prioritize:

1. the headline
2. the image/environment
3. minimal navigation

Everything else is secondary.

The current preferred visual direction is a cinematic data-centre / computational infrastructure environment.

The data-centre works because it communicates:

- technology
- computation
- infrastructure
- scale
- engineering

without defining the studio as a specific product company.

The hero should NOT visually lock the studio into inventory management, warehousing, logistics, FMCG, finance, or any other single vertical.

---

# 4. Hero Imagery Rules

The hero image should feel closer to high-end architectural/product photography than conventional technology stock photography.

Preferred characteristics:

- strong architectural lines
- depth
- scale
- dark graphite / black materials
- restrained warm lighting
- natural-looking highlights
- cinematic shadows
- realistic physical environment
- clean composition
- space for typography
- subtle human presence may be used for scale

Avoid:

- blue cybersecurity imagery
- glowing server racks everywhere
- floating holograms
- digital brains
- AI robots
- neon circuit boards
- fake HUD overlays
- floating binary code
- glowing network connections
- excessive RGB lighting
- generic "future technology" stock imagery

The image should suggest technology rather than literally explain technology.

---

# 5. Typography

Typography is one of the primary visual elements of the website.

The site should use typography boldly and confidently.

## Primary Typography

The main sans-serif should feel:

- modern
- clean
- highly legible
- neutral but sophisticated
- appropriate at very large display sizes

Large headlines should be allowed to become major visual elements.

The exact font family is NOT yet locked.

The implementation agent may research appropriate professional web fonts based on the supplied references.

Selection criteria should include:

- excellent large-display rendering
- strong lowercase forms
- clean geometry without looking sterile
- good readability
- multiple useful weights
- strong web performance
- appropriate licensing

Avoid selecting a font simply because it is commonly used by SaaS templates.

---

## Secondary / Editorial Typography

A restrained serif or editorial typeface MAY be introduced later for selective use.

Potential uses:

- founder section
- project titles
- quotations
- editorial statements
- small visual accents

It should never compete with the primary sans-serif.

The serif/sans combination visible in some Dribbble references is inspiration, not a requirement.

---

# 6. Typography Scale

The website should embrace large typography.

Hero and major section headlines should feel substantially larger than conventional corporate websites.

Do not compress headings because they appear "too big" by normal SaaS standards.

Large typography + whitespace is part of the identity.

However:

- readability takes priority
- line breaks must feel intentional
- mobile typography must be carefully re-composed
- avoid awkward single-word lines unless intentionally designed

---

# 7. Whitespace

Whitespace is a core design element, not unused space.

Sections should have room to breathe.

Prefer:

- fewer elements
- larger spacing
- stronger hierarchy

over:

- filling empty areas
- adding decorative components
- adding unnecessary text
- squeezing multiple concepts into one viewport

If a section feels slightly too spacious compared with a normal SaaS website, that may be correct.

The site should feel editorial rather than dashboard-like.

---

# 8. Color Philosophy

Exact colors are NOT yet locked.

The current direction is restrained and largely neutral.

Primary environment:

- warm white / off-white
- charcoal
- black
- soft neutral greys

Accent colors should be used sparingly.

Avoid building the identity around:

- purple-to-blue gradients
- neon green
- generic "AI blue"
- excessive gradient backgrounds
- rainbow effects

Color should support imagery and typography rather than compete with them.

---

# 9. Light and Dark Sections

The website will NOT have a user-controlled light/dark mode toggle.

This is intentional.

The website should instead be treated as one art-directed visual experience.

Individual sections may transition between light and dark environments.

For example:

Dark cinematic hero

→

Warm off-white editorial section

→

Large project imagery

→

Dark visual break

→

Light founder/studio section

These transitions should be part of the storytelling.

Do not implement automatic system-theme switching.

Do not duplicate the entire design into separate light and dark themes.

---

# 10. Navigation

Navigation should be extremely restrained.

Current conceptual navigation:

- Work
- Studio
- Contact

Company name/logo sits separately.

The navigation should feel closer to a design studio or architecture studio than an enterprise SaaS navigation bar.

Avoid:

- huge navigation menus
- excessive dropdowns
- multiple CTA buttons
- "Solutions / Products / Resources / Pricing / Company / Blog / Login / Start Free Trial" style navigation

The website is intentionally small.

The navigation should reflect that.

---

# 11. Buttons and Calls to Action

Calls to action should be restrained.

Examples of the desired tone:

- Explore our work →
- View project →
- Try the demo →
- Contact →

Avoid excessive button usage.

Not every section needs a button.

Avoid:

- giant pill buttons everywhere
- multiple competing CTAs
- gradient buttons
- glowing buttons
- animated rainbow borders

Buttons should feel like part of the typography system rather than decorative objects.

---

# 12. Cards and Containers

Avoid the default SaaS tendency to put everything inside cards.

Do NOT automatically turn:

- services
- technologies
- founder information
- capabilities
- statistics

into grids of rounded cards.

Use cards only when the information genuinely benefits from containment.

Prefer:

- typography
- composition
- whitespace
- imagery
- columns
- strong section boundaries

over repeated card grids.

Rounded corners may be used selectively, especially for images and product interfaces, but they should not dominate the design language.

---

# 13. Product / Project Presentation

Projects should be treated almost like editorial case studies.

The Inventory/Sales Optimizer will eventually become Project 01.

When the actual MVP exists, its REAL interface should be used.

Do not create fake dashboards purely to make the marketing website look populated.

Preferred presentation:

large project title

+

short statement

+

large cinematic/product visual

+

optional interaction/demo link

The product UI may be presented:

- directly
- inside a browser frame
- inside a device
- inside a carefully art-directed photographic environment

The Dribbble references should inform this presentation.

The project should feel like work being exhibited rather than a product being aggressively sold.

---

# 14. Imagery Across the Website

Photography and visual assets should carry significant weight.

Potential sources include:

- original/generated imagery
- carefully selected licensed photography
- real product screenshots
- custom diagrams
- founder photography
- device/product compositions

AI-generated imagery is acceptable when it looks photographic and intentional.

AI-generated imagery must NOT look obviously "AI-generated."

Avoid:

- impossible architecture
- meaningless interfaces
- malformed equipment
- fake text
- visual clutter
- excessive cinematic effects
- generic futuristic imagery

Generated assets should be treated as art-directed photography, not AI decoration.

---

# 15. Motion

Motion should feel subtle and expensive.

Potential techniques:

- gentle image reveals
- slow parallax
- restrained text entrances
- image scaling during scroll
- section transitions
- subtle hover interactions
- smooth project reveals

Avoid:

- constant movement
- bouncing elements
- excessive cursor effects
- scroll hijacking
- unnecessary 3D rotation
- animation merely because the library supports it

Motion should reinforce hierarchy and atmosphere.

The visitor should notice that the website feels smooth, not notice every animation individually.

Respect `prefers-reduced-motion`.

---

# 16. Responsive Design

Mobile is not simply the desktop layout squeezed into a smaller viewport.

The design must be intentionally recomposed.

Important considerations:

- headline line breaks
- image crops
- navigation
- whitespace
- typography scale
- project presentation

The cinematic identity must survive on mobile.

Do not sacrifice the visual concept purely to preserve identical desktop positioning.

Desktop, tablet, and mobile should feel like the same art direction adapted intelligently to different canvases.

---

# 17. Content Density

Keep content intentionally concise.

The website should not spoon-feed visitors.

Avoid long explanations where a strong sentence can communicate the idea.

Prefer:

> Complex problems. Thoughtful software.

over:

> We are an innovative software development company leveraging artificial intelligence, machine learning, advanced analytics and cutting-edge technologies to solve complex business challenges.

The first is the desired philosophy.

The second is explicitly NOT the desired philosophy.

---

# 18. Things We Must Not Become

The following patterns should be actively rejected during implementation.

## Generic AI Startup

Avoid:

- glowing purple gradients
- AI brains
- robots
- neural-network backgrounds
- "AI-powered" written everywhere
- futuristic blue interfaces

## Generic SaaS Landing Page

Avoid default structures such as:

Hero

→ logo wall

→ three feature cards

→ six benefit cards

→ pricing table

→ testimonials

→ FAQ

→ giant CTA

unless there is a genuine content reason for them.

## Fake Corporate Scale

The studio is early-stage.

Do not fabricate:

- customers
- testimonials
- partnerships
- usage statistics
- product metrics
- enterprise claims
- fake case studies

Visual polish should communicate quality.

Fake scale should not.

## Overdesign

Avoid adding elements simply because the page feels empty.

Empty space is intentional.

---

# 19. Current Visual Reference Hierarchy

When design decisions conflict, use this hierarchy:

### 1. This document
Highest authority for established principles.

### 2. `/design-references/hero-image.png`
Primary hero composition/art-direction reference.

### 3. Dribbble reference images
Primary reference for imagery, photographic treatment and editorial personality.

### 4. Godly reference images
Primary reference for website structure, spacing and modern B2B layout.

### 5. External research
Useful for discovering implementation techniques and additional inspiration, but must remain consistent with the above.

External references should never override the established visual identity simply because they are trendy.

---

# 20. Research Permission

Implementation agents are encouraged to research contemporary high-quality web design.

They may investigate:

- Godly
- Dribbble
- premium software studio websites
- architecture/editorial websites
- typography systems
- motion design patterns
- responsive implementations
- modern frontend techniques

The goal of research is to understand WHY good designs work.

Do not clone a website.

Do not copy another company's visual identity.

Develop an original implementation consistent with this document.

---

# 21. Open Design Decisions

The following are deliberately NOT locked yet:

- company name
- final logo
- exact primary font
- optional secondary font
- exact color values
- final project imagery
- final founder photography
- detailed animation system
- final copy outside established text
- final Inventory Optimizer UI

Use placeholders where necessary.

Do not turn placeholders into permanent branding decisions without explicit approval.

---

# 22. Locked Decisions

The following should currently be treated as established:

### Positioning

Broad software + AI studio.

Not tied to one industry or product.

### Hero headline

> **Complex problems. Thoughtful software.**

### Hero visual direction

Cinematic computational/data-centre infrastructure.

Reference:

`/design-references/hero-image.png`

### Structural inspiration

Godly references.

### Art-direction inspiration

Dribbble references.

### Theme

Single art-directed experience.

No dark/light toggle.

### Overall visual character

Premium.

Editorial.

Technical.

Restrained.

Spacious.

Confident.

### Communication philosophy

Show more.

Explain less.

---

# 23. Final Design Test

Before adding any major UI element, ask:

> Does this make the website feel more intentional, or merely more populated?

If the answer is merely more populated, remove it.

When uncertain, prefer:

**less text  
fewer components  
better typography  
more space  
stronger imagery**
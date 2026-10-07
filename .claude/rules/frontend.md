---
paths:
  - "**/*.{ts,tsx,js,jsx,mjs,cjs,css,scss}"
  - "**/package.json"
  - "**/next.config.*"
  - "docs/design/**"
---

# Frontend rules

## The wireframe is the source of truth for UI

`docs/design/Portfolio Tracker UI.html` defines the screens, navigation,
layout, component structure, and information hierarchy. Open it before
starting any frontend issue.

- **Precedence:** the invariants in `CLAUDE.md` come first, then the issue's
  acceptance criteria for *what* gets built, then the wireframe for *how* it is
  laid out. If the wireframe breaks an invariant (for example, it shows a bare
  return percentage), follow the invariant and flag the discrepancy.
- **Ask** when the issue and the wireframe actually conflict, or when an issue
  needs a screen, control, or flow the wireframe doesn't show at all. The
  wireframe is updated first, then the code.
- **Decide yourself** on states the wireframe doesn't draw but the work
  obviously needs: loading, empty, error, stale-price indicators, and mobile
  layout. Keep them in the wireframe's visual language.
- The wireframe is a layout reference. It is not a styling spec or a data
  contract. Never hard-code its sample figures.

## Backend owns the numbers

- The frontend talks to the API over HTTP only, never directly to the
  database or to Supabase.
- The frontend displays figures and never derives them. No summing,
  return calculation, FX conversion, or valuation in the browser. If a figure
  is needed, the API provides it.
- Money and quantities arrive as decimal strings. Don't convert them to a JS
  `number` for arithmetic. Formatting for display is fine.
- Every return figure is shown with its method label, which comes from the
  API response.
- Stale and unpriced values are shown as such, using the API's markers. Never
  hide them, and never substitute zero.
- Suggestion copy describes observations. It never tells the user to buy or
  sell.

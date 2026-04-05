# Design System (Phase 4)

This project now uses a lightweight design-system layer in `frontend/css/design-system.css`.

## Goals
- Keep olive identity while raising visual quality.
- Make all pages feel consistent and premium.
- Reduce one-off styling drift as features grow.

## Core Principles
- Zero-friction interactions: clear hierarchy, minimal visual noise.
- Fluid responsiveness: spacing and layout adapt naturally.
- Motion with restraint: smooth reveals and feedback without distraction.
- Accessibility first: contrast, focus clarity, and reduced-motion respect.

## Tokens
Primary token groups:
- Typography: `--ds-font-sans`, `--ds-font-display`
- Text: `--ds-text-strong`, `--ds-text`, `--ds-text-soft`
- Surfaces: `--ds-surface-0..2`
- Borders: `--ds-border-soft`, `--ds-border`, `--ds-border-strong`
- Semantic: `--ds-success`, `--ds-danger`, `--ds-warning`
- Elevation: `--ds-shadow-soft`, `--ds-shadow-md`, `--ds-shadow-lg`
- Radius: `--ds-radius-sm/md/lg`
- Spacing: `--ds-space-1..5`

## Shared Component Rules
- Cards, forms, inputs, badges, tables, messages, and buttons are normalized globally.
- Form controls keep minimum touch target height (`42px`).
- Focus rings are visible and consistent.
- Action rows use consistent spacing.

## Motion
- Reveal-on-scroll behavior is handled in `frontend/src/ui-feedback.js`.
- Components receive staggered reveal classes: `.reveal-prep` and `.reveal-in`.
- `prefers-reduced-motion` disables heavy transitions.

## Async UX (Phase 4)
- Global fetch progress line is shown at the top of the viewport.
- Action buttons keep loading/error/done states with safe auto-reset.
- Success/error `.message` updates also surface as non-blocking toasts.

## Utilities
- `.ds-grid-2`
- `.ds-grid-3`

Use these for future dashboard sections instead of writing ad-hoc grids.

## How To Extend
1. Add/adjust tokens in `design-system.css` first.
2. Reuse existing component selectors before creating new classes.
3. Add utility classes only when patterns repeat in 2+ pages.
4. Keep page-specific overrides in `style.css`; keep cross-page standards in `design-system.css`.

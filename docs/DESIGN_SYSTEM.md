# AI Ranking OS Design System v1

The product UI optimizes for one decision flow: understand brand health, identify the cause, choose
an action, and measure the change. It targets WCAG 2.1 AA and authenticated desktop-first SaaS use,
with complete tablet and mobile layouts.

## Tokens

| Role | Token | Value | Use |
| --- | --- | --- | --- |
| Primary | `--blue` | `#3B82F6` family | Primary action, selection, charts |
| Success | `--green` | `#22C55E` family | Growth, healthy state, completion |
| Warning | `--yellow` | `#F59E0B` family | Attention, weak metric |
| Danger | `--red` | `#EF4444` family | Failure, critical state |
| Background | `--bg` | deep navy | Application canvas |
| Surface | `--surface` | raised navy | Cards, drawers, navigation |
| Border | `--border` | blue-grey | Structural separation |

Spacing follows an 8 px grid. Default card radius is 18 px; controls use 10–12 px. Motion is
150–300 ms and respects `prefers-reduced-motion`. Text and controls must meet WCAG AA contrast.

## Components

- `Button`: primary command with hover/tap feedback; never use as navigation text.
- `Card`: raised analytical surface with restrained reveal animation.
- `KpiCard`: icon, value, delta and sparkline; always opens metric detail.
- `Metric`: label, numeric value and semantic progress bar.
- `ChartContainer`: consistent title, caption and action frame for visualizations.
- `Drawer`: contextual detail without leaving the current decision flow.
- `Modal`: reserved for blocking confirmation; implemented on the accessible overlay primitive.
- `WizardStep`: numbered or completed state for linear guided flows.
- `Timeline`: chronological product or execution state.
- `Badge`: neutral, success, warning and danger status label.
- `Skeleton`: content-shaped loading placeholder; spinners are not used.

The production React primitives live in `frontend/src/ui.tsx`. Interactive charts live in
`frontend/src/charts.tsx`. New screens must reuse these components and tokens before introducing
screen-specific styles.

## Interaction rules

1. Every interactive KPI explains why, evidence, remediation and expected effect.
2. Color is never the only status signal; pair it with text, icon or numeric value.
3. Errors use human language and an explicit recovery action.
4. Empty states explain value and offer one primary action.
5. Keyboard focus must remain visible. Touch targets should be at least 44 px.
6. Charts require accessible labels and must not hide the underlying numerical meaning.

## Performance budgets

- LCP: under 2 seconds on the target production connection.
- INP: under 200 ms.
- CLS: under 0.1.
- Initial JavaScript: under 200 KB gzip.
- Lighthouse performance and accessibility target: 95 or higher.

# AI Ranking OS Web

Production React/TypeScript client for login, Research Wizard, execution and report viewing.

```bash
npm ci
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

Vite proxies `/api` to the local backend. Production uses the edge Nginx configuration in
`deployment/production`.

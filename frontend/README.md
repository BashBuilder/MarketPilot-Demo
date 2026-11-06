# MarketPilot Frontend

The review and approval surface for MarketPilot's multi-agent campaign pipeline:
submit an idea, watch the agents work over SSE, inspect the package, then approve
or request a revision.

Built with Next.js App Router, TypeScript (strict), Tailwind, shadcn/ui, Recharts,
Zod, MSW, Vitest, and Playwright.

## Requirements

- Node.js 22 or newer
- pnpm 12 (`packageManager` is pinned in `package.json`)

## Setup

```bash
pnpm install
cp .env.example .env.local
```

On PowerShell use `Copy-Item .env.example .env.local`. Set
`NEXT_PUBLIC_API_URL` in `.env.local` to the backend API, for example
`http://localhost:8000/api/v1`. Only `NEXT_PUBLIC_*` values reach the browser;
never put secrets in them.

The backend returns generated images as paths relative to its asset directory,
not as HTTP URLs. Set the server-only `BACKEND_ASSET_DIR` to that directory so
the same-origin `/api/assets` proxy can display previews. Use a shared volume in
Docker, or point it at the backend checkout during local development:

```bash
BACKEND_ASSET_DIR=../MarketPilot-Backend/backend/assets
```

## Scripts

| Script | Purpose |
| --- | --- |
| `pnpm dev` | Next dev server using `.env.local` |
| `pnpm dev:mock` | Dev server with the in-app MSW mock API |
| `pnpm dev:real` | Dev server pointed at `http://localhost:8000/api/v1` |
| `pnpm build` / `pnpm start` | Production build and server |
| `pnpm lint` | ESLint |
| `pnpm typecheck` | Next type generation plus `tsc --noEmit` |
| `pnpm test` / `pnpm test:watch` | Vitest |
| `pnpm test:e2e` / `pnpm e2e:mock` | Playwright against the mock API |
| `pnpm e2e:real` | Playwright against a real backend |

## Mock vs real mode

**Mock (`pnpm dev:mock`)** sets `NEXT_PUBLIC_API_MOCKING=enabled`. MSW serves the
API in the browser and in Server Components, so no backend is needed. The mock
seeds one campaign awaiting approval and mirrors newly created campaigns to the
server store so the review page works after submission.

**Real (`pnpm dev:real` or `pnpm dev`)** calls the backend at
`NEXT_PUBLIC_API_URL`. The backend must already be running; the frontend never
starts it.

### End-to-end modes

Playwright has two projects:

- `mock`: starts the app on port 3000 with MSW enabled. This is the default for
  `pnpm e2e:mock` and `pnpm test:e2e`.
- `real`: starts the app on port 3001 with `NEXT_PUBLIC_API_URL=$E2E_API_URL`
  and runs only the happy-path spec. It is skipped unless `E2E_API_URL` is set.

```bash
E2E_API_URL=http://localhost:8000/api/v1 pnpm e2e:real
```

The real project does not start the backend. Start it separately first, for
example with `docker compose up postgres redis backend`.

## Folder map

```
src/
  app/                 routes, layout, global styles, mock bridge route
  components/
    agents/            live agent timeline, handoffs, tool calls
    approval/          approve and revise controls
    campaign/          brief, research, copy, assets, compliance
    layout/            shell, header, navigation
    score/             score breakdown chart
    states/            empty, loading, error primitives
    ui/                shadcn/ui primitives
    version/           version list, compare, diff
  lib/
    api/               typed API client, no fetch outside here or lib/sse
    schemas/           Zod contract schemas
    security/          security header builder
    sse/               SSE hook and pure run reducer
  mocks/               MSW handlers, fixtures, stores, mock bridge
  test/                Vitest setup helpers
e2e/                   Playwright accessibility, responsive, security, happy path
ci/                    CI workflow to move into .github/workflows
```

## Tests

```bash
pnpm test              # Vitest unit and component tests
pnpm exec playwright install chromium
pnpm e2e:mock          # happy path, axe light/dark, responsive, headers
```

Playwright covers idea submission through approval, axe checks on every page in
light and dark themes, horizontal-overflow checks at 360, 768, and 1280 px, and
the configured security headers. The e2e suite runs against the mock API by
default; use `pnpm e2e:real` for a running backend.

## CI

`ci/frontend-workflow.yml` is ready to move to
`.github/workflows/frontend-workflow.yml`. It installs with pnpm, then runs lint,
type check, Vitest, build, Playwright on the mock API, and
`pnpm audit --prod --audit-level=high`.

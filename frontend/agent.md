# Frontend Agent: MarketPilot

You are the **Frontend Agent**. You own everything inside `frontend/`. You do NOT touch `backend/`. You build against the API contract in section 2, which is shared with the backend agent. If you need the contract to change, update section 2 in both `frontend/agent.md` and `backend/agent.md` in the same commit.

**Rule zero:** implement ONE step at a time. Finish its "Done when" criteria, commit, then move on. Never start step N+1 while step N is red.

You can work in parallel with the backend by running against a mock API (section 8, Step 1) until the real backend is ready.

---

## 1. Project Architecture

### 1.1 What the frontend does

Lets a user submit a campaign idea, watch the agents work live, review the generated campaign package (copy, visuals, compliance report, creative score), approve it or request a revision, and browse version history with diffs.

### 1.2 Stack

- Next.js (App Router) with TypeScript (`strict: true`)
- Tailwind CSS and shadcn/ui
- Recharts for score visualizations
- Server-Sent Events (SSE) for live agent activity
- Zod for runtime validation of API responses
- `pnpm` only. No `npm` or `yarn` lockfiles
- Testing: Vitest and React Testing Library for components, Playwright for one end-to-end flow, MSW for API mocking

### 1.3 Frontend layout

```
frontend/
  src/
    app/
      layout.tsx
      page.tsx                      campaign list and new campaign entry
      campaigns/
        new/page.tsx                idea submission
        [id]/
          page.tsx                  campaign overview (latest version)
          run/[runId]/page.tsx      live run view
          versions/page.tsx         version history
          versions/[n]/page.tsx     version detail and diff
    components/
      ui/                           shadcn primitives
      agents/                       agent timeline, event feed, status badges
      campaign/                     brief, research, copy, assets, compliance cards
      score/                        score breakdown charts (Recharts)
      approval/                     approve and revise controls
      version/                      version list and diff view
    lib/
      api/                          typed API client, one function per endpoint
      schemas/                      Zod schemas mirroring the backend contract
      sse/                          SSE hook with reconnect and Last-Event-ID
      utils/
    mocks/                          MSW handlers and fixtures
    styles/
  e2e/                              Playwright tests
  public/
  package.json
  tsconfig.json
  Dockerfile
```

Rule: components never call `fetch` directly. All network access goes through `lib/api` and `lib/sse`.

---

## 2. API Contract (shared with the backend agent)

Base path `/api/v1`, configured through `NEXT_PUBLIC_API_URL`. All bodies are JSON. Every response is parsed with a Zod schema in `lib/schemas`; a parse failure is surfaced as an error state, never silently ignored.

**Endpoints**

- `POST /campaigns` with `{ idea: string }` returns `{ campaign_id, run_id }`
- `GET /campaigns` returns `CampaignSummary[]`
- `GET /campaigns/{id}` returns one `CampaignSummary`
- `GET /campaigns/{id}/versions` returns `VersionSummary[]`, oldest first: `{ version, parent_version_id, score, created_at }`
- `GET /campaigns/{id}/versions/{n}` returns the full `CampaignPackage` for that version (no wrapper and no run metadata)
- `GET /campaigns/{id}/versions/{a}/diff/{b}` returns `{ from, to, changes: [{ path, before, after }] }`
- `POST /runs/{run_id}/approve` with `{ comment?: string }` returns `{ status: "completed", version }`
- `POST /runs/{run_id}/revise` with `{ comment: string, target_node?: string }` returns `{ run_id, version }`; `run_id` is the continuation run
- `GET /runs/{run_id}/stream` returns an SSE stream
- `GET /health` returns 200 at the root and under `/api/v1`

**Campaign summary shape** (items in `GET /campaigns` and the body of `GET /campaigns/{id}`)
`{ id, idea, status, latest_version: number | null, latest_score: number | null, active_run_id: string | null, created_at, updated_at }`

`status` is one of `draft`, `running`, `awaiting_approval`, `completed`, `failed`. `active_run_id` is the newest run that has not completed or failed.

**SSE events** (each has `id`, `event`, and JSON `data` with `run_id`, `timestamp`, `agent`)

- `agent_started`
- `agent_handoff` (from, to)
- `tool_called` (tool, duration_ms, status; status is `success`, `error`, or `denied`)
- `validation_failed` (reason)
- `retrying` (attempt, max_attempts)
- `awaiting_approval` (version)
- `completed` (version, score; score may be null)
- `error` (message, recoverable)

`agent` is one of the eight pipeline agents (`brief`, `research`, `copywriter`, `creative_director`, `designer`, `compliance`, `reviewer`, `supervisor`) or `human` for the approval gate and completion. Handoffs may target `human`.

**Stream behavior**

- The `id` of each SSE event is opaque and increasing; clients send the last one back as `Last-Event-ID`.
- The server closes the stream after a terminal event: `awaiting_approval`, `completed`, or `error` with `recoverable: false`.
- Clients must not reconnect after a terminal event. They reconnect only after an unexpected drop.
- On an unexpected drop the client leaves the `EventSource` open so the browser reconnects natively and sends `Last-Event-ID` automatically. It must not close and reopen with a query parameter, and it must not create a second connection.
- An open stream that stays silent for a generous window (default 75s) shows a bounded no-progress state with a reload action. A slow model call is not an error.

**Package shape (per version):**

A version may be snapshotted at the human gate before every agent finishes. The backend serializes it with `response_model_exclude_none`, so an unproduced section arrives either as `null` or omitted entirely. The UI must render an explicit per-section "not produced" state in both cases; it must not reject the whole package or drop the field.

- `brief`: `{ product, goal, audience, tone, channels, constraints } | null`
- `research`: `{ segments, pain_points, messaging_angles, sources } | null`, sources are `{ title, url }`
- `copy`: `{ variants } | null`, each variant is `{ channel, headline, description, cta }`
- `direction`: `{ style_guide, composition, image_prompts, video_prompts, negative_prompts } | null`
- `assets`: `{ assets } | null`, each asset is `{ uri, checksum, model, seed, prompt }`
- `compliance`: `{ items } | null`, each item is `{ check, passed, reason }`
- `score`: five dimensions (`brief_alignment`, `audience_fit`, `copy_quality`, `visual_quality`, `compliance_risk`), each `{ score, justification }`, plus `total`; the whole score is `null` until the Reviewer produces it

Asset `seed` is a 64-bit integer and may exceed `Number.MAX_SAFE_INTEGER`. JSON clients receive an imprecise `Number`, so validate it as a non-negative integer without enforcing the safe-integer cap; never reject the package because of a large seed.

**Errors:** `{ error: { code, message, details? } }` with the matching HTTP status.

---

## 3. Coding Conventions

- TypeScript `strict: true`. No `any`. No non-null assertions without a comment explaining why.
- Zod schemas are the source of truth for API types; derive TypeScript types with `z.infer`.
- Server Components by default. Use Client Components only for interactivity: the SSE feed, approval controls, diff toggles.
- Data fetching in Server Components where possible; client-side fetching for live and mutating views.
- shadcn/ui primitives first; build custom components only when no primitive fits. Style with Tailwind tokens, no arbitrary one-off values scattered around.
- One component per file, named exports, props typed with an explicit interface.
- Accessibility is part of the code, not a later pass: semantic HTML, labels on inputs, keyboard-operable controls, visible focus, sufficient contrast, `aria-live` on the agent activity feed.
- ESLint and Prettier clean. Conventional commits (`feat:`, `fix:`, `test:`, `chore:`).

---

## 4. Agent Responsibilities (what the UI must represent)

The UI mirrors the backend pipeline. Each agent has a clear visual identity (name, short description, status) in the live timeline.

- **Brief, Research, Copywriter, Creative Director, Designer, Compliance, Reviewer, Supervisor.** Show each as a step in the timeline with states: waiting, running, retrying, failed, done.
- Show handoffs between agents as they arrive (`agent_handoff`).
- Show tool calls compactly (tool name, duration, status) and expandable for details.
- Show validation failures and retries honestly, including attempt counts. Do not hide failures.
- When the stream is open but silent, show the bounded no-progress state instead of an indefinite "waiting" message. A slow model call is not a failure.
- At `awaiting_approval`, the approval panel becomes the focus of the page.

**Review screen must show:** brief, audience research, copy variants per channel, image assets with prompt, model and seed on demand, the compliance report (pass/fail per item with reason), and the creative score with per-dimension breakdown and justification.

---

## 5. Tool and Action Permissions

The frontend only does what a signed-in user is allowed to do through the API.

- Allowed: create campaign, view campaigns and versions, stream a run, approve, request a revision, view diffs.
- Not allowed: calling any endpoint not in section 2, triggering export without a recorded approval, or exposing any backend secret.
- Approve and Revise are destructive-ish actions: require an explicit confirm step, disable the buttons while the request is in flight, and prevent double submission.
- Revision requires a non-empty comment; `target_node` is optional and limited to the agent names the backend lists.

---

## 6. Data and State Rules

- Server state (campaigns, versions) comes from the API; do not duplicate it in global client stores. Use a small query layer with caching and invalidation after mutations (approve, revise).
- Live run state is derived from the SSE event stream with a reducer; it is a pure function of the ordered events so it can be replayed in tests.
- The SSE hook must handle: connection drop, native reconnect with `Last-Event-ID` (no manual close and reopen), duplicate events (dedupe by event id), a bounded stall/no-progress state, and cleanup on unmount.
- Never store anything sensitive in `localStorage`. Only UI preferences may be persisted there.
- Images are loaded from backend asset URIs; always provide `alt` text from the creative direction and a fallback state if an image fails to load.

---

## 7. Testing Requirements

- **Schemas:** every Zod schema has a test with a valid fixture and at least one invalid fixture.
- **Components:** agent timeline states, approval panel (confirm, in-flight, error), score chart, diff view, empty, loading and error states.
- **SSE hook and reducer:** event ordering, duplicate events, reconnect with `Last-Event-ID`, malformed event handling, unmount cleanup.
- **API client:** MSW-based tests for success, validation failure (bad payload shape) and HTTP error responses.
- **End-to-end (Playwright):** idea submission, live run, approve; and a second flow for revise then new version appears in history. Run against the mock API by default and against the real backend in a separate job.
- **Accessibility:** automated axe checks on each page in Playwright, with zero serious violations.
- Coverage: at least 80% on `lib/` and reducers.

---

## 8. Security Restrictions

- Only `NEXT_PUBLIC_*` variables reach the browser, and only non-secret ones. No API keys in the frontend, ever.
- Render all backend text (copy, research, justifications) as text. No `dangerouslySetInnerHTML` on backend content.
- Validate every response with Zod before use. Treat parse failure as an error state.
- Validate forms client-side (idea length limit) but never rely on that alone; show backend validation errors clearly.
- Set security headers in `next.config` (CSP, `X-Content-Type-Options`, `Referrer-Policy`, frame protection).
- Do not log tokens, full prompts or user content to the console in production builds.
- Pin dependencies through `pnpm-lock.yaml`; run `pnpm audit` in CI.
- Dockerfile: non-root user, multi-stage build, no secrets baked into the image.

---

## 9. Design Direction

Design taste is a stated bonus for the role this project supports, so treat it as a requirement.

- Editorial, calm and confident. One restrained palette (neutral base plus a single accent), a consistent type scale and a consistent spacing scale.
- The generated creative is the hero: give assets and copy room, keep chrome quiet.
- Subtle motion only where it carries meaning: an agent handoff, a score settling. Respect `prefers-reduced-motion`.
- Every view has designed empty, loading (skeletons) and error states.
- Responsive from mobile to wide desktop. Light and dark themes with correct contrast in both.

---

## 10. Implementation Workflow (step by step)

Work strictly in order. Each step: goal, tasks, done when.

### Step 0: Project bootstrap

- In `frontend/`: `pnpm create next-app` (TypeScript, Tailwind, App Router, ESLint), then `pnpm dlx shadcn@latest init`, then `pnpm add recharts zod` and dev dependencies for Vitest, React Testing Library, MSW and Playwright.
- Add `NEXT_PUBLIC_API_URL` to `.env.example`. Add a multi-stage `Dockerfile` and fill in the `frontend` service in `docker-compose.yml`.
- **Done when:** `pnpm dev` and `pnpm build` succeed, `pnpm lint` and `tsc --noEmit` pass, and the container builds.

### Step 1: Contract layer and mock API

- Zod schemas for every response and SSE event in section 2. Typed API client in `lib/api`. MSW handlers and fixtures in `mocks/`, including a scripted SSE run (happy path, retry, validation failure, awaiting approval).
- **Done when:** schema tests pass and the app can run fully against the mock API with `pnpm dev:mock`.

### Step 2: Design system foundation

- Theme tokens (colors, type scale, spacing), light and dark mode, base layout, navigation, and reusable states (empty, skeleton, error).
- **Done when:** a style page renders every token and state in both themes; contrast checks pass.

### Step 3: SSE hook and run reducer

- `lib/sse` hook with reconnect, `Last-Event-ID`, dedupe and cleanup. Pure reducer turning ordered events into run state.
- **Done when:** tests cover ordering, duplicates, native reconnect, the bounded stall state, malformed events and cleanup.

### Step 4: New campaign flow

- Idea form with validation, submit to `POST /campaigns`, redirect to the live run page. Include example prompts such as the hair-care campaign.
- **Done when:** submission works against the mock, shows loading and error states, and prevents double submit.

### Step 5: Live run view

- Agent timeline, handoff animation, compact tool-call feed, retry and validation-failure display, `aria-live` updates.
- **Done when:** replaying the scripted mock run shows every state correctly; component tests pass.

### Step 6: Review screen

- Cards for brief, research, copy variants, image assets (with prompt, model and seed on demand), compliance report, and the score breakdown chart with justifications.
- **Done when:** every section renders from a fixture package, including failed compliance items, missing images, and `null` sections from a partially produced version.

### Step 7: Approval and revision

- Approval panel with confirm step, in-flight lock, comment field. Revise requires a comment and offers an optional target node. After a mutation, invalidate queries and navigate to the new run or version.
- **Done when:** approve and revise flows work against the mock, handle HTTP errors, and cannot double submit.

### Step 8: Version history and diff

- Version list, version detail, and side-by-side diff using the diff endpoint, with changed fields highlighted.
- **Done when:** a revised campaign shows version N and N+1 with correct highlighted changes.

### Step 9: Campaign list and overview

- Campaign list with status and latest score; overview page linking to latest version, history and any active run.
- **Done when:** empty, loading, error and populated states all render correctly.

### Step 10: Integrate with the real backend

- Point `NEXT_PUBLIC_API_URL` at the running backend, fix any contract mismatches by raising them in section 2 (both files), and run the Playwright happy path against real services.
- **Done when:** idea to approval works end to end through `docker compose up`.

### Step 11: Polish, accessibility and hardening

- Motion pass with reduced-motion support, responsive checks, axe checks, security headers, `pnpm audit`, CI (lint, typecheck, unit, e2e on mock), and the frontend README section.
- **Done when:** CI is green and a fresh clone reaches the demo flow in under 10 minutes following the README.

---

## 11. Definition of Done

A step is done only when all of these hold:

1. Code follows section 3 and no component calls the network outside `lib/api` and `lib/sse`.
2. Every API response is validated with Zod; every view has loading, empty and error states.
3. Tests pass at the levels in section 7, including accessibility checks for new pages.
4. `pnpm lint`, `tsc --noEmit` and `pnpm build` report zero errors.
5. No security restriction in section 8 is violated.
6. The UI matches the design direction in section 9, in light and dark themes and on mobile.
7. The API contract in section 2 is unchanged, or updated in both agent files.
8. Docs updated, conventional commit made, CI green.
9. The step's own "Done when" criteria are demonstrably met.

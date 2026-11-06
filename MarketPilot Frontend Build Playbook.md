# MarketPilot Frontend Build Playbook

Every opencode prompt for building the frontend, in order. Each step has a plain-words explanation above its prompt.

## How to use this document

Work through the steps from top to bottom. Never skip ahead, and never start the next step while the current one is failing.

For every step, do the same routine:

1. Run `/new` in opencode to start with a clean, cheap session.
2. Make sure you are in the **Plan** agent (press `Tab` to switch between Plan and Build).
3. Paste the prompt. Read the plan it shows.
4. Press `Tab` to switch to **Build** and say "go ahead".
5. Run the check command. If it is green, make the commit.

The check command for every frontend step (run it inside `frontend/`):

```
pnpm test && pnpm lint && pnpm exec tsc --noEmit
```

If a step's tests fail twice, stop and use `/undo` instead of letting the agent keep patching.

## Before you start

**In plain words:** The shared setup (signing in to opencode, creating the empty project folders, and the rules that keep sessions small) is explained once in the Backend Build Playbook, Part 0. Do that first, then come back here.

What you need before Step 0:

- The repo skeleton exists and is committed (the root kickoff step in the backend playbook).
- `AGENTS.md` has the "Size and Token Discipline" rules, including the line about never exploring `node_modules`.
- `frontend/agent.md` exists.

Open the frontend terminal like this:

```
cd frontend && opencode
```

Keep these habits:

- Commit only this folder: `git add frontend/ && git commit -m "..."`. Never edit `backend/` from this terminal.
- If a library's usage is unclear, tell the agent to read the project's own files first (for example `src/components/ui/*.tsx` for shadcn components). It should not wander through `node_modules`. If it truly needs one library file, make it name that exact file.
- The frontend can be built against a mock API, so it does not wait for the backend until Step 10.

If the agent starts reading `node_modules`, paste this to stop it:

```
Stop reading node_modules. For component APIs read src/components/ui/*.tsx in this project. If you need a library API that isn't there, tell me the exact file and why, and read only that one file with a line limit. Continue the current step.
```

## Step 0: Frontend bootstrap

**In plain words:** Create the Next.js app, set up the design-component library, and install the extra tools. This proves the frontend builds and starts.

```
Read ./agent.md and ../AGENTS.md. Do Step 0 only: create the Next.js app, init shadcn, add dependencies. Then stop. Do not start Step 1. Show a short plan first.
```

**Commit:** `git add frontend/ && git commit -m "chore(frontend): bootstrap"`

## Step 1: Contract layer and mock API

This lets you build the whole frontend before the backend exists. The "contract" is the agreed list of what the API sends and receives.

### Step 1a: Zod schemas

**In plain words:** Write the rulebook that checks every piece of data coming from the backend. If the data does not match, the app notices instead of quietly breaking.

```
Read ./agent.md section 2 and Step 1 only. Do Step 1a only: Zod schemas in src/lib/schemas/, one file per concept: campaign, version, package (brief, research, copy, direction, assets, compliance, score), sse-events, api-error. Export inferred types with z.infer. Write a test per schema with one valid and one invalid fixture. No API client yet. Each file under 100 lines. Show the plan first.
```

### Step 1b: API client

**In plain words:** Build one small function for each backend page, all going through one shared helper. Nothing else in the app is allowed to talk to the network directly.

```
Continue Step 1. Add src/lib/api/ with one small typed function per endpoint in section 2, a shared request helper that reads NEXT_PUBLIC_API_URL, parses every response with the Zod schemas, and throws a typed ApiError using the error format. No component may call fetch directly. Test with MSW for success, bad payload and HTTP error. Show the plan first.
```

### Step 1c: Mock API

**In plain words:** Build a pretend backend that answers every request with sample data, including a scripted live run (a normal run, a retry, a failure, then waiting for approval). Now the app can run on its own.

```
Finish Step 1. In src/mocks/ add MSW handlers and fixtures for all endpoints, plus a scripted SSE run: happy path, one retry, one validation failure, then awaiting_approval. Add "dev:mock" to package.json so the app runs against the mock. Stop after Step 1's "Done when". Show the plan first.
```

**Commit:** `git add frontend/ && git commit -m "feat(frontend): contract layer and mock API"`

## Step 2: Design system foundation

### Step 2a: Theme tokens

**In plain words:** Decide the look once: colors, text sizes, and spacing, in light and dark versions, with a switch between them.

```
Read ./agent.md section 9 and Step 2 only. Do Step 2a only: Tailwind and CSS-variable tokens (one accent plus neutrals, type scale, spacing scale) with light and dark themes and a theme toggle. Check contrast for text on background in both themes. No pages yet. Show the plan first.
```

### Step 2b: Layout and navigation

**In plain words:** Build the frame every page sits inside: a top bar with links, and a neat responsive page container. It must work with the keyboard.

```
Continue Step 2. Add the root layout, a small top navigation (campaign list, new campaign), and a responsive page container using shadcn primitives. Keyboard accessible with visible focus. Show the plan first.
```

### Step 2c: Reusable states and style page

**In plain words:** Build the standard "nothing here yet", "loading" and "something went wrong" screens once, so every page can reuse them. Then make a page that shows all of them.

```
Finish Step 2. Add reusable EmptyState, SkeletonBlock and ErrorState components, then a /style page that renders every token and state in both themes. Add a Vitest test for each state component. Stop after Step 2's "Done when". Show the plan first.
```

**Commit:** `git add frontend/ && git commit -m "feat(frontend): design system foundation"`

## Step 3: SSE hook and run reducer

SSE (server-sent events) is how the backend streams live updates to the browser.

### Step 3a: Run reducer (pure)

**In plain words:** Write the part that turns a list of live events into a simple status board (who is waiting, running, retrying, failed or done). It is plain logic with no screen yet, so it is easy to test.

```
Read ./agent.md sections 4 and 6 and Step 3 only. Do Step 3a only: src/lib/sse/reducer.ts, a pure function turning an ordered list of SSE events (types from src/lib/schemas) into run state: per-agent status (waiting, running, retrying, failed, done), handoffs, tool calls, current attempt counts, final status. Ignore duplicate event ids. Test with the scripted mock run: happy path, retry, validation failure, awaiting approval, duplicates. No React yet. Under 150 lines. Show the plan first.
```

### Step 3b: SSE hook

**In plain words:** Build the connection to the live stream. It reconnects if the connection drops, never repeats an event, and cleans up when you leave the page.

```
Finish Step 3. Add src/lib/sse/useRunStream.ts: a client hook that opens EventSource on /runs/{run_id}/stream, validates each event with the Zod schemas, feeds the reducer, tracks the last event id, reconnects with Last-Event-ID after a drop, and closes on unmount. Malformed events are logged to the state as errors, not thrown. Tests with a fake EventSource: ordering, reconnect, malformed event, cleanup. Stop after Step 3's "Done when". Show the plan first.
```

**Commit:** `git add frontend/ && git commit -m "feat(frontend): SSE hook and run reducer"`

## Step 4: New campaign flow

### Step 4a: Idea form component

**In plain words:** Build the form where you type your campaign idea, with a character counter, clear error messages, and three example ideas you can click.

```
Read ./agent.md Step 4 only. Do Step 4a only: src/components/campaign/IdeaForm.tsx using shadcn form primitives. Fields: idea textarea with a character counter and a length limit, validation on submit, clear error text, disabled button while submitting, labels and keyboard support. Include 3 clickable example prompts (one is the fictional hair-care campaign for adults 25 to 40). It takes onSubmit as a prop. Component tests for validation, example prompt fill, and the in-flight disabled state. Show the plan first.
```

### Step 4b: New campaign page and redirect

**In plain words:** Put the form on its own page. When you submit, it creates the campaign and sends you to the live run page, and it stops you from submitting twice.

```
Finish Step 4. Add src/app/campaigns/new/page.tsx that renders IdeaForm and calls the createCampaign function from src/lib/api, shows ApiError messages in the ErrorState component, prevents double submit, and redirects to /campaigns/{id}/run/{runId}. Add a minimal placeholder page at that route showing the run id so the redirect works until Step 5. Test with MSW for success and an HTTP error. Stop after Step 4's "Done when". Show the plan first.
```

**Commit:** `git add frontend/ && git commit -m "feat(frontend): new campaign flow"`

Check it with `pnpm dev:mock` before committing 4b.

## Step 5: Live run view

### Step 5a: Agent timeline

**In plain words:** Build the progress list that shows all eight agents in order, each with a status badge (waiting, running, retrying, failed, done). Motion is gentle and turns off for people who prefer less motion.

```
Read ./agent.md section 4 and Step 5 only. Do Step 5a only: src/components/agents/AgentTimeline.tsx. It takes the run state from the reducer and renders the eight agents in pipeline order with a name, one-line description, and a status badge for waiting, running, retrying, failed, done. Show the attempt count when retrying. Subtle motion on status change that respects prefers-reduced-motion. Component tests for each status. Under 150 lines; split a StatusBadge into its own file. Show the plan first.
```

### Step 5b: Event feed and notices

**In plain words:** Build the small pieces that show what is happening: tool calls, handoffs between agents, and clear notices when something fails or retries. Failures are never hidden.

```
Continue Step 5. Add src/components/agents/ToolCallFeed.tsx (compact rows: tool name, duration, status, expandable details), HandoffNote.tsx (from agent to agent), and FailureNotice.tsx for validation_failed and retrying events showing the reason and attempt count. Never hide failures. The feed container uses aria-live="polite". Component tests for each. Show the plan first.
```

**Commit (after 5a and 5b):** `git add frontend/ && git commit -m "feat(frontend): agent timeline and event feed"`

### Step 5c: Live run page

**In plain words:** Put it all together on one page that watches a run live, and shows a clear "ready for your review" panel when the agents finish.

```
Finish Step 5. Replace the placeholder at src/app/campaigns/[id]/run/[runId]/page.tsx with the live run view: a client component using useRunStream, rendering AgentTimeline, ToolCallFeed, handoffs and failure notices. On awaiting_approval show a prominent panel linking to the review page for that version. Handle stream errors with ErrorState and a reconnecting indicator. Test by replaying the scripted mock run and asserting the final state. Stop after Step 5's "Done when". Show the plan first.
```

**Commit:** `git add frontend/ && git commit -m "feat(frontend): live run view"`

## Step 6: Review screen

Before this step, run `pnpm dev:mock` once and confirm the mock package fixture has a failed compliance item and an asset. If it does not, ask the agent to add them first. Otherwise the Step 6b and 6c tests will pass without testing the failure cases.

### Step 6a: Brief, research and copy cards

**In plain words:** Build the three cards that show the brief, the audience research, and the ad copy (grouped by channel). Text from the backend is always shown as plain text, never as code, for safety.

```
Read ./agent.md section 4 and Step 6 only. Do Step 6a only: src/components/campaign/BriefCard.tsx, ResearchCard.tsx, CopyCard.tsx rendering the package fields from the Zod types. Copy shows variants grouped by channel. Render all backend text as plain text, never as HTML. Each card handles missing data with the EmptyState component. One test file per card using the mock package fixture. Show the plan first.
```

### Step 6b: Assets and compliance

**In plain words:** Build the picture grid (with a fallback if an image fails to load, and a toggle to see how each image was made) and the compliance report. Pass and fail are shown with words or icons, not color alone.

```
Continue Step 6. Add AssetGrid.tsx (images with alt text from the creative direction, load-failure fallback, a details toggle revealing prompt, model and seed) and ComplianceReport.tsx (items with pass or fail, reason, clear visual distinction that does not rely on color alone). Tests including a failed compliance item and a broken image. Show the plan first.
```

**Commit (after 6a and 6b):** `git add frontend/ && git commit -m "feat(frontend): review cards"`

### Step 6c: Score chart and review page

**In plain words:** Build the score chart (bars for each of the five qualities and the total, with the reasons written below) and assemble every card into the full review page. It leaves a marked spot for the approve and revise buttons.

```
Finish Step 6. Add src/components/score/ScoreBreakdown.tsx using Recharts: per-dimension bars out of 10, the weighted total, and each justification in text below (the chart must have a text alternative). Then wire everything into src/app/campaigns/[id]/versions/[n]/page.tsx using the API client, with loading, empty and error states, and leave a clearly marked slot for the approval panel (Step 7). Test the page with the mock package, including a failed compliance item. Stop after Step 6's "Done when". Show the plan first.
```

**Commit:** `git add frontend/ && git commit -m "feat(frontend): review screen"`

## Step 7: Approval and revision

### Contract addition (do this before Step 7b)

**In plain words:** The guide listed the approve, revise and diff pages but not what they send back. Write the answers down in both guides so the frontend and backend agree.

Paste this under the endpoint list in section 2 of **both** `backend/agent.md` and `frontend/agent.md`, then commit both:

```markdown
**Response shapes**
- `POST /runs/{run_id}/approve` returns `{ status: "approved", version: number }`
- `POST /runs/{run_id}/revise` returns `{ run_id: string, version: number }` (the new run and the version it will produce)
- `GET /campaigns/{id}/versions/{a}/diff/{b}` returns `{ from: number, to: number, changes: [{ path: string, before: unknown, after: unknown }] }`
```

The backend will not build these endpoints until its Steps 11 and 12, so the frontend works against the mock until then.

### Step 7a: Approval panel component

**In plain words:** Build the decision box with two buttons: Approve, and Request revision. Each asks "are you sure?" first, revising needs a comment, and the buttons lock while a request is being sent so nothing is sent twice.

```
Read ./agent.md section 5 and Step 7 only. Do Step 7a only: src/components/approval/ApprovalPanel.tsx. Props: version number, onApprove(comment?), onRevise(comment, targetNode?), isPending, error. Two actions: Approve and Request revision. Each opens a confirm dialog (shadcn). Revise requires a non-empty comment and offers an optional target node chosen from the eight agent names. Disable all controls while pending so a double submit is impossible. Show the error with ErrorState. Component tests: confirm step required, revise blocked without a comment, controls disabled while pending, error shown. Under 150 lines; split the dialog into its own file. Show the plan first.
```

### Step 7b: Wire approve and revise

**In plain words:** Connect the buttons to the backend. After approving, show an approved state. After requesting changes, jump to the new live run. The panel only appears when a human decision is actually needed.

```
Finish Step 7. Make sure src/lib/api has approveRun and reviseRun matching the response shapes now in section 2 (update the Zod schemas and MSW handlers if they differ). In the review page src/app/campaigns/[id]/versions/[n]/page.tsx replace the marked slot with ApprovalPanel. After approve: invalidate campaign and version queries and show an approved state. After revise: navigate to /campaigns/{id}/run/{newRunId}. Only show the panel when the run is awaiting approval. Tests with MSW: approve success, revise success and redirect, HTTP error shown, double click sends one request. Stop after Step 7's "Done when". Show the plan first.
```

**Commit:** `git add frontend/ && git commit -m "feat(frontend): approval and revision"`

Check it with `pnpm dev:mock` before committing.

## Step 8: Version history and diff

### Step 8a: Version list and detail

**In plain words:** Build the history page that lists every version of a campaign, newest first, each linking to its review page.

```
Read ./agent.md Step 8 only. Do Step 8a only: src/app/campaigns/[id]/versions/page.tsx listing versions newest first with version number, date, score and status, each linking to its detail page. Add src/components/version/VersionList.tsx. Reuse the review page for detail (no new detail page). Include loading, empty and error states. Tests with MSW: list renders in order, empty state, error state. Show the plan first.
```

### Step 8b: Diff view

**In plain words:** Build the "what changed" screen. Pick two versions and see the old and new values side by side, with changes clearly marked (not by color alone).

```
Finish Step 8. Add src/components/version/DiffView.tsx and a compare control on the versions page (pick two versions). It calls the diff endpoint, groups changes by top-level section (brief, copy, assets, score), and shows before and after side by side with changed fields highlighted. Highlighting must not rely on color alone (use labels or markers). Render all values as plain text. Tests with MSW: copy change, asset change, no changes message, error state. Stop after Step 8's "Done when". Show the plan first.
```

**Commit:** `git add frontend/ && git commit -m "feat(frontend): version history and diff"`

## Step 9: Campaign list and overview

### Step 9a: Campaign list

**In plain words:** Build the home page: a list of all campaigns, newest first, each as a small card with its status and score. It has friendly empty, loading and error screens.

```
Read ./agent.md Step 9 only. Do Step 9a only: src/app/page.tsx as a campaign list using the listCampaigns API function. Add src/components/campaign/CampaignCard.tsx showing the idea (truncated), status, latest score, last updated, and a link to the overview. Newest first. Include loading skeletons, EmptyState with a link to the new campaign page, and ErrorState with a retry. Tests with MSW: populated, empty, error, and ordering. Under 150 lines per file. Show the plan first.
```

### Step 9b: Campaign overview

**In plain words:** Build the page for one campaign: its idea, the latest version summary, links to the review and history pages, and a link to the live run if one is active.

```
Finish Step 9. Add src/app/campaigns/[id]/page.tsx: the campaign idea, the latest version summary (score and status), links to the latest version review page and the version history, and a notice with a link to the live run when a run is active. Reuse components where they exist. Include loading, error and not found states. Tests with MSW: with active run, without active run, not found. Stop after Step 9's "Done when". Show the plan first.
```

**Commit:** `git add frontend/ && git commit -m "feat(frontend): campaign list and overview"`

## Work you can do before the backend API is ready

The steps in this section are numbered 11 and "Step 10 prep" because they were planned that way, but they do not need the backend. Do them now, after Step 9. Then pause this terminal until the backend finishes its Step 12.

### Contract sync (only if the backend added `sources` to the research output)

**In plain words:** If the backend's Research agent now returns a list of sources (web links), the frontend has to know about that new field.

```
Read ./agent.md section 2. Add sources ({url, title}[]) to the research Zod schema, the mock package fixture and ResearchCard. Render titles as plain text links with rel="noopener noreferrer". Update the affected tests. Show the plan first.
```

### Contract addition (also needed before the backend's Step 12)

**In plain words:** Two more things need writing down in both guides: the shape of a campaign in a list, and exactly how the live stream starts, ends and reconnects.

Paste this under the endpoint list in section 2 of **both** `backend/agent.md` and `frontend/agent.md`, then commit both. If you already did it from the backend playbook, skip this.

```markdown
**Campaign summary shape** (items in `GET /campaigns`, and the top of `GET /campaigns/{id}`)
`{ id, idea, status, latest_version: number | null, latest_score: number | null, active_run_id: string | null, created_at, updated_at }`

**Stream behavior**
- The `id` of each SSE event is opaque and increasing; clients send the last one back as `Last-Event-ID`.
- The server closes the stream after a terminal event: `awaiting_approval`, `completed`, or `error` with `recoverable: false`.
- Clients must not reconnect after a terminal event. They reconnect only after an unexpected drop.
- `GET /health` exists at the root and under `/api/v1`.
```

### Step 11a: Security headers

**In plain words:** Add the browser safety settings that stop common attacks, then check the app still loads.

```
Read ./agent.md section 8 and Step 11 only. Do Step 11a only: in next.config add security headers (Content-Security-Policy allowing the API origin from NEXT_PUBLIC_API_URL and images from the same origin plus the API origin, X-Content-Type-Options nosniff, Referrer-Policy, and frame protection). Add a test that fetches a page from the running app or inspects the config and checks each header. Confirm pnpm build still passes and the app still loads against the mock. Show the plan first.
```

### Step 11b: Accessibility checks

**In plain words:** Add an automatic checker that scans every page for problems that would make it hard to use with a screen reader or keyboard, and fix what it finds.

```
Do Step 11b only: add @axe-core/playwright and write one Playwright test per page (list, new campaign, live run, review, versions, overview) running against the mock API. Fail the test on serious or critical violations. Fix any violations found, one page at a time, smallest change first. Show the plan first.
```

**Commit (after 11a and 11b):** `git add frontend/ && git commit -m "feat(frontend): security headers and accessibility checks"`

After 11b, also run `pnpm exec playwright test`.

### Step 11c: Motion, responsive, themes

**In plain words:** Make sure animations turn off for people who prefer that, the pages fit phone, tablet and desktop screens without sideways scrolling, and everything is readable in both light and dark themes.

```
Read ./agent.md sections 3 and 9 and Step 11 only. Do 11c only:
1. Check every animated component (AgentTimeline, handoff, score) respects prefers-reduced-motion.
2. Add a Playwright test visiting each page at widths 360, 768 and 1280 and asserting no horizontal overflow (document scrollWidth not greater than clientWidth). Do not take or read screenshots.
3. Run the axe tests in both light and dark themes.
Fix violations one page at a time with the smallest change. Show the plan first.
```

### Step 11d: CI and README

**In plain words:** Write the automatic-checks file and the frontend's own instructions page. The agent writes the CI file into a safe folder, and you move it into place yourself.

```
Do 11d. You must not touch files outside frontend/. Write the CI workflow (install with pnpm, lint, tsc, vitest, build, Playwright on the mock, pnpm audit --prod --audit-level=high) to frontend/ci/frontend-workflow.yml; I will move it to .github/workflows/ myself. Write frontend/README.md: setup, scripts, mock versus real mode, folder map, how to run tests. Show the plan first.
```

**Commit (after 11c and 11d):** `git add frontend/ && git commit -m "feat(frontend): polish and CI"`

The backend's Step 15c copies this CI file into `.github/workflows/`. If you prefer, move it yourself from the root terminal.

### Step 10 prep (no backend needed)

**In plain words:** Get ready to talk to the real backend: add a switch for it, set up the real-backend test mode, and write the main user journey test, running it against the mock for now.

```
Do the Step 10 preparation only. Add a "dev:real" script setting NEXT_PUBLIC_API_URL to http://localhost:8000/api/v1. Configure Playwright with two projects, mock and real, where real is skipped unless E2E_API_URL is set, and add "e2e:real". Write the happy-path spec (submit idea, live run, approve) and run it against the mock. Do not start the backend. Show the plan first.
```

**Commit:** `git add frontend/ && git commit -m "feat(frontend): real-backend test setup"`

Then **pause the frontend terminal** until the backend has finished its Step 12.

## Step 10: Real integration (after the backend's Step 12)

Start the backend in fake mode first. In the backend folder:

```
APP_MODE=fake uv run uvicorn app.main:app --reload
```

Fake mode runs the whole pipeline with no internet and no cost, so these tests use no model tokens.

### Step 10a: Contract check against the real API

**In plain words:** Check that the real backend's answers match what the frontend expects, and fix the live stream so it stops reconnecting once the run is finished.

```
Read ./agent.md section 2 and Step 10 only. Do 10a only. The backend is running at http://localhost:8000 in fake mode. Run "pnpm dev:real" and walk through the app manually only via tests, not screenshots. First fix src/lib/sse/useRunStream.ts if needed: it must NOT reconnect after a terminal event (awaiting_approval, completed, or error with recoverable false), only after an unexpected drop; add a test for that. Then write a small script scripts/check-contract.ts that calls each GET endpoint on the real backend and parses the response with the Zod schemas, printing each failing endpoint and the Zod error. Run it, and list the failures. Do not change the backend. Do not patch around a mismatch in components; fix the Zod schema only if the guide's section 2 says the backend is right, otherwise stop and tell me. Show the plan first.
```

### Step 10b: Real end-to-end test

**In plain words:** Run the real user journey against the real backend: submit an idea, watch it run, and approve. Then do a second journey that asks for a revision and checks the new version and the diff.

```
Finish Step 10. Run the Playwright happy path against the real backend with E2E_API_URL=http://localhost:8000/api/v1 using the "real" project: submit the hair-care idea, watch the live run reach awaiting approval, open the review page, approve, and see the approved state. Then a second spec: submit, revise with a comment and a target node, see the new run, and see version 2 in history with a diff. Fix frontend defects with the smallest change, one at a time. If a failure is a backend defect, stop and report it with the request and response involved. Stop after Step 10's "Done when". Show the plan first.
```

**Commit:** `git add frontend/ && git commit -m "feat(frontend): real backend integration"`

After 10b, run `pnpm run e2e:real` as well as the usual check command. If the backend later changes how it returns image sizes or formats, the picture grid may need a layout tweak; re-run the real end-to-end spec to see.

## Final frontend check

**In plain words:** One last run of every test, to make sure nothing broke along the way.

```
Run "pnpm test && pnpm lint && pnpm exec tsc --noEmit", then with the backend running in fake mode run "pnpm run e2e:real". Report results only. Do not change code unless a test fails; then fix the smallest cause and stop.
```

## Checklist

| Check | Done when |
| --- | --- |
| Unit and component tests, lint, types | all green |
| Playwright on the mock | all green |
| Playwright on the real backend (fake mode) | happy path and revision path green |
| Accessibility checks | no serious or critical problems in light and dark |
| Fresh-clone test (see the backend playbook) | demo works in under 10 minutes |

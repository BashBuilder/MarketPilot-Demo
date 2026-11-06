# MarketPilot Backend Build Playbook

Every opencode prompt for building the backend, in order. Each step has a plain-words explanation above its prompt.

## How to use this document

Work through the steps from top to bottom. Never skip ahead, and never start the next step while the current one is failing.

For every step, do the same routine:

1. Run `/new` in opencode to start with a clean, cheap session.
2. Make sure you are in the **Plan** agent (press `Tab` to switch between Plan and Build).
3. Paste the prompt. Read the plan it shows.
4. Press `Tab` to switch to **Build** and say "go ahead".
5. Run the check command. If it is green, make the commit.

The check command for every backend step (run it inside `backend/`):

```
uv run pytest && uv run ruff check . && uv run mypy app
```

If a step's tests fail twice, stop and use `/undo` instead of letting the agent keep patching.

## Part 0: Setup (do this once)

### 0.1 Install and connect opencode

**In plain words:** Sign in to opencode once so it can use a model, then open it in the project folder.

```
git init
opencode auth login
opencode
```

`git init` is only needed if the folder is not a git repo yet. In `opencode auth login`, pick DeepSeek and paste your API key.

Useful commands inside opencode:

- `/models` picks the model. A free DeepSeek Flash model is a good default for most steps. Free offers change every week or two, so pick the model in the app each session instead of writing it into a config file.
- `/new` starts a fresh session. `/compact` shrinks a long one. `/undo` reverts the last edit.
- Type `@` and a filename to point the agent at one specific file.
- Do **not** run `/init`. It would overwrite the `AGENTS.md` you already have.

Files you should already have from earlier: `AGENTS.md` and `opencode.json` at the repo root, and `agent.md` inside both `backend/` and `frontend/`. In `opencode.json`, the `bash` block sits next to `read`, both directly under `permission`.

### 0.2 Create the empty project skeleton (from the repo root)

**In plain words:** This makes the empty folders and starter files for the whole project, with no real code yet. You approve the plan before anything is created.

```
Read AGENTS.md. Do ONLY the repo skeleton, no application code:
1. Create empty folders and placeholder files exactly as in the Repo Layout section: backend/, frontend/, docker-compose.yml, .env.example, .gitignore, README.md.
2. .gitignore must cover: node_modules, .venv, __pycache__, .next, dist, build, coverage, .env, generated_assets, *.safetensors.
3. docker-compose.yml: postgres (pgvector image) and redis only. Leave backend and frontend services as commented placeholders.
4. Do not run installs, do not touch the agent.md guides.
Show me the plan first. Wait for my go-ahead before creating files.
```

After approving and building, commit and clear the session:

```
git add -A && git commit -m "chore: repo skeleton"
```

Then run `/new`.

### 0.3 Rules to add to the root AGENTS.md

**In plain words:** These rules keep every agent session small. They tell the agent to write small files, edit one file at a time, and stay out of folders full of library code.

Add this block under the working rules in `AGENTS.md`:

```markdown
## Size and Token Discipline
- Keep every new file under ~150 lines. If it grows past that, split it into modules.
- Create or edit one file at a time, then run its test or type check before the next file.
- Never paste a whole file back to rewrite it. Use targeted edits.
- Do not read lockfiles, generated output, images, or whole directories. Open only the files the step names.
- Do not summarize or re-explain finished work. Report in three lines: changed, verified, next.
- Stop after the current step. Never start the next step on your own.
- Never explore node_modules or .venv. Read the project's own source first; if you need one library file, name it and read only that file.
```

### 0.4 The reusable next-step prompt

**In plain words:** A short prompt you can reuse for any step in the guide when you do not have a custom one.

```
Read ./agent.md. Do Step N only, in the smallest files you can. One file at a time, run its test after each file, and stop after the step's "Done when" is met. Do not start Step N+1.
```

### 0.5 Working with two terminals

**In plain words:** Once the skeleton exists, the backend and frontend are built in separate terminals so they can move at the same time.

```
cd backend && opencode
```

```
cd frontend && opencode
```

- Commit per area (`git add backend/` for one, `git add frontend/` for the other) so the two sessions never tangle in one commit.
- Neither terminal edits the other's folder.
- Keep a third terminal at the repo root for `docker compose up postgres redis` and for git.
- If the API contract must change, stop both sessions, update section 2 in both `agent.md` files, then continue.

## Step 0: Backend bootstrap

**In plain words:** Set up the Python project, install the libraries, and make one tiny page (`/health`) that says the app is alive. This proves the backend runs.

```
Read ./agent.md and ../AGENTS.md. Do Step 0 only, backend part: uv init and add dependencies, a minimal app/main.py with GET /health, one placeholder test. Do not start Step 1. Show a short plan first.
```

**Commit:** `git add backend/ && git commit -m "chore(backend): bootstrap"`

## Step 1: Core config and logging

**In plain words:** Teach the app to read its settings (like API keys) from the environment and to stop with a clear message if a required one is missing. Also set up logs that always say which run they belong to.

```
Read ./agent.md sections 3 and 9 (Step 1 only) and ../AGENTS.md "Size and Token Discipline" if present.
Do Step 1 only:
1. app/core/config.py: pydantic-settings Settings class loading DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DATABASE_URL, REDIS_URL, IMAGE_PROVIDER, COST_CAP_PER_RUN, FRONTEND_ORIGIN. Required vars fail fast with a clear error. Cached get_settings().
2. app/core/logging.py: JSON logging with context variables run_id, campaign_id, agent, step.
3. tests/test_config.py and tests/test_logging.py.
One file at a time, run its test after each file. No other modules. Show a short plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): core config and logging"`

## Step 2: Database layer

This step has four small parts. Run `docker compose up postgres redis` from the root terminal before 2c.

### Step 2a: Core table models

**In plain words:** Describe the first four database tables (campaigns, runs, versions, approvals) as Python classes. Nothing connects to a database yet.

```
Read ./agent.md section 6 and Step 2 only. Do Step 2a only: SQLAlchemy async models for campaigns, workflow_runs, campaign_versions, approvals.
Put them in app/database/models/ as one file per model plus __init__.py and a base.py (UUID PKs, created_at, updated_at where mutable). campaign_versions needs parent_version_id and is append-only. Index foreign keys and (campaign_id, version).
No session, no Alembic, no repositories yet. Each file under 100 lines. Show the plan first.
```

### Step 2b: Remaining table models

**In plain words:** Describe the rest of the tables: saved progress, agent outputs, images, compliance results, scores, tool calls, and policy documents.

```
Continue Step 2. Add models for workflow_checkpoints, agent_outputs, assets, compliance_reports, creative_scores, tool_calls, policy_documents (pgvector column) in app/database/models/, one file each, per ./agent.md section 6. agent_outputs and tool_calls are immutable. Assets store URI, checksum, model, seed, prompt. Only models. Show the plan first.
```

**Commit (after 2a and 2b):** `feat(backend): database models`

### Step 2c: Session and migration

**In plain words:** Connect to the real database and create the tables with a migration file, so any fresh database can be built the same way.

```
Continue Step 2. Add app/database/session.py (async engine, session context manager, no global sessions). Set up Alembic in migrations/ for async, generate the initial migration from the models. Do not write repositories yet. Verify: docker compose up postgres, then uv run alembic upgrade head works on a fresh DB. Show the plan first.
```

### Step 2d: Repositories and seed

**In plain words:** Add small helper functions for reading and writing each table, plus a script that fills the database with a demo campaign. A test proves an old version can never be changed.

```
Finish Step 2. Add app/database/repositories/ with one small file per aggregate (campaigns, runs, versions, approvals first). Add tests/test_versions_append_only.py proving a prior version cannot be mutated. Then app/database/seed.py, idempotent: one demo campaign and sample policy documents. Stop after Step 2's "Done when" is met. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): repositories and seed"`

## Step 3: Workflow state and schemas

### Step 3a: Early agent output models

**In plain words:** Define exactly what the first four agents must hand back (brief, research, copy, creative direction), with rules that reject empty or broken answers.

```
Read ./agent.md section 4 and Step 3 only. Do Step 3a only: Pydantic v2 output models in app/agents/outputs/, one file per model: CampaignBrief, AudienceResearch, AdCopySet, CreativeDirection. Fields follow the descriptions in section 4 (brief: product, goal, audience, tone, channels, constraints; copy: variants per channel with headline, description, CTA). Add strict validation (min lengths, non-empty lists). One test file per model with a valid and an invalid fixture. Each file under 100 lines. Show the plan first.
```

### Step 3b: Later agent output models

**In plain words:** Do the same for the last agents: images, compliance results, the creative score, and routing decisions. The score total must match the weighted dimensions.

```
Continue Step 3. In app/agents/outputs/ add AssetSet (uri, checksum, model, seed, prompt per asset), ComplianceReport (items with pass/fail and reason), CreativeScore (five dimensions, 0 to 10, one-line justification each, weighted total out of 100 using the rubric in section 4), RouteDecision. A validator must reject a total that does not match the weighted dimensions. Tests for each. Show the plan first.
```

**Commit (after 3a and 3b):** `git add backend/ && git commit -m "feat(backend): agent output models"`

### Step 3c: Workflow state and typed errors

**In plain words:** Create the shared notebook that every agent reads from and writes to, and the named kinds of errors the system will use.

```
Finish Step 3. Add app/core/errors.py with ToolError, ValidationFailure, GuardrailViolation, RetryExhausted. Add app/graph/state.py with WorkflowState (idea, brief, research, copy, direction, assets, compliance, score, versions, status, retry counters, errors) using the output models. Tests: state serializes and deserializes round trip; invalid agent output raises ValidationFailure. Stop after Step 3's "Done when". Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): workflow state and typed errors"`

### Step 3d (optional): Check the backend against the frontend

**In plain words:** A cheap read-only check that the backend's data shapes match what the frontend expects. It changes nothing.

```
Read only the files in ../frontend/src/lib/schemas/ and compare field names and types with app/agents/outputs/ and the package shape in ./agent.md section 2. Do not edit anything. List every mismatch in a short table and stop.
```

If it finds mismatches, decide which side changes, then update both guides before editing any code.

## Step 4: LLM client

### Step 4a: Client interface and fake

**In plain words:** Define what "talking to a language model" looks like in code, and build a pretend model for tests so tests never cost money.

```
Read ./agent.md Step 4 only. Do Step 4a only: in app/llm/ add an LLMClient protocol with one async method that takes messages and an optional Pydantic model class and returns the validated model plus a TokenUsage object. Add FakeLLMClient that returns queued responses, for tests. No network code. Tests for the fake. Show the plan first.
```

### Step 4b: DeepSeek client

**In plain words:** Build the real connection to DeepSeek, asking for JSON answers and turning them into checked Python objects.

```
Continue Step 4. Add DeepSeekClient in app/llm/deepseek.py using the OpenAI-compatible API with base URL and key from Settings. Request JSON output, parse into the requested Pydantic model, enforce a timeout, and fill TokenUsage. Do not call the network in tests: mock the HTTP layer. Show the plan first.
```

### Step 4c: Failure handling

**In plain words:** Decide what happens when the model answers badly or the network fails: bad answers carry the error text (so the model can be told what to fix), and temporary network problems are marked retryable.

```
Finish Step 4. Make malformed JSON and schema mismatch raise ValidationFailure with the validation error text in the message (the verifier in Step 6 will feed it back). Make timeouts and HTTP 5xx raise ToolError with a retryable flag. Tests for each case. Stop after Step 4's "Done when". Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): LLM client abstraction"`

## Step 5: Harness (registry, guardrails, middleware)

The "harness" is the safety and bookkeeping layer around the agents. These steps build it.

### Step 5a: Tool registry

**In plain words:** Make a list that says which agent is allowed to use which tool. Anything not on the list is refused.

```
Read ./agent.md section 5 and Step 5 only. Do Step 5a only: app/harness/registry.py. A ToolSpec (name, args model, async callable, side_effecting flag) and a registry that holds a per-agent allowlist exactly as in section 5 (default deny). Methods: register_tool, allowed_tools(agent), get_tool(agent, name). get_tool must raise GuardrailViolation for a tool the agent is not allowed to use or an unknown tool. Tests for allow, deny and unknown. Under 120 lines. Show the plan first.
```

### Step 5b: Guardrails and call caps

**In plain words:** Add limits so a run cannot call the image or search tools too many times or spend too much money. Also add a way to mark outside text as "untrusted" so it cannot trick the model.

```
Continue Step 5. Add app/harness/guardrails.py: a per-run counter that enforces per-tool call caps from Settings (add MAX_IMAGE_CALLS_PER_RUN and MAX_SEARCH_CALLS_PER_RUN to config with defaults) and a cost check against COST_CAP_PER_RUN. Exceeding a cap raises GuardrailViolation with a clear message. Add a helper that wraps untrusted text in delimiter blocks for prompts. Tests for each cap and the cost limit. Show the plan first.
```

**Commit (after 5a and 5b):** `git add backend/ && git commit -m "feat(backend): tool registry and guardrails"`

### Step 5c: Middleware and tool-call recording

**In plain words:** Wrap every tool call so it is checked against the rules, timed, logged, and saved in the database. Success, denial and failure are all recorded.

```
Finish Step 5. First add a small tool_calls repository in app/database/repositories/ if one does not exist (create only). Then add app/harness/middleware.py: an async wrapper that, for every tool call, checks the registry and guardrails, times the call, logs with run_id, agent and step context, and writes a tool_calls row (agent, tool, args hash, duration, cost, outcome). Failures are recorded then re-raised. Tests: a successful call writes one row, a denied call writes a denied row, a failing call writes a failed row. Stop after Step 5's "Done when". Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): harness middleware"`

## Step 6: Retries and verification

### Step 6a: Retry policy

**In plain words:** When something fails for a temporary reason, try again after a short wait that grows each time. Give up after a set number of tries.

```
Read ./agent.md Step 6 only. Do Step 6a only: app/harness/retries.py. An async retry wrapper with exponential backoff and jitter, a max attempts setting, retrying only ToolError where retryable is true, and an optional fallback callable used after the last failed attempt. When attempts are exhausted raise RetryExhausted carrying the last error. Sleep must be injectable so tests run instantly. Tests: fail then succeed, non-retryable error is not retried, exhausted raises RetryExhausted, fallback is used. Show the plan first.
```

### Step 6b: Output validators

**In plain words:** Write the checks that look at an agent's answer and say what is wrong with it (for example, a headline too long, or an image file that does not open).

```
Continue Step 6. Add app/harness/verification.py with a Validator protocol and two validator layers: schema checks (already done by Pydantic) and semantic checks. Write semantic validators for copy (headline length limits, no empty variants) and assets (file exists, decodes as an image, checksum matches). Each returns a list of issues with readable messages. Tests for passing and failing cases. No retry loop yet. Show the plan first.
```

**Commit (after 6a and 6b):** `feat(backend): retries and validators`

### Step 6c: Verify-and-retry loop

**In plain words:** Combine the two: run the agent, check its answer, and if it is wrong, tell it exactly what was wrong and let it try again, up to a limit.

```
Finish Step 6. In app/harness/verification.py add run_with_verification: call the agent step, run validators, and on failure retry with the validator issue text appended to the next prompt as feedback, up to a max attempts value from Settings. Emit a validation_failed and retrying event through a callback the caller passes in (events are not wired to SSE yet). After the last attempt raise RetryExhausted. Tests: first attempt invalid then valid, feedback text reaches the second attempt, exhausted case. Stop after Step 6's "Done when". Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): verification loop"`

## Step 7: Context, memory and checkpoints

### Step 7a: Context budget

**In plain words:** Give each agent only the part of the shared notebook it needs, and trim long text when it gets too big, so the model is never overloaded.

```
Read ./agent.md Step 7 only. Do Step 7a only: app/harness/context.py. Add a token estimator (simple character-based approximation, injectable so it can be swapped) and a function build_agent_context(state, agent_name, budget) that returns only the state fields that agent needs (define a small mapping: for example copywriter gets brief and research, designer gets direction, reviewer gets everything). If over budget, trim in this order: older research detail first, then long free-text fields, never the brief or the latest compliance issues. Tests: each agent receives only its mapped fields; a long fixture stays under budget; the brief is never trimmed. Under 150 lines. Show the plan first.
```

### Step 7b: Checkpoint save and load

**In plain words:** Save the project's progress after every step, like a game save, and be able to load the latest save.

```
Continue Step 7. Add app/harness/checkpoints.py with save_checkpoint(run_id, node_name, state) and load_latest_checkpoint(run_id) using a workflow_checkpoints repository (create the repository in app/database/repositories/ if it does not exist). State is stored as validated JSON and re-validated on load. Each checkpoint is a new row, never updated. Tests: save then load returns an equal state; the latest of several checkpoints is returned; corrupt JSON raises ValidationFailure. Show the plan first.
```

**Commit (after 7a and 7b):** `git add backend/ && git commit -m "feat(backend): context budget and checkpoints"`

### Step 7c: Resume and human interrupt

**In plain words:** If the program crashes, it can pick up where it left off. Also add the "pause and wait for a human to approve or ask for changes" button on the backend side.

```
Finish Step 7. In app/harness/checkpoints.py add resume_point(run_id) that returns the next node to run after the latest checkpoint, and a small interrupt primitive: request_approval(run_id) sets the run status to awaiting_approval and checkpoints, and submit_decision(run_id, decision) records approve or revise (with comment and optional target node) and returns the node to continue from. No LangGraph wiring yet; keep these framework-independent. Tests: simulated crash after node 3 resumes at node 4; request_approval then submit_decision(revise, target_node) routes to that node; approve returns the done marker. Stop after Step 7's "Done when". Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): resume and approval interrupt"`

## Step 8: Tools

The agents use tools to do real work. Each tool is built with a fake version first, so tests are free and fast. Run `docker compose up postgres redis` from the root terminal before 8c.

### Step 8a: Image tool interface and fake

**In plain words:** Define what "make an image" means in code, and build a pretend image maker that draws tiny test pictures. Only the Designer may use it.

```
Read ./agent.md Step 8 only. Do Step 8a only: app/tools/image_tools.py. An ImageGenerator protocol (generate(prompt, negative_prompt, seed, size) and edit(image_path, instruction)) returning an object with file path, checksum, model name, seed and prompt. Add FakeImageGenerator that writes a small deterministic PNG to the assets directory (add ASSET_DIR to Settings). Add generate_image and edit_image tool functions with Pydantic arg models, registered in the registry for the Designer only. Tests: files are written, checksums are stable for the same seed, a non-Designer agent is denied. No real model code. Show the plan first.
```

### Step 8b: Search tool

**In plain words:** Build the web-research tool with a pretend search for now. Every result keeps its web address so facts can be traced back. Only the Research agent may use it.

```
Continue Step 8. Add app/tools/search_tools.py: a SearchProvider protocol, a FakeSearchProvider returning fixed results, and a search tool that returns results with source URL, title and snippet so provenance is kept. Registered for the Research agent only, with the per-run call cap from guardrails. Do not pick a real search service yet; leave a single setting SEARCH_PROVIDER defaulting to fake. Tests for results shape, cap exceeded, and denial for other agents. Show the plan first.
```

**Commit (after 8a and 8b):** `feat(backend): image and search tools`

### Step 8c: Policy lookup

**In plain words:** Build a tool that finds the advertising rules most related to a piece of text, by comparing meanings instead of exact words. It only reads, never writes.

```
Continue Step 8. Add app/tools/policy_tools.py: policy_lookup(query, top_k) doing a read-only parameterized pgvector similarity query over policy_documents. Add an Embedder protocol in app/llm/embeddings.py with a FakeEmbedder that returns deterministic vectors from the text hash. Update seed.py so sample policy documents are embedded with the active embedder. Registered for Copywriter, Compliance and Reviewer. Tests against real Postgres: the closest seeded policy is returned for a matching query, read-only (no writes), denial for other agents. Show the plan first.
```

### Step 8d: Export tool

**In plain words:** Build the tool that packs an approved campaign into files. It refuses to run unless a human has approved that version.

```
Finish Step 8. Add app/tools/export_tools.py: export_package(version_id) assembling the approved version into a single JSON file plus referenced asset files in a folder under ASSET_DIR/exports. It must refuse unless an approval row exists for that version (raise GuardrailViolation). Registered for the Reviewer only. Tests: refused without approval, works after approval, output contains brief, copy, assets and score. Stop after Step 8's "Done when". Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): policy lookup and export tools"`

**Open decisions from this step:**

- Embeddings: the fake embedder is only a placeholder. Choose a real one (for example a small local sentence-transformers model) before you rely on policy lookup quality.
- Real image generation and a real search provider are chosen later, in Step 14 and when you pick a provider. Do not let the agent download model weights now.

## Step 9: The agents

This is the longest stretch. Build one agent at a time, in pipeline order. Each agent gets a prompt file, tests, and a failure-path test. Agents never touch the database directly; if the agent adds a database import, stop it and have it pass data in through state instead.

### Step 9a: Agent base and prompt loader

**In plain words:** Build the shared "template" every agent is made from: it loads its instructions from a text file, gets only the information it needs, and has its answers checked and retried.

```
Read ./agent.md section 4 and Step 9 only. Do Step 9a only, no real agents yet:
1. app/agents/prompts/loader.py: load_prompt(agent_name) reads app/agents/prompts/<agent_name>.md and returns text plus a version string read from a "version:" first line.
2. app/agents/base.py: a BaseAgent with name, output model class, prompt name, and an async run(state, llm, emit, tools). It builds messages from the prompt plus build_agent_context(state, name, budget), wraps any untrusted text with the guardrails delimiter helper, then calls run_with_verification with the agent's validators. It must NOT import anything from app/database. It returns the validated output model and never mutates state.
3. Tests with FakeLLMClient: prompt loads, only mapped context reaches the prompt, invalid output retries with feedback, exhausted retries raise RetryExhausted.
Under 150 lines per file. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): agent base and prompt loader"`

### Step 9b: Brief agent

**In plain words:** Build the first agent. It turns a vague idea into a clear campaign brief, without making up health claims.

```
Read ./agent.md section 4 and Step 9 only. Do Step 9b: the Brief agent only.
1. app/agents/prompts/brief.md (version: 1): turn a vague idea into a CampaignBrief (product, goal, audience, tone, channels, constraints). Rules in the prompt: invent no medical, health or performance claims; fictional products are fine; if the idea is thin, make reasonable assumptions and list them in constraints.
2. app/agents/brief.py using BaseAgent. Semantic validators: product, goal and audience non-empty, at least one channel.
3. Tests with FakeLLMClient: valid brief passes, missing audience triggers a retry with the issue text in the feedback.
4. Add one golden idea (the fictional hair-care campaign for adults 25 to 40) to app/evaluation/datasets.py as data only.
Show the plan first.
```

### Step 9c: Research agent

**In plain words:** Build the agent that studies the audience. It may only quote sources the search tool actually returned, so it cannot invent web links.

```
Do Step 9c: the Research agent only.
1. First check AudienceResearch in app/agents/outputs/. If it has no sources field, add sources as a list of {url, title}, update its tests, and tell me, because the frontend schemas need the same change.
2. app/agents/prompts/research.md (version: 1): segments, pain points and messaging angles for the brief's audience. Rules: use the search tool; cite only sources the tool returned.
3. app/agents/research.py: tools only through the registry middleware (Research is the only agent with search). Semantic validator: every source URL in the output must appear in the tool results of this run, otherwise the issue text says which URL was not retrieved.
4. Tests with FakeSearchProvider: valid cited output passes, an invented URL triggers a retry, the search call cap is respected, a non-Research agent cannot call search.
Show the plan first.
```

**Commit (after 9b and 9c):** `feat(backend): brief and research agents`

If 9c adds a `sources` field, update the research part of the package shape in section 2 of both `agent.md` files, then add the field to the frontend's schema and mock fixture (see the frontend playbook).

### Step 9d: Copywriter agent

**In plain words:** Build the agent that writes headlines and descriptions. When compliance flags a problem, it rewrites only the flagged lines and leaves the rest alone.

```
Do Step 9d: the Copywriter agent only.
1. app/agents/prompts/copywriter.md (version: 1): headlines, descriptions and CTAs, several variants per channel, using brief and research. Rules: no unsubstantiated claims, no guaranteed results, no before-and-after promises. Use policy_lookup to check wording against policy before finalizing.
2. app/agents/copywriter.py with the semantic validators from app/harness/verification.py (headline length, no empty variants).
3. Revision mode: if state.compliance contains failed items, the prompt gets only those failed items and the current copy, and the agent must rewrite only the flagged variants and keep the rest unchanged. Add a validator that unflagged variants are identical to the previous ones.
4. Tests: normal run, revision run changes only flagged variants, policy_lookup is allowed for this agent and image tools are denied.
Show the plan first.
```

### Step 9e: Creative Director agent

**In plain words:** Build the agent that writes the instructions for the pictures (what to draw, the style, and what to avoid). It has no tools at all, and it refuses real people and brand names.

```
Do Step 9e: the Creative Director agent only.
1. app/agents/prompts/creative_director.md (version: 1): image and video generation instructions, style guide, composition notes and negative prompts based on brief and copy. Rules: no real people's likenesses, no copyrighted characters or brand names, no medical imagery that implies a result.
2. app/agents/creative_director.py with no tools at all. Validators: every image prompt non-empty and within a length limit set in Settings, at least one negative prompt, a small blocklist check for named real people or brands (a list in app/agents/blocklist.py, short and editable).
3. Tests: valid direction passes, blocklisted name triggers a retry, the agent has an empty tool allowlist and any tool call is denied.
Stop after 9e. Do not start the Designer. Show the plan first.
```

**Commit (after 9d and 9e):** `feat(backend): copywriter and creative director agents`

### Step 9f: Designer agent

**In plain words:** Build the agent that makes the actual images from the creative instructions. It records how each image was made, and it never goes over the image limit.

```
Read ./agent.md section 4 and Step 9 only. Do Step 9f: the Designer agent only.
1. app/agents/prompts/designer.md (version: 1): turn CreativeDirection into assets by calling generate_image (and edit_image for revisions). Record seed, prompt and model for every asset. Rules: never alter copy or direction; never exceed the image call cap.
2. app/agents/designer.py using BaseAgent. Validators from app/harness/verification.py: each asset file exists, decodes as an image, and its checksum matches the recorded one. Exceeding MAX_IMAGE_CALLS_PER_RUN raises GuardrailViolation and must NOT be retried.
3. Revision mode: if state.compliance has failed asset items, regenerate only those assets and keep the others untouched.
4. Tests with FakeImageGenerator: all assets generated, a revision changes only flagged assets, cap exceeded raises GuardrailViolation, a non-Designer agent is denied the tool.
Under 150 lines per file. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): designer agent"`

### Step 9g: Compliance agent

**In plain words:** Build the agent that checks the ads against the rules. Simple fixed rules catch obvious bad claims first, and those rules always win over the model's opinion.

```
Do Step 9g: the Compliance agent only.
1. app/agents/compliance_rules.py: a short, editable rule list of deterministic checks (guaranteed or instant results, before-and-after promises, miracle or cure wording, absolute claims like "100%", targeting minors, named real people or brands). Pure function check_text(text) returning rule hits.
2. app/agents/prompts/compliance.md (version: 1): review copy and assets against retrieved policy, returning one ComplianceReport item per copy variant and per asset, with pass or fail and a reason. It flags only; it never rewrites copy.
3. app/agents/compliance.py: run the rule check first, then the LLM with policy_lookup. Any rule hit forces a fail for that item even if the LLM says pass. Validators: every copy variant and asset has an item, every fail has a non-empty reason.
4. Add two bad-claim cases to app/evaluation/datasets.py as data only (for example "guaranteed hair regrowth in 7 days").
5. Tests: seeded bad claims fail, a clean variant passes, a rule hit overrides an LLM pass, a missing item triggers a retry, the agent cannot call image or search tools.
Use the fake embedder for policy_lookup. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): compliance agent"`

### Step 9h: Reviewer agent and scoring

**In plain words:** Build the agent that scores the whole campaign out of 100. The math is plain code, not the model, and the score points to the weakest part to fix. It can never approve anything.

```
Do Step 9h: the Reviewer agent only.
1. app/agents/scoring.py: pure functions only. weighted_total(dimensions) per the section 4 rubric, and weakest_node(score) mapping the lowest dimension to the node to rerun: brief alignment to brief, audience fit to research, copy quality to copywriter, visual quality to creative_director, compliance risk to copywriter.
2. app/agents/prompts/reviewer.md (version: 1): score the full package on the five dimensions, 0 to 10, one-line justification each, recommend revisions. It must not approve anything.
3. app/agents/reviewer.py: allowed tool is policy_lookup (read-only). The export tool must not be callable here. Validators: every dimension scored, justifications non-empty, total equals weighted_total.
4. Tests: total mismatch triggers a retry, weakest_node covers all five dimensions and ties pick the earlier pipeline node, the Reviewer is denied export_package, the output has no approval field.
Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): reviewer agent and scoring"`

### Step 9i: Supervisor (the router)

**In plain words:** Build the traffic controller that decides what runs next: loop back to fix a problem, send to a human, or finish. It is plain rules with no model call, so it costs nothing and is easy to test.

```
Do Step 9i: the Supervisor only.
1. Add SCORE_THRESHOLD (default 70) and MAX_AUTO_LOOPS (default 2) to Settings.
2. app/agents/supervisor.py: a pure function route(state) returning RouteDecision (next node, reason). No LLM call. Rules in order: a RetryExhausted error in state means escalate to the human; failed compliance items route to copywriter if any copy item failed, otherwise designer; a score below SCORE_THRESHOLD with auto loops below MAX_AUTO_LOOPS routes to weakest_node and increments the loop counter; otherwise go to the human approval gate. Human decisions: revise goes to the given target node, or the weakest node if none was given.
3. Tests for every rule, the loop cap (third low score goes to the human, not another loop), and the escalation case.
Stop after 9i. Do not start Step 10. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): supervisor routing"`

Verify after every sub-step with the standard check command.

## Step 10: The LangGraph workflow

This wires the agents together into one running pipeline. Run `docker compose up postgres redis` from the root terminal before 10b.

### Step 10a: Node wrapper

**In plain words:** Build the "wrapper" that runs one agent safely: announce it started, run it through the checks, save its answer and progress, then announce the handoff to the next agent.

```
Read ./agent.md Step 10 only. Do Step 10a only: app/graph/nodes.py. A make_node(agent) factory returning an async node that: emits agent_started, builds context, runs the agent through the harness, validates the output, merges it into WorkflowState, writes an agent_outputs row through its repository (agents never write to the database; this layer does), saves a checkpoint, then emits agent_handoff. If RetryExhausted is raised, set status to escalated, record the error in state, checkpoint, and emit an error event. Events go through an injected emit callback. Tests with fakes: state merged, rows and checkpoint written, events in order, and the exhausted path. Under 150 lines; split helpers into their own file. Show the plan first.
```

### Step 10b: Linear workflow

**In plain words:** Connect the seven agents in a straight line from Brief to Reviewer, ending at the point where a human decides. No loops yet. This is your first real checkpoint, so fix it before moving on if it fails.

```
Continue Step 10. Add app/graph/workflow.py: a LangGraph StateGraph wiring brief, research, copywriter, creative_director, designer, compliance, reviewer in order with the node factory, ending at an awaiting_approval state (call request_approval). Linear happy path only: no loops, no conditional edges yet. Integration test against real Postgres with FakeLLM, fake image, fake search: all seven outputs persisted, checkpoints saved, events in the right order, final status awaiting_approval. Show the plan first.
```

**Commit (after 10a and 10b):** `git add backend/ && git commit -m "feat(backend): node wrapper and linear workflow"`

Optional but worthwhile: once 10b passes, write one `@pytest.mark.live` test that sends the golden hair-care idea through the real DeepSeek model (keep the fake image generator, and set `COST_CAP_PER_RUN`). Run it with `uv run pytest -m live`. It shows whether the eight prompts work together.

### Step 10c: Conditional loops

**In plain words:** Teach the pipeline to go back and fix things: if compliance fails, redo the copy or images; if the score is low, redo the weakest part. After two automatic tries it hands over to a human.

```
Read ./agent.md Step 10 and app/agents/supervisor.py only. Do Step 10c only: in app/graph/workflow.py add conditional edges after the compliance node and after the reviewer node, both calling supervisor.route(state). Compliance can route back to copywriter or designer; reviewer can route to the weakest node or to the human gate. After a loop target runs, execution continues through the normal pipeline order from that node. Increment the loop counter on every automatic loop and checkpoint it. An escalated status goes straight to the human gate. Integration tests (fakes, real Postgres): failed copy item loops to copywriter once then passes; low score loops to the weakest node; the third low score goes to the human gate instead of looping; RetryExhausted escalates; the loop counter survives a checkpoint reload. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): conditional workflow loops"`

Design note: after a loop target runs, the pipeline continues forward from that node, so a copy fix also reruns the Creative Director and Designer. That is slower but keeps the images consistent with the new copy.

### Step 10d: Human gate and resume

**In plain words:** Add the final controls: start a run (or pick it up after a crash), pause when it needs a human, continue after approval, or redo from a chosen step after a revision request.

```
Finish Step 10. Add run_workflow(run_id) in app/graph/workflow.py: if checkpoints exist it starts from resume_point(run_id), otherwise from brief; it stops when the status is awaiting_approval and does nothing if the run is already completed. Add continue_run(run_id, decision) that calls submit_decision and then continues: approve sets status completed and emits completed; revise reruns from the given target node (or the weakest node if none), with the node's earlier outputs kept. Integration tests: a simulated crash after the copywriter resumes at creative_director and finishes; run_workflow on a run waiting for approval does not rerun any node; revise with a target node reruns only from that node forward; approve completes. Stop after Step 10's "Done when". Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): human gate and resume"`

## Step 11: Versioning and approvals

Run `docker compose up postgres redis` from the root terminal first.

### Contract addition (do this before Step 11)

**In plain words:** The guide listed the approve, revise and diff pages but not what they send back. Write the answers down in both guides so the frontend and backend agree.

Paste this under the endpoint list in section 2 of **both** `backend/agent.md` and `frontend/agent.md`, then commit both:

```markdown
**Response shapes**
- `POST /runs/{run_id}/approve` returns `{ status: "approved", version: number }`
- `POST /runs/{run_id}/revise` returns `{ run_id: string, version: number }` (the new run and the version it will produce)
- `GET /campaigns/{id}/versions/{a}/diff/{b}` returns `{ from: number, to: number, changes: [{ path: string, before: unknown, after: unknown }] }`
```

### Step 11a: Version snapshots

**In plain words:** Every time a run reaches "waiting for a human", save a full copy of the campaign as a new numbered version. Old versions are never changed.

```
Read ./agent.md section 6 and Step 11 only. Do Step 11a only: app/graph/versioning.py. When a run reaches awaiting_approval, snapshot the full package (brief, research, copy, direction, assets, compliance, score) into a new campaign_versions row: version number is the previous latest plus one, parent_version_id is the previous version or null for the first. Use the versions repository; add any missing repository method (create only, never update). Hook the snapshot into the workflow at the point it requests approval. Tests: first run creates version 1 with no parent; a second package creates version 2 linked to 1; version 1 stays byte-identical afterward; trying to update a version raises an error. Show the plan first.
```

### Step 11b: Approvals and revisions

**In plain words:** Add the approve and request-changes actions. A change request carries the human's comment to the right agent and starts a new version.

```
Continue Step 11. Add app/graph/approvals.py with approve_run(run_id, comment) and revise_run(run_id, comment, target_node) that write approvals rows through the approvals repository, then call continue_run. Add revision_feedback (string or null) to WorkflowState and to the context mapping so the target node sees the human comment and its own previous output. Revise creates a new run linked to the same campaign, starting from the previous version's package, and when that run reaches approval it becomes version N+1 with parent N. Return the shapes from section 2: approve returns {status, version}, revise returns {run_id, version}. Tests: approve records a row and completes; revise with a comment creates version N+1 linked to N and the comment reaches the target node's context; revise without a comment is rejected; approving a run that is not awaiting approval raises a typed error. Show the plan first.
```

**Commit (after 11a and 11b):** `git add backend/ && git commit -m "feat(backend): versioning and approvals"`

### Step 11c: Diff and export gate

**In plain words:** Build the "what changed between version 1 and version 2" calculator, and prove with one full test that nothing can be exported before a human approves.

```
Finish Step 11. Add app/graph/diff.py: compute_diff(version_a, version_b) returning {from, to, changes: [{path, before, after}]} with dotted paths like copy.variants.0.headline, covering all package sections, and an empty list for identical versions. Pure function, no database access; a thin loader fetches the two packages. Add one end-to-end test: run, revise with a target node, approve, then export; export before approval must fail; the diff between version 1 and 2 lists only the fields the revision changed. Stop after Step 11's "Done when". Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): version diff and export gate"`

Verify after every sub-step with the standard check command.

## Step 12: API and live streaming (SSE)

This turns everything into the web API the frontend talks to. The frontend stays paused until this step is done.

### Contract addition (do this before Step 12)

**In plain words:** Two more things need writing down in both guides: the shape of a campaign in a list, and exactly how the live stream starts, ends and reconnects.

Paste this under the endpoint list in section 2 of **both** `backend/agent.md` and `frontend/agent.md`, then commit both:

```markdown
**Campaign summary shape** (items in `GET /campaigns`, and the top of `GET /campaigns/{id}`)
`{ id, idea, status, latest_version: number | null, latest_score: number | null, active_run_id: string | null, created_at, updated_at }`

**Stream behavior**
- The `id` of each SSE event is opaque and increasing; clients send the last one back as `Last-Event-ID`.
- The server closes the stream after a terminal event: `awaiting_approval`, `completed`, or `error` with `recoverable: false`.
- Clients must not reconnect after a terminal event. They reconnect only after an unexpected drop.
- `GET /health` exists at the root and under `/api/v1`.
```

This demo API has no authentication. State that plainly in the README later.

### Step 12a: App shell and campaign endpoints

**In plain words:** Start the web server and add the first pages: create a campaign, list campaigns, and get one campaign. Errors always come back in one consistent shape.

```
Read ./agent.md section 2 and Step 12 only. Do Step 12a only:
1. app/main.py: FastAPI app with an /api/v1 router, GET /health at the root and under /api/v1, CORS allowing only FRONTEND_ORIGIN (no wildcard), a per-request async session dependency, and an exception handler turning typed errors and validation errors into {error: {code, message, details?}} with the right status (ValidationFailure 422, GuardrailViolation 403, unknown id 404, other 500 with no stack trace in the body).
2. app/api/campaigns.py: POST /campaigns {idea} creates the campaign and a run through repositories, calls an injected RunLauncher (a protocol with start(run_id); for now a stub that records the id), and returns {campaign_id, run_id}. GET /campaigns and GET /campaigns/{id} return the campaign summary shape in section 2. Validate idea length with a Settings limit.
3. Pydantic response models in app/api/schemas.py matching section 2 exactly.
Tests with httpx.AsyncClient: create, list, get, 404 shape, bad idea 422 shape, CORS header present for the frontend origin and absent for another origin. Under 150 lines per file. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): API shell and campaign endpoints"`

### Step 12b: Versions, diff and approvals endpoints

**In plain words:** Add the pages for browsing versions, comparing two versions, and approving or requesting changes. Wrong requests get clear error answers.

```
Continue Step 12. Add app/api/versions.py and app/api/runs.py:
GET /campaigns/{id}/versions (list), GET /campaigns/{id}/versions/{n} (full package), GET /campaigns/{id}/versions/{a}/diff/{b} (use compute_diff), POST /runs/{run_id}/approve {comment?}, POST /runs/{run_id}/revise {comment, target_node?}. Approve and revise call the functions in app/graph/approvals.py and return the shapes in section 2. Revise requires a non-empty comment and a target_node that is one of the eight agent names, otherwise 422. Approving or revising a run that is not awaiting approval returns 409 with the error format. Revise hands the new run_id to the injected RunLauncher. Tests: every endpoint, 404 for unknown campaign or version, 409 cases, 422 cases, diff of identical versions returns an empty changes list. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): version and approval endpoints"`

### Step 12c: Event bus and SSE stream

**In plain words:** Build the live "news feed" of what the agents are doing. Events are stored in Redis, so a browser that disconnects can reconnect and catch up without missing anything or repeating anything.

```
Continue Step 12. Use Redis Streams (one stream per run, key run:{run_id}:events) so replay works.
1. app/events/bus.py: an EventBus protocol with publish(run_id, event_type, agent, data) and read(run_id, after_id). A RedisEventBus and an InMemoryEventBus for tests. The stored id is the stream id. The event body carries run_id, timestamp and agent plus the data per section 2.
2. Wire it as the emit callback used by the node wrapper and the verification loop, so agent_started, agent_handoff, validation_failed, retrying, awaiting_approval, completed and error all publish. Also make the middleware publish tool_called (tool, duration_ms, status) through a context-held emitter.
3. app/api/stream.py: GET /runs/{run_id}/stream returning text/event-stream. Honor the Last-Event-ID header by replaying events after that id, then follow new events, send a comment heartbeat every 15 seconds, and close the stream right after a terminal event. Unknown run returns 404 before streaming.
Tests: events for a fake full run arrive in pipeline order including tool_called, plus a forced validation failure producing validation_failed then retrying; a client that stops after event 3 and reconnects with Last-Event-ID receives only events after 3, no duplicates; the stream ends after awaiting_approval; unknown run 404. Because the stream closes, httpx's ASGI transport can read it fully in tests. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): event bus and SSE stream"`

### Step 12d: Run launcher, fake mode and contract tests

**In plain words:** Make runs actually start in the background when you create a campaign. Add a "fake mode" that runs the whole pipeline with no internet and no cost. Then add tests that lock the API shapes so the frontend never breaks silently.

```
Finish Step 12.
1. app/runs/launcher.py: a real RunLauncher that starts run_workflow(run_id) as an asyncio task owned by the app (keep references so tasks are not garbage collected), catches and records any exception as an error event with recoverable false, and cancels cleanly on shutdown. Replace the stub in the dependency wiring.
2. Fake mode: add APP_MODE (real or fake) to Settings. In fake mode the app wires a scripted LLM client that returns valid canned outputs for each of the eight agents (use the golden idea data), FakeImageGenerator, FakeSearchProvider and FakeEmbedder, so the whole pipeline runs with no network and no tokens. Document it in .env.example.
3. tests/test_contract.py: build the expected shapes from section 2 of this guide and assert every endpoint response and every SSE event conforms (required keys, types, no extra required fields). Include the campaign summary shape.
4. Read ONLY ../frontend/src/lib/schemas/ and compare it with the response models in app/api/schemas.py. Do not edit the frontend. List every mismatch in a short table.
Stop after Step 12's "Done when": full run in fake mode produces the right event order via httpx, Last-Event-ID resume works, contract test passes. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): run launcher, fake mode, contract tests"`

If the mismatch table from item 4 is not empty, decide which side changes, update section 2 in both guides, and fix the side that is wrong before the frontend starts.

Then start the backend for the frontend:

```
APP_MODE=fake uv run uvicorn app.main:app --reload
```

Now restart the frontend terminal and do the frontend Step 10 (see the frontend playbook).

## Step 13: Evaluation

This measures whether the safety rules and the pipeline logic actually work. Offline mode checks the harness (rules, loop cap, schemas) using fakes. It does not prove the real model output is good; only `--live` mode shows real model behavior.

### Step 13a: Golden dataset (data only)

**In plain words:** Write down a fixed set of test cases: sample ideas, ads that must be rejected, and ads that must be accepted.

```
Read ./agent.md Step 13 only. Do Step 13a only: expand app/evaluation/datasets.py, data only, no logic. Add:
1. GOLDEN_IDEAS: 6 campaign ideas (include the fictional hair-care one for adults 25 to 40) each with an id and short expected traits (target age range, channel hints).
2. BAD_CLAIM_CASES: 12 copy variants that must FAIL compliance, each with an id and the rule it violates (guaranteed results, instant results, before-and-after promises, miracle or cure wording, absolute claims like "100%", targeting minors, named real person, named brand).
3. CLEAN_CASES: 8 copy variants that must PASS (plain benefit claims, no guarantees).
4. Fictional products only; no real people or brands beyond the blocklist test cases, which use obviously fake names.
Add one test checking every case has a unique id and a non-empty text. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): evaluation datasets"`

### Step 13b: Evaluators

**In plain words:** Write the small scoring functions that turn test results into numbers: how many bad ads were caught, how many good ads were wrongly blocked, and whether scores stay steady.

```
Continue Step 13. Add app/evaluation/evaluators.py, pure functions with no I/O:
1. schema_validity(raw_outputs) returning pass count, total and the failing agent names.
2. compliance_recall(cases, results) for BAD_CLAIM_CASES (share correctly failed) and compliance_false_positive_rate for CLEAN_CASES (share wrongly failed). Return per-rule recall too.
3. score_spread(scores) returning max minus min of total scores across repeated runs of the same package, and stable(scores, max_spread) as a bool.
4. loop_behavior(events) checking a run never exceeded MAX_AUTO_LOOPS.
Tests for each with hand-built inputs, including empty input and a perfect and a worst case. Under 150 lines; split by metric if longer. Show the plan first.
```

### Step 13c: Runner and regression gate

**In plain words:** Build one command that runs all the tests and prints a pass-rate table. If any number drops below the agreed minimum, it fails, so quality cannot quietly get worse.

```
Continue Step 13. Add app/evaluation/runner.py, run with "uv run python -m app.evaluation.runner [--live] [--update-baseline]":
1. Offline mode (default): uses the fake LLM, fake image and fake search from APP_MODE=fake. Runs compliance cases through check_text plus the Compliance agent, runs the 6 golden ideas through the whole workflow, and computes the metrics from 13b.
2. --live mode: real DeepSeek, fake image generator, a hard cost stop from COST_CAP_PER_RUN, and a score stability test that runs the Reviewer 3 times on one stored package.
3. app/evaluation/baseline.json holds the thresholds (schema validity 100%, bad-claim recall at least 0.9, false positives at most 0.1, spread at most 8 points). The runner prints a pass-rate table and exits nonzero if any metric is below its threshold. --update-baseline rewrites the file and is never run automatically.
4. Write results to app/evaluation/results/ (add to .gitignore).
5. Tests: the table output, the nonzero exit on a seeded regression (a fake that lets a bad claim through), and offline mode needs no network.
Show the plan first.
```

**Commit (after 13b and 13c):** `git add backend/ && git commit -m "feat(backend): evaluation runner and baseline"`

### Step 13d (optional): Real embedder and live evaluation

**In plain words:** Swap the pretend meaning-finder for a real one and run the evaluation against the real model. Only do this when you decide you want it; the agent must stop and ask before downloading anything.

```
Do 13d only if I say so. Replace FakeEmbedder usage in real mode with a local sentence-transformers model behind the existing Embedder protocol: add the dependency as an optional group (uv add --optional embeddings sentence-transformers), keep the fake as the default for tests and fake mode, and add EMBEDDER (fake or local) to Settings. Re-embed the seeded policy documents on startup when the embedder changes. Do NOT download any model automatically: print the model name and size and stop for my approval. Then run "uv run python -m app.evaluation.runner --live" and report the table. Show the plan first.
```

If recall is already high with the fake embedder (the fixed rules do most of the work), you can skip 13d.

## Step 14: Image and video model exploration

Decide how you will run image models before 14b. Local models need a GPU with enough VRAM. Without one, use a hosted endpoint that serves an open-source model, which avoids downloading multi-gigabyte weights.

### Step 14a: Provider adapters (no downloads)

**In plain words:** Build the plug-in connectors for two real ways to make images (a hosted service, or a model on your own machine) without downloading anything yet.

```
Read ./agent.md Step 14 only. Do 14a only: in app/tools/image_providers/ add two adapters implementing the existing ImageGenerator protocol, each in its own file under 120 lines:
1. hosted.py: HostedImageGenerator calling an HTTP endpoint configured by IMAGE_API_URL and IMAGE_API_KEY, with timeout and mapping failures to ToolError (retryable on 5xx and timeouts, not on 4xx).
2. local_diffusers.py: LocalDiffusersGenerator using the diffusers library, imported lazily so the project runs without it, with the model id from Settings.
Add both to IMAGE_PROVIDER choices (fake, hosted, local). Add diffusers and torch only as an optional dependency group (images). Do NOT install the optional group and do NOT download any model weights. Tests with the HTTP layer mocked: success, 5xx retryable, 4xx not retryable, and importing the module without diffusers installed does not crash. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): image provider adapters"`

### Step 14b: Benchmark script

**In plain words:** Write a script that tries each image model on the same five prompts and records speed and memory use, leaving blanks for you to rate quality and fill in the licence.

```
Continue Step 14. Add benchmarks/image_models.py (outside app/). For each configured provider and model id, generate images for 5 fixed prompts built from the first 5 GOLDEN_IDEAS with fixed seeds, record per image: latency, file size, seed, model id, and peak VRAM when CUDA is available. Save the images under ASSET_DIR/benchmarks/<model>/. Write benchmarks/results.md with a table (model, median latency, peak VRAM, failure count) and a column for my manual quality score from 1 to 5, left blank, plus a licence column left blank for me to fill in. Before any model weights would be downloaded, print the model id and approximate size and wait for my confirmation. Support --dry-run that uses FakeImageGenerator to prove the script works. Test the dry run only. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): image model benchmark script"`

Then you run it yourself against 2 or 3 models (for example FLUX.1 schnell and SDXL):

```
uv run --group images python benchmarks/image_models.py
```

Rate the five images per model yourself, and fill in the licence column from each model's own page. Commercial-use terms differ between model variants.

### Step 14c: Decision document and video check

**In plain words:** Write down which image model you chose and why, and decide about video. If no video model runs on your hardware, record that video is skipped.

```
Finish Step 14. Using only benchmarks/results.md which I will have filled in, write docs/model-decision.md: the compared models with their numbers, the chosen default image model and why, the fallback, the licence note I wrote, and how to switch (IMAGE_PROVIDER and model id). Add a short video section: name at most two open-source video models to evaluate, the hardware each realistically needs, and the decision. If none runs on my hardware, record "video skipped, stub kept" and make sure the video tool stays a stub that raises a clear "not enabled" ToolError. Do not run any video model. Set the chosen default in .env.example. Stop after Step 14's "Done when". Show the plan first.
```

**Commit:** `git add -A && git commit -m "docs: model decision"`

## Step 15: Hardening, CI and README

This is the last build step. 15a and 15b run in the backend terminal. **15c and 15d run from the repo root**, because they edit root files (`docker-compose.yml`, `.env.example`, `README.md`, `.github/`).

### Step 15a: Redis limits and startup resume

**In plain words:** Stop the live-event storage from growing forever, and make the server pick up any unfinished runs when it restarts.

```
Read ./agent.md Step 15 and sections 6 and 8 only. Do Step 15a only:
1. app/events/bus.py: cap each run stream with XADD MAXLEN (approximate) from a Settings value EVENT_STREAM_MAXLEN (default 2000), and set an expiry on the stream key (EVENT_STREAM_TTL_SECONDS, default 86400) after the terminal event is published. InMemoryEventBus gets the same cap so the behavior is tested.
2. app/runs/startup.py: resume_unfinished_runs(). On app startup, find runs whose status is running (not awaiting_approval, completed or escalated), take a short Redis lock per run so two server processes cannot start the same run, and start each through the RunLauncher using run_workflow, which resumes from the latest checkpoint. Log each resumed run. A failure on one run must not stop the others or the app from starting.
3. Wire it into the FastAPI lifespan, switchable with RESUME_ON_STARTUP (default true).
Tests: stream length stays under the cap after many events; the TTL is set after a terminal event; a run left at "running" is resumed once; a locked run is skipped; one failing resume does not block the rest; RESUME_ON_STARTUP=false resumes nothing.
Under 150 lines per file. Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): stream limits and startup resume"`

### Step 15b: Rate limits and concurrency cap

**In plain words:** Stop one person (or a bug) from flooding the server: limit requests per minute and limit how many runs can go at once.

```
Continue Step 15.
1. app/api/limits.py: a Redis fixed-window rate limiter as a FastAPI dependency, keyed by client IP (read X-Forwarded-For only when TRUST_PROXY=true, otherwise the socket address). Settings: RATE_LIMIT_PER_MINUTE (default 20) for POST /campaigns, /runs/*/approve and /runs/*/revise, and a more generous limit for GETs. Over the limit returns 429 with the standard error format and a Retry-After header.
2. A concurrency cap: MAX_CONCURRENT_RUNS (default 3). When the number of running runs is at the cap, POST /campaigns and revise return 429 with code "too_many_runs" and create nothing. Count from the database, not from memory.
3. Security checks from section 8: confirm idea length and comment length limits exist and are in Settings; confirm no response body contains a stack trace or a secret; confirm CORS has no wildcard. Add a test for each.
4. Add the new settings to .env.example (edit only the three new lines, nothing else, via ../.env.example).
Tests: the 21st request in a minute gets 429 with Retry-After; the cap blocks the 4th concurrent run and creates no rows; limits apply per IP; X-Forwarded-For is ignored unless TRUST_PROXY is true.
Show the plan first.
```

**Commit:** `git add backend/ && git commit -m "feat(backend): rate limits and concurrency cap"`

Verify after each with the standard check command.

### Step 15c: Containers and CI (from the repo root)

**In plain words:** Package the app so it starts with one command, and set up automatic checks that run every time you push code.

Open a terminal at the repo root (`cd ..` from `backend/`), start opencode, and paste:

```
Read AGENTS.md and backend/agent.md Step 15 only. Do Step 15c only. You may edit docker-compose.yml, .env.example and files under .github/. Do not edit application code.
1. backend/Dockerfile: multi-stage build with uv (sync with the lockfile, no dev dependencies in the final image), non-root user, no secrets baked in, a HEALTHCHECK calling /health, and an entrypoint script that runs "alembic upgrade head" then uvicorn.
2. docker-compose.yml: postgres (pgvector image) and redis with healthchecks, backend and frontend services un-commented and built from their Dockerfiles, depends_on with service_healthy, APP_MODE defaulting to fake so a fresh clone works with no keys, named volume for the database and for ASSET_DIR. Ports: backend 8000, frontend 3000. The frontend must reach the backend at the URL set by NEXT_PUBLIC_API_URL (note it is baked in at build time; use a build arg).
3. .github/workflows/backend.yml: on push and pull request, with postgres (pgvector) and redis service containers: uv sync --frozen, ruff check, ruff format --check, mypy app, pytest, "uv run alembic upgrade head" then "uv run alembic check" to catch model drift, pip-audit, and the offline evaluation runner as a gate (nonzero exit fails the job).
4. Copy frontend/ci/frontend-workflow.yml to .github/workflows/frontend.yml unchanged except for paths needed to run from the repo root (working-directory: frontend).
5. Check with "docker compose config" and "docker compose build". Do not run "docker compose up". Report any build error and its fix.
Show the plan first.
```

Check it yourself before committing:

```
docker compose config
docker compose build
```

**Commit:** `git add -A && git commit -m "chore: containers and CI"`

If CI later fails on `alembic check`, a model changed without a migration. Generate one with `uv run alembic revision --autogenerate -m "..."`. Do not loosen the check.

### Step 15d: README (from the repo root)

**In plain words:** Write the project's front page: what it is, how to run it, how it works, and an honest list of what it does not do.

```
Do Step 15d. Write README.md at the repo root with: what MarketPilot is in three sentences; a simple (no tree-drawing characters) architecture summary covering the eight agents, the harness, the human approval gate and version history; quick start (cp .env.example .env, docker compose up --build, open http://localhost:3000, run the demo idea); the two modes (APP_MODE fake needs no keys, real needs DEEPSEEK_API_KEY and a chosen image provider, link docs/model-decision.md); how to run tests, the evaluation runner and the live checks; the tool permission table; the API contract summary linking backend/agent.md section 2; and a "Limitations" section stating plainly: no authentication in this demo, runs execute inside the API process, the offline evaluation checks the harness not model quality, and video is not enabled (if that is what docs/model-decision.md says). Keep it under 200 lines. Do not add screenshots or a demo GIF. Do not claim anything the code does not do; if unsure, read the file named. Show the plan first.
```

**Commit:** `git add -A && git commit -m "docs: README"`

## The fresh-clone test (you do this yourself)

**In plain words:** The final proof. Download your own project to a clean folder and see if a stranger could run it. The agent cannot do this for you.

```
git clone <your-repo-url> /tmp/mp-test && cd /tmp/mp-test
cp .env.example .env
docker compose up --build
```

Then open `http://localhost:3000`, submit the hair-care idea, watch the run, approve it, request one revision, and check version history and the diff. Time it: the target is under 10 minutes from clone to a working demo. If anything fails, copy the error into the root terminal and fix the smallest thing.

## Final checklist

| Check | Done when |
| --- | --- |
| Backend tests, lint, types, evaluation gate | all green in CI |
| Frontend tests, lint, types, Playwright (mock and real) | all green |
| `docker compose up --build` from a fresh clone | demo works, under 10 minutes |
| `docs/model-decision.md` | filled in from your own benchmark |
| One live DeepSeek run | done once, with `COST_CAP_PER_RUN` set |
| README Limitations | honest and matches the code |

**Things only you can do:** rate the benchmark images and fill in licences, run the live DeepSeek check, run the fresh-clone test, and move or create the CI files if you have not.

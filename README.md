# AI QA Agent — Agentic Playwright Testing Assistant

Turns a plain-English instruction like *"Test login using invalid
credentials"* into: a structured test plan → runnable Playwright code →
an actual browser run → screenshots/trace/video → and, if it fails, an
AI-written bug report — all wrapped in one HTML report.

## Architecture (already built)

```
instruction
   -> agents/planner.py     Plain English -> TestPlan (Pydantic)
   -> agents/generator.py   TestPlan -> Playwright code (Pydantic)
   -> executor/runner.py    Runs code in real Chromium, captures artifacts
   -> agents/analyzer.py    On failure -> BugReport (Pydantic)
   -> reports/report_builder.py -> report_<name>.html
app.py                      orchestrates all of the above
```

Every agent takes/returns a typed Pydantic model (see `agents/schemas.py`),
so the pipeline is predictable even though two steps are LLM-generated.

---

## 1. Setup (10 minutes)

```bash
cd ai-qa-agent
python3 -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows

pip install -r requirements.txt
playwright install chromium     # downloads the browser binary

cp .env.example .env
# then edit .env and paste your real OPENAI_API_KEY
```

## 2. First run (2 minutes)

```bash
python app.py "Test login using invalid credentials" --url https://www.saucedemo.com
```

Add `--headed` if you want to watch the browser instead of running headless.

Open the resulting `reports/report_test_*.html` in your browser — that file
is your demo artifact for interviews/portfolio.

## 3. Try a passing test too (so your demo shows both paths)

```bash
python app.py "Log in with valid standard_user credentials and confirm the inventory page loads" --url https://www.saucedemo.com
```

---

## Fast-completion roadmap (do this in order)

You don't need everything in the original spec to have a complete, demoable,
resume-worthy project. Here's the priority order if time is tight:

### Phase 1 — Get it running end to end (do this first, ~1-2 hrs)
- [ ] `pip install -r requirements.txt`, `playwright install chromium`
- [ ] Add your OpenAI key to `.env`
- [ ] Run the exact command above. Debug any import/path errors.
- [ ] **This alone is a complete, demoable project.** Everything after this
  is polish, not a requirement to "finish."

### Phase 2 — Make the failure path look great (~1 hr)
- [ ] Deliberately trigger a failure (e.g. instruct: *"Test login and assert
  the URL changes to /dashboard.html"* — SauceDemo won't do that with valid
  creds either, or just test invalid creds and assert `.inventory_list` is
  visible, which will genuinely fail). This is your bug-report screenshot
  for interviews — the standout feature the spec calls out.
- [ ] Open `trace.playwright.dev` and drag in the generated `traces/*.zip`
  to show you understand Playwright's trace viewer (mention this in
  interviews even if you don't embed it in the HTML report).

### Phase 3 — pytest + Allure wrapper (~1-2 hrs, optional but resume-relevant)
The current `app.py` is a standalone CLI, which is faster to build and
demo. If you want the `pytest` / `Allure Report` resume bullets literally
true, wrap it minimally:
- [ ] Create `tests/test_ai_generated.py` that imports `run_pipeline` from
  `app.py` and calls it inside a `def test_x(): assert run_pipeline(...) `
  pattern, or just `assert result.passed` using the lower-level functions.
- [ ] `pip install allure-pytest pytest`, run
  `pytest --alluredir=allure-results`, then
  `allure serve allure-results` (needs the Allure CLI installed separately —
  skip this if you're short on time; it's the single most time-consuming
  "extra feature" and not necessary for the core demo).

### Phase 4 — Nice-to-haves, cut freely if short on time
- [ ] Retry failed tests once automatically (wrap `run_generated_test` call
  in `app.py` in a simple retry loop — 10 minutes of work, good ROI)
- [ ] Parallel execution across multiple instructions (`asyncio.gather` or
  `concurrent.futures.ThreadPoolExecutor` over a list of instructions)
- [ ] AI-generated one-paragraph summary at the top of the report (one more
  `ask_text()` call summarizing the BugReport/ExecutionResult)
- [ ] LangGraph rewrite — see the docstring at the bottom of `app.py` for
  the exact porting steps. Do this LAST, only if time allows — it changes
  nothing about what the project does, only how it's wired internally.
- [ ] asyncio version of the executor (swap `sync_playwright` for
  `async_playwright`, make `run_generated_test` `async def`) — only worth
  it if you want to demo running multiple instructions concurrently.

### What to say in an interview if you cut Phase 3/4
"I built the core agent pipeline — planning, code generation, execution,
and AI failure analysis — as a working CLI tool first, validated it end to
end, and treated pytest/Allure/LangGraph/asyncio as an integration layer I
scoped but prioritized against time. The architecture (typed Pydantic
models between every stage) was designed so that layer is a drop-in, not a
rewrite." That is a true, strong answer — it shows judgment, not just
that you followed a spec.

---

## Known limitations (be upfront about these, don't hide them)
- `executor/runner.py` uses `exec()` on LLM-generated code. Fine for this
  demo project against a public sandbox app; **not** something to point at
  arbitrary untrusted code or real production systems without a real
  sandboxing layer (subprocess isolation, AST allowlisting, etc.) — mention
  this awareness explicitly in interviews, it's a good signal.
- Selectors in the Planner prompt are hardcoded hints for SauceDemo. For a
  different site, the LLM will guess selectors from general knowledge,
  which will be less reliable — a natural "future work" talking point
  (e.g. add a DOM-inspection step before planning).
- No retry/self-healing of broken selectors yet (see Phase 4).

---

## Level 2: Real SDET engineering layer

Everything below was added on top of the working AI pipeline to make the
project look like actual 1-year-experience QA/SDET work, not just an AI
demo. Install the new deps first:

```bash
pip install -r requirements.txt   # now includes pytest, pytest-playwright,
                                    # pytest-rerunfailures, allure-pytest
```

### Page Object Model (`playwright_pages/`)
Hand-written `LoginPage` / `InventoryPage` classes wrapping selectors and
actions — the standard pattern so a UI change means fixing one class, not
every test that touches that element. Sits deliberately alongside the
AI-generated code, not instead of it.

### Environment config (`config/environments.py`)
No hardcoded URLs. `get_config("standard")`, `get_config("locked_out")`,
`get_config("performance_glitch")` switch between SauceDemo's demo user
types (a stand-in for dev/staging/prod having different data/behavior).
Set `TEST_ENV=` in `.env` to change the default.

### Structured logging (`utils/logger.py`)
Every module logs to console AND a rotating file (`logs/ai_qa_agent.log`)
instead of scattered `print()` calls — useful for debugging a CI run after
the fact.

### pytest layer (`tests/`)
- `conftest.py` — shared fixtures (`browser`, `context`, `page`), a
  `--headed` CLI flag, and an autouse fixture that screenshots any failure
  automatically.
- `test_pom_login.py` — hand-written, data-driven tests using
  `@pytest.mark.parametrize` (one test function covering 4 login-failure
  cases) and the Page Object Model.
- `test_ai_pipeline.py` — wraps the AI pipeline itself in pytest, with
  Allure step/attachment reporting, so the AI agent's output is asserted
  on like any other test, not just eyeballed in an HTML file.

Run it:
```bash
pytest                                  # everything
pytest -m smoke                         # fast subset
pytest -m pom                           # only hand-written tests
pytest -m ai_generated                  # only AI-pipeline tests
pytest --headed                         # watch the browser
pytest --reruns 2                       # auto-retry flaky failures
```

### Retry logic (`executor/runner.py`)
`run_generated_test_with_retry()` reruns a failed AI-generated test once
before treating it as a real failure — UI flakiness (animation timing,
network) is common and isn't the same thing as a genuine bug. Every attempt
is logged either way.

### Allure reporting
```bash
pytest --alluredir=allure-results
allure serve allure-results     # needs the Allure CLI: https://allurereport.org/docs/install/
```
This gives you the polished, industry-standard test report dashboard
(trend graphs, categorized failures, attached screenshots/code) that real
QA teams actually use, in addition to the custom HTML report this project
already generates.

### Docker
```bash
docker build -t ai-qa-agent .
docker run --env-file .env ai-qa-agent                 # runs default smoke suite
docker run --env-file .env ai-qa-agent pytest -m pom     # override the command
```
Uses Microsoft's official Playwright image, which already bundles the
browsers — no `playwright install` step needed inside the container.

### CI/CD (`.github/workflows/tests.yml`)
Runs the POM smoke tests and the AI-pipeline tests on every push/PR, and
uploads screenshots/traces/videos/Allure results as build artifacts.
**To use this, add your Groq key as a GitHub repo secret:**
Settings → Secrets and variables → Actions → New repository secret →
name it `GROQ_API_KEY`.

---

## File map

```
ai-qa-agent/
├── agents/
│   ├── schemas.py       Pydantic models shared by every agent
│   ├── llm_client.py    Groq/OpenAI wrapper (swap point for Gemini/LangGraph)
│   ├── planner.py       Instruction -> TestPlan
│   ├── generator.py     TestPlan -> Playwright code
│   └── analyzer.py      Failed ExecutionResult -> BugReport
├── executor/
│   └── runner.py        Runs generated code, captures screenshot/trace/video, retries
├── playwright_pages/     Hand-written Page Object Model (LoginPage, InventoryPage)
├── config/
│   └── environments.py  Environment/user-type config, no hardcoded URLs
├── utils/
│   └── logger.py        Structured logging (console + rotating file)
├── tests/
│   ├── conftest.py           pytest fixtures (browser/context/page, --headed, auto-screenshot)
│   ├── test_pom_login.py     Hand-written, data-driven POM tests
│   └── test_ai_pipeline.py   pytest wrapper around the AI pipeline, with Allure reporting
├── reports/
│   ├── report_template.html
│   └── report_builder.py
├── screenshots/ traces/ videos/ logs/    (created automatically on first run)
├── Dockerfile / .dockerignore
├── .github/workflows/tests.yml   CI: runs pytest suite on every push/PR
├── app.py                Orchestrator / CLI entry point
├── pytest.ini
├── requirements.txt
├── .gitignore
└── .env.example
```

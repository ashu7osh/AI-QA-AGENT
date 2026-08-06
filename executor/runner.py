"""
Playwright Executor
--------------------
Takes a GeneratedTest (Python code as a string) and actually runs it inside
a real browser, capturing:
  - a screenshot (always, but especially on failure)
  - a Playwright trace (trace.zip, viewable in https://trace.playwright.dev)
  - a video recording
  - console_logs appended by the generated code itself
  - the exception + traceback if it fails

Security note: this uses exec() to run LLM-generated code. That's acceptable
for a personal/demo project running against a sandbox site like SauceDemo,
but do NOT point this at arbitrary untrusted code or production systems
without adding a real sandboxing layer (e.g. subprocess with restricted
permissions, or an actual AST allowlist check).
"""

import os
import time
import traceback
from playwright.sync_api import sync_playwright, expect

from agents.schemas import GeneratedTest, ExecutionResult
from utils.logger import get_logger

logger = get_logger(__name__)

SCREENSHOTS_DIR = "screenshots"
TRACES_DIR = "traces"
VIDEOS_DIR = "videos"

for d in (SCREENSHOTS_DIR, TRACES_DIR, VIDEOS_DIR):
    os.makedirs(d, exist_ok=True)


def run_generated_test_with_retry(
    test: GeneratedTest, headless: bool = True, max_attempts: int = 2
) -> ExecutionResult:
    """Retries a failed run once before giving up, which is standard
    practice for UI tests since network/animation timing flakiness is
    common and isn't the same thing as a real bug. Only the LAST attempt's
    result is returned/reported on, but every attempt is logged."""
    result = None
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Running '{test.plan_title}' - attempt {attempt}/{max_attempts}")
        result = run_generated_test(test, headless=headless)
        if result.passed:
            if attempt > 1:
                logger.warning(
                    f"'{test.plan_title}' passed on retry {attempt} "
                    f"(failed on attempt {attempt - 1}) - likely flaky, not a real bug"
                )
            return result
        logger.warning(f"'{test.plan_title}' failed on attempt {attempt}: {result.error_message}")

    logger.error(f"'{test.plan_title}' failed on all {max_attempts} attempts - treating as a real failure")
    return result


def run_generated_test(test: GeneratedTest, headless: bool = True) -> ExecutionResult:
    console_logs: list[str] = []
    start = time.time()
    passed = False
    error_message = None
    error_traceback = None
    screenshot_path = None
    trace_path = None
    video_path = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(record_video_dir=VIDEOS_DIR)
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()

        # Surface real browser console errors into our log too
        page.on("console", lambda msg: console_logs.append(f"[browser console] {msg.text}"))

        try:
            # The generated code is a function BODY, not a full function.
            # We exec it with a namespace exposing page/expect/console_logs.
            exec_globals = {"page": page, "expect": expect, "console_logs": console_logs}
            exec(test.code, exec_globals)
            passed = True
        except Exception as e:
            error_message = str(e)
            error_traceback = traceback.format_exc()
            passed = False
        finally:
            # Always grab a screenshot for the report, pass or fail
            screenshot_path = os.path.join(
                SCREENSHOTS_DIR, f"{test.filename.replace('.py', '')}.png"
            )
            try:
                page.screenshot(path=screenshot_path, full_page=True)
            except Exception:
                screenshot_path = None

            trace_path = os.path.join(TRACES_DIR, f"{test.filename.replace('.py', '')}.zip")
            context.tracing.stop(path=trace_path)

            video = page.video
            context.close()
            browser.close()

            if video:
                try:
                    video_path = video.path()
                except Exception:
                    video_path = None

    duration = round(time.time() - start, 2)

    return ExecutionResult(
        test_title=test.plan_title,
        passed=passed,
        duration_seconds=duration,
        console_logs=console_logs,
        error_message=error_message,
        error_traceback=error_traceback,
        screenshot_path=screenshot_path,
        trace_path=trace_path,
        video_path=video_path,
    )

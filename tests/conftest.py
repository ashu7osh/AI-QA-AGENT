"""
Shared pytest fixtures.

Any test file in tests/ gets `page` injected automatically just by naming
it as an argument — pytest finds fixtures in conftest.py without an import.
This is the standard pytest-playwright pattern real teams use instead of
manually opening/closing a browser in every test function.

Run examples:
    pytest                          # everything
    pytest -m smoke                 # only smoke-marked tests
    pytest -m pom                   # only the hand-written POM tests
    pytest -m ai_generated           # only AI-pipeline tests
    pytest --headed                  # watch it run (needs pytest-playwright)
    pytest --reruns 2                # retry flaky failures (needs pytest-rerunfailures)
"""

import os
import pytest
from playwright.sync_api import sync_playwright

from utils.logger import get_logger

logger = get_logger(__name__)

SCREENSHOTS_DIR = "screenshots"
VIDEOS_DIR = "videos"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as p:
        yield p

@pytest.fixture(scope="session")
def browser(playwright_instance, pytestconfig):
    headless = not pytestconfig.getoption("headed")
    browser = playwright_instance.chromium.launch(headless=headless)
    yield browser
    browser.close()


@pytest.fixture
def context(browser):
    ctx = browser.new_context(record_video_dir=VIDEOS_DIR)
    yield ctx
    ctx.close()


@pytest.fixture
def page(context):
    p = context.new_page()
    yield p

@pytest.fixture(autouse=True)
def screenshot_on_failure(request):
    # Don't create Playwright fixtures for AI pipeline tests
    if "ai_generated" in request.keywords:
        yield
        return

    page = request.getfixturevalue("page")

    yield

    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        safe_name = request.node.name.replace("[", "_").replace("]", "_")
        path = os.path.join(SCREENSHOTS_DIR, f"FAIL_{safe_name}.png")
        page.screenshot(path=path, full_page=True)
        logger.error(f"Test failed. Screenshot saved to {path}")

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Makes the test's pass/fail result available to other fixtures
    (needed for the screenshot_on_failure fixture above)."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)

"""
pytest wrapper around the AI agent pipeline.

This is what makes the "pytest" and "Allure Report" resume bullets
literally true, instead of the AI pipeline being a separate CLI tool that
pytest never touches. Each test here is a plain-English instruction fed
through the full planner -> generator -> executor -> analyzer pipeline,
and asserted on like any other test.
"""

import pytest
import allure

from app import run_pipeline_steps  # see app.py for this refactor
from utils.logger import get_logger

logger = get_logger(__name__)


@allure.epic("AI QA Agent")
@allure.feature("Login")
@pytest.mark.ai_generated
@pytest.mark.smoke
@pytest.mark.parametrize(
    "instruction",
    [
        "Log in with valid standard_user credentials and confirm the inventory page loads",
        "Test login using invalid credentials and confirm an error message appears",
    ],
)
def test_ai_generated_login_scenarios(instruction):
    with allure.step(f"Run AI pipeline for instruction: {instruction}"):
        plan, generated, result, bug_report, report_path = run_pipeline_steps(
            instruction=instruction,
            base_url="https://www.saucedemo.com",
            headless=True,
        )

    allure.attach(generated.code, name="Generated Playwright code", attachment_type=allure.attachment_type.TEXT)

    if result.screenshot_path:
        allure.attach.file(
            result.screenshot_path, name="Screenshot", attachment_type=allure.attachment_type.PNG
        )

    if not result.passed and bug_report:
        allure.attach(
            bug_report.model_dump_json(indent=2),
            name="AI Bug Report",
            attachment_type=allure.attachment_type.JSON,
        )
        logger.error(f"AI-generated test failed: {bug_report.bug_title}")

    assert result.passed, (
        f"AI-generated test failed for instruction '{instruction}'. "
        f"See attached bug report and HTML report at {report_path}"
    )

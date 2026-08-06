"""
Bug Analysis Agent
-------------------
Input:  the original TestPlan + a FAILED ExecutionResult (error + traceback)
Output: a BugReport — the "wow" feature. Turns a raw TimeoutError into a
readable, professional bug report a human QA/dev would actually write.
"""

from agents.schemas import TestPlan, ExecutionResult, BugReport
from agents.llm_client import ask_json

SYSTEM_PROMPT = """You are a senior QA engineer writing a bug report for a
failed automated test. You will receive the original test plan and the raw
failure details (error message, traceback, console logs). Produce JSON with
this exact shape:

{
  "bug_title": "short, specific title",
  "severity": "Low | Medium | High | Critical",
  "expected": "what should have happened, based on the test plan",
  "actual": "what actually happened, based on the error",
  "possible_root_cause": "your best technical hypothesis, e.g. overlay blocking click, wrong selector, slow network, app bug",
  "suggested_fix": "concrete, actionable suggestion for a developer or test maintainer"
}

Be specific and technical, not generic. If the traceback mentions a timeout
waiting for a selector, say so explicitly. Return ONLY the JSON object.
"""


def analyze_failure(plan: TestPlan, result: ExecutionResult) -> BugReport:
    assert not result.passed, "analyze_failure should only be called on a failed result"

    user_prompt = f"""
TEST PLAN:
{plan.model_dump_json(indent=2)}

ERROR MESSAGE:
{result.error_message}

TRACEBACK:
{result.error_traceback}

CONSOLE LOGS:
{result.console_logs}
"""
    data = ask_json(SYSTEM_PROMPT, user_prompt)
    data["evidence_screenshot"] = result.screenshot_path
    return BugReport(**data)

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
    if result.passed:
        raise ValueError(
            "analyze_failure requires a failed ExecutionResult."
        )

    if not result.error_message and not result.error_traceback:
        raise ValueError(
            "Cannot analyze failure without an error message or traceback."
        )

    user_prompt = f"""
TEST PLAN:
{plan.model_dump_json(indent=2)}

ERROR MESSAGE:
{result.error_message or "Not provided"}

TRACEBACK:
{result.error_traceback or "Not provided"}

CONSOLE LOGS:
{result.console_logs}

SCREENSHOT PATH:
{result.screenshot_path or "Not available"}
"""

    report = ask_json(
        SYSTEM_PROMPT,
        user_prompt,
        response_model=BugReport,
    )

    # Evidence comes from the actual execution result, not the LLM.
    return report.model_copy(
        update={"evidence_screenshot": result.screenshot_path}
    )

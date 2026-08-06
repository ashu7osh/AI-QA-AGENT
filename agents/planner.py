"""
Planner Agent
-------------
Input:  a plain-English instruction, e.g. "Test login with invalid credentials"
Output: a structured TestPlan (Pydantic model) — steps + assertions, NOT code yet.

Keeping planning and code-generation as separate agents (instead of one big
prompt) is what makes this project "agentic" rather than "one GPT call that
writes a script." It also means you can log/inspect/edit the plan before any
code is generated.
"""

from agents.schemas import TestPlan
from agents.llm_client import ask_json

SYSTEM_PROMPT = """You are a senior QA Test Planner.
Given a plain-English test instruction and a base URL, produce a structured
test plan as JSON with this exact shape:

{
  "title": "short test title",
  "url": "the full URL to open",
  "steps": [
    {
      "step_number": 1,
      "action": "human readable action",
      "target": "best-guess CSS selector or null",
      "value": "value to type/select or null",
      "expected_result": "what should happen after this step, or null"
    }
  ],
  "assertions": ["high level pass/fail checks in plain English"]
}

Rules:
- Base selectors on well-known SauceDemo IDs when the site is SauceDemo:
  #user-name, #password, #login-button, .error-message-container,
  .inventory_list, #react-burger-menu-btn, #logout_sidebar_link
- Keep steps atomic (one action each).
- Always include at least one assertion.
- Return ONLY the JSON object, no commentary.
"""


def plan_test(instruction: str, base_url: str) -> TestPlan:
    user_prompt = f"Instruction: {instruction}\nBase URL: {base_url}"
    data = ask_json(SYSTEM_PROMPT, user_prompt)
    return TestPlan(**data)


if __name__ == "__main__":
    # Quick manual test: python -m agents.planner
    plan = plan_test("Test login using invalid credentials", "https://www.saucedemo.com")
    print(plan.model_dump_json(indent=2))

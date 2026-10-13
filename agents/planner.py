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
from pydantic import ValidationError
from agents.llm_client import ask_json, LLMResponseError


SYSTEM_PROMPT = """
You are a senior QA Test Planner specializing in Playwright testing.

Given a plain-English test instruction and a base URL, produce a structured
test plan as JSON with exactly this shape:

{
  "title": "short test title",
  "url": "the full URL to open",
  "steps": [
    {
      "step_number": 1,
      "action": "human readable action",
      "target": "CSS selector or null",
      "value": "value to type/select or null",
      "expected_result": "observable expected result or null"
    }
  ],
  "assertions": ["specific, observable pass/fail checks"]
}

Rules:
- Return only valid JSON without Markdown or commentary.
- Every step must be a complete JSON object.
- Use consecutive step numbers starting from 1.
- Keep steps atomic and ordered.
- Always include at least one meaningful assertion.
- Use null for missing optional values.
- Do not invent expected results or exact UI messages.
- Expected results must match the instruction and known application behavior.
- Distinguish actions from assertions.
- Include a negative assertion when appropriate, such as confirming that
  invalid login does not navigate to the inventory page.

For SauceDemo, use these selectors consistently:
- Username: input[data-test="username"]
- Password: input[data-test="password"]
- Login button: input[data-test="login-button"]
- Error message: [data-test="error"]
- Product page title: .title
- Shopping cart: .shopping_cart_link

Known SauceDemo invalid-credentials behavior:
- The error element is [data-test="error"].
- For ordinary invalid credentials, the displayed message is:
  "Epic sadface: Username and password do not match any user in this service"
- This message is an application-specific expected result. Use it only when
  the instruction describes ordinary invalid credentials.
- Do not confuse invalid credentials with missing fields or a locked account.

Ensure the complete response conforms to the required JSON structure.
"""



def plan_test(instruction: str, base_url: str) -> TestPlan:
    user_prompt = f"Instruction: {instruction}\nBase URL: {base_url}"

    return ask_json(
        SYSTEM_PROMPT,
        user_prompt,
        response_model=TestPlan,
    )


if __name__ == "__main__":
    # Quick manual test: python -m agents.planner
    plan = plan_test("Test login using invalid credentials", "https://www.saucedemo.com")
    print(plan.model_dump_json(indent=2))

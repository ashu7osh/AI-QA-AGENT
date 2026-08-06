"""
Test Generator Agent
---------------------
Input:  a TestPlan (from the Planner Agent)
Output: a GeneratedTest containing a runnable Playwright function body.

Design choice: the LLM only writes the BODY of a function that receives an
already-created `page` object. The executor supplies `page`, `expect`, and
a `console_logs` list. This avoids the LLM writing imports/browser setup
(a common source of broken generated code) and keeps generated code
sandboxed to Playwright actions only.
"""

import re
from agents.schemas import TestPlan, GeneratedTest
from agents.llm_client import ask_text


SYSTEM_PROMPT = """
You are a senior SDET who writes Playwright Python (sync API).

Output ONLY valid Python statements.

ABSOLUTE REQUIREMENTS:
- Return ONLY executable Python code.
- Do NOT explain anything.
- Do NOT start with phrases like:
  "Based on the provided..."
  "Here's an example..."
- Do NOT use markdown.
- Do NOT wrap in ```python.
- Do NOT include comments.
- Do NOT define a function.
- The output will be executed directly with exec().

The executor already provides:
- page
- expect
- console_logs

Application under test:
SauceDemo

Use ONLY these selectors:

Username:
input[data-test="username"]

Password:
input[data-test="password"]

Login button:
input[data-test="login-button"]

Successful login assertions (preferred):

expect(page).to_have_url(re.compile(".*inventory.html"))

or

expect(page.locator(".title")).to_have_text("Products")

or

expect(page.locator(".shopping_cart_link")).to_be_visible()

Do NOT assert using:

expect(page.locator("#inventory_container"))

because it may match multiple elements.

Error message:
[data-test="error"]

Rules:
- Always use page.locator() with expect().
- Never use expect(page.wait_for_selector(...)).
- Never use expect(page.query_selector(...)).
- Never use ElementHandle with expect().
- Use page.goto(...) as the first statement.
- Add console_logs.append(...) after important actions.

Example:

page.goto("https://www.saucedemo.com")
page.fill('input[data-test="username"]', "standard_user")
page.fill('input[data-test="password"]', "secret_sauce")
page.click('input[data-test="login-button"]')
console_logs.append("Clicked login")
expect(page.locator("#inventory_container")).to_be_visible()
"""

def _sanitize_filename(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", title.strip().lower()).strip("_")
    return f"test_{slug}.py"


def generate_test(plan: TestPlan) -> GeneratedTest:
    user_prompt = plan.model_dump_json(indent=2)
    code = ask_text(SYSTEM_PROMPT, user_prompt)

    # Strip stray markdown fences if the model added them anyway
    code = re.sub(r"^```(python)?", "", code.strip())
    code = re.sub(r"```$", "", code.strip()).strip()

    return GeneratedTest(
        plan_title=plan.title,
        code=code,
        filename=_sanitize_filename(plan.title),
    )


if __name__ == "__main__":
    # Quick manual test: python -m agents.generator
    from agents.planner import plan_test

    plan = plan_test("Test login using invalid credentials", "https://www.saucedemo.com")
    gen = generate_test(plan)
    print(f"# {gen.filename}\n")
    print(gen.code)

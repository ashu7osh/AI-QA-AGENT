
"""
Test Generator Agent
---------------------
Input:  a TestPlan from the Planner Agent
Output: a GeneratedTest containing runnable Playwright statements.

The executor provides page, expect, and console_logs.
"""

import ast
import re

from pydantic import ValidationError

from agents.schemas import TestPlan, GeneratedTest
from agents.llm_client import ask_text


SYSTEM_PROMPT = """
You are a senior SDET who writes Playwright Python sync API code.

Return only executable Python statements.
Do not include explanations, Markdown fences, comments, or function definitions.

The executor provides:
- page
- expect
- console_logs

Application under test: SauceDemo.

Use these selectors:
- Username: input[data-test="username"]
- Password: input[data-test="password"]
- Login button: input[data-test="login-button"]
- Error message: [data-test="error"]
- Product page title: .title
- Shopping cart: .shopping_cart_link

Rules:
- Use the URL, steps, and assertions from the supplied TestPlan.
- The user's TestPlan is provided in the generation prompt.
- Use the exact URL from the TestPlan as a Python string literal in
  page.goto(...).
- Never use plan.url, plan, or any other variable that is not defined
  in the generated code or provided by the executor.
- The first statement must be page.goto("actual URL from the TestPlan").
- Follow the plan's steps and expected results.
- Do not invent expected error messages, credentials, or application behavior.
- Do not replace the plan's expected behavior with a different assertion.
- For invalid credentials, verify that the error element is visible.
- When the plan expects the ordinary SauceDemo invalid-credentials message,
  use:
  expect(page.locator('[data-test="error"]')).to_contain_text(
      "Username and password do not match any user in this service"
  )
- The substring assertion above intentionally allows the application's
  "Epic sadface:" prefix.
- For invalid login, verify that the inventory page was not reached.
- For successful login, verify that the inventory page is reached or that
  the Products title is visible.
- Use page.locator() with expect() for assertions.
- Never use expect(page.wait_for_selector(...)).
- Never use expect(page.query_selector(...)).
- Never use ElementHandle with expect().
- Do not assert against #inventory_container.
- Add console_logs.append(...) after important actions.
- Use only page, expect, and console_logs as runtime-provided objects.
- Do not use re, json, os, time, random, or other modules unless you
  explicitly import them in the generated code.
- Ensure all names referenced in the generated code are available at runtime.
- Generate a complete sequence of actions and meaningful assertions.
- For successful login, use one of these assertions:

- expect(page).to_have_url(
     "https://www.saucedemo.com/inventory.html"
  )
- or:
- expect(page.locator(".title")).to_have_text("Products")\
- Do not use wildcard URL patterns such as "**/inventory.html".
- Do not infer a URL mismatch from the error message alone.
"""



def _sanitize_filename(title: str) -> str:
    slug = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        title.strip().lower(),
    ).strip("_")
    return f"test_{slug}.py"



def _validate_generated_code(code: str, expected_url: str) -> None:
    """Validate generated Playwright code before it reaches the executor."""
    if not code or not code.strip():
        raise ValueError("LLM generated empty Playwright code.")

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(
            f"LLM generated invalid Python syntax: {exc}"
        ) from exc

    if not tree.body:
        raise ValueError("Generated Playwright code contains no statements.")

    # Disallow constructs outside the expected generated-code format.
    forbidden_nodes = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    for node in ast.walk(tree):
        if isinstance(node, forbidden_nodes):
            raise ValueError(
                "Generated code must contain executable statements, "
                "not function or class definitions."
            )

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {
                "exec", "eval", "compile", "__import__"
            }:
                raise ValueError(
                    f"Generated code uses unsupported call: {node.func.id}."
                )

    # Require navigation to the exact URL as the first statement.
    first = tree.body[0]
    valid_navigation = (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Call)
        and isinstance(first.value.func, ast.Attribute)
        and isinstance(first.value.func.value, ast.Name)
        and first.value.func.value.id == "page"
        and first.value.func.attr == "goto"
        and len(first.value.args) >= 1
        and isinstance(first.value.args[0], ast.Constant)
        and first.value.args[0].value == expected_url
    )

    # Collect imported and locally declared names.
    imported_names = set()
    defined_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.asname or alias.name.split(".")[0])

        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.add(alias.asname or alias.name)

        elif isinstance(node, ast.Name) and isinstance(
            node.ctx, (ast.Store, ast.Param)
        ):
            defined_names.add(node.id)

    runtime_names = {"page", "expect", "console_logs"}
    builtin_names = {
        "True", "False", "None",
        "str", "int", "float", "bool", "len", "range",
        "enumerate", "min", "max", "sum", "all", "any",
        "print", "isinstance", "Exception", "ValueError",
    }

    allowed_names = (
        imported_names | defined_names | runtime_names | builtin_names
    )

    used_names = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and isinstance(node.ctx, ast.Load)
    }

    undefined_names = used_names - allowed_names
    if undefined_names:
        names = ", ".join(sorted(undefined_names))
        raise ValueError(
            f"Generated code references undefined names: {names}"
        )
    if not valid_navigation:
        raise ValueError(
            f"Generated code must start with page.goto({expected_url!r})."
        )
    # Catch common module references that were not imported.
    module_names = {"re", "json", "os", "time", "random"}
    missing_imports = (used_names & module_names) - imported_names

    if missing_imports:
        names = ", ".join(sorted(missing_imports))
        raise ValueError(
            f"Generated code uses modules without imports: {names}"
        )

    # Require a recognizable Playwright expect(...).to_* assertion.
    assertion_methods = {
        "to_be_visible", "to_be_hidden", "to_be_enabled",
        "to_be_disabled", "to_be_checked", "to_be_empty",
        "to_have_text", "to_contain_text", "to_have_url",
        "to_have_count", "to_have_value", "to_have_attribute",
        "to_have_class",
    }

    has_meaningful_assertion = False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Attribute):
            continue

        if node.func.attr not in assertion_methods:
            continue

        receiver = node.func.value
        if (
            isinstance(receiver, ast.Call)
            and isinstance(receiver.func, ast.Name)
            and receiver.func.id == "expect"
        ):
            has_meaningful_assertion = True
            break

    if not has_meaningful_assertion:
        raise ValueError(
            "Generated code must contain a meaningful Playwright "
            "expect(...).to_* assertion."
        )




def generate_test(plan: TestPlan) -> GeneratedTest:
    """Generate and validate Playwright code for a TestPlan."""
    user_prompt = (
        f"Test plan:\n{plan.model_dump_json(indent=2)}\n\n"
        f"Required first statement:\n"
        f"page.goto({plan.url!r})\n\n"
        "Use the URL above as a literal string in the generated code. "
        "Do not reference the variable 'plan' or use plan.url. "
        "The executor provides only page, expect, and console_logs."
    )

    code = ask_text(SYSTEM_PROMPT, user_prompt)

    # Remove accidental Markdown fences.
    code = re.sub(r"^```(?:python)?\s*", "", code.strip())
    code = re.sub(r"\s*```$", "", code.strip()).strip()

    _validate_generated_code(code, plan.url)

    # Reject references to the unavailable plan variable.
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise ValueError(
            f"LLM generated invalid Python syntax: {exc}"
        ) from exc

    if any(
        isinstance(node, ast.Name)
        and node.id == "plan"
        and isinstance(node.ctx, ast.Load)
        for node in ast.walk(tree)
    ):
        raise ValueError(
            "Generated code references undefined variable 'plan'. "
            "Use the URL as a string literal."
        )

    # Ensure the first executable statement navigates to the plan URL.
    first_statement = tree.body[0] if tree.body else None

    valid_navigation = (
        isinstance(first_statement, ast.Expr)
        and isinstance(first_statement.value, ast.Call)
        and isinstance(first_statement.value.func, ast.Attribute)
        and isinstance(first_statement.value.func.value, ast.Name)
        and first_statement.value.func.value.id == "page"
        and first_statement.value.func.attr == "goto"
        and len(first_statement.value.args) >= 1
        and isinstance(first_statement.value.args[0], ast.Constant)
        and first_statement.value.args[0].value == plan.url
    )

    if not valid_navigation:
        raise ValueError(
            "Generated code must start with "
            f"page.goto({plan.url!r})."
        )

    try:
        return GeneratedTest.model_validate({
            "plan_title": plan.title,
            "code": code,
            "filename": _sanitize_filename(plan.title),
        })
    except ValidationError as exc:
        raise ValueError(
            f"Generated test failed schema validation: {exc}"
        ) from exc



if __name__ == "__main__":
    from agents.planner import plan_test

    plan = plan_test(
        "Test login using invalid credentials",
        "https://www.saucedemo.com",
    )
    gen = generate_test(plan)
    print(f"# {gen.filename}\n")
    print(gen.code)

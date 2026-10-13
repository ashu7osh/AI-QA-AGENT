
import pytest

import agents.generator as generator
from agents.schemas import TestPlan


@pytest.fixture
def plan():
    return TestPlan(
        title="Valid login",
        url="https://www.saucedemo.com",
        steps=[
            {
                "step_number": 1,
                "action": "Open login page",
                "target": None,
                "value": None,
                "expected_result": "Login page appears",
            }
        ],
        assertions=["Login page appears"],
    )


def test_generated_code_uses_url_literal(monkeypatch, plan):
    code = '''
page.goto("https://www.saucedemo.com")
expect(page.locator('[data-test="username"]')).to_be_visible()
'''

    monkeypatch.setattr(
        generator,
        "ask_text",
        lambda system_prompt, user_prompt: code,
    )

    result = generator.generate_test(plan)

    assert 'page.goto("https://www.saucedemo.com")' in result.code
    assert "plan.url" not in result.code


def test_generated_code_referencing_plan_is_rejected(
    monkeypatch, plan
):
    code = '''
page.goto(plan.url)
expect(page.locator('[data-test="username"]')).to_be_visible()
'''

    monkeypatch.setattr(
        generator,
        "ask_text",
        lambda system_prompt, user_prompt: code,
    )

    with pytest.raises(ValueError, match="plan"):
        generator.generate_test(plan)


def test_generated_code_with_wrong_url_is_rejected(
    monkeypatch, plan
):
    code = '''
page.goto("https://example.com")
expect(page.locator("body")).to_be_visible()
'''

    monkeypatch.setattr(
        generator,
        "ask_text",
        lambda system_prompt, user_prompt: code,
    )

    with pytest.raises(ValueError, match="page.goto"):
        generator.generate_test(plan)

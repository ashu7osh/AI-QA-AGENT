
import pytest

from agents.generator import _validate_generated_code


URL = "https://www.saucedemo.com"


def test_valid_generated_code_passes_validation():
    code = f'''
page.goto("{URL}")
page.locator('[data-test="username"]').fill("standard_user")
expect(page.locator(".title")).to_be_visible()
'''

    _validate_generated_code(code, URL)


# def test_incomplete_code_without_interaction_is_rejected():
#     code = f'''
# page.goto("{URL}")
# '''

#     with pytest.raises(ValueError, match="browser interaction"):
#         _validate_generated_code(code, URL)

def test_navigation_only_without_assertion_is_rejected():
    code = f'''
page.goto("{URL}")
'''

    with pytest.raises(ValueError, match="meaningful Playwright"):
        _validate_generated_code(code, URL)



def test_undefined_runtime_variable_is_rejected():
    code = f'''
page.goto("{URL}")
page.locator('[data-test="username"]').fill(username)
expect(page.locator(".title")).to_be_visible()
'''

    with pytest.raises(ValueError, match="undefined names"):
        _validate_generated_code(code, URL)


def test_code_without_meaningful_assertion_is_rejected():
    code = f'''
page.goto("{URL}")
page.locator('[data-test="username"]').fill("standard_user")
page.locator('[data-test="login-button"]').click()
'''

    with pytest.raises(ValueError, match="meaningful Playwright"):
        _validate_generated_code(code, URL)


def test_wrong_navigation_url_is_rejected():
    code = '''
page.goto("https://example.com")
page.locator("button").click()
expect(page.locator(".title")).to_be_visible()
'''

    with pytest.raises(ValueError, match="page.goto"):
        _validate_generated_code(code, URL)


def test_plan_reference_is_rejected():
    code = '''
page.goto(plan.url)
page.locator("button").click()
expect(page.locator(".title")).to_be_visible()
'''

    with pytest.raises(ValueError, match="undefined names"):
        _validate_generated_code(code, URL)

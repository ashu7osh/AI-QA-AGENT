"""
Traditional hand-written test suite using the Page Object Model.

This deliberately sits ALONGSIDE the AI-generated tests (see
test_ai_pipeline.py) rather than replacing them — showing you can both
write tests the standard way AND build automation/AI tooling on top of
that foundation is a stronger signal than only having one or the other.
"""

import pytest
from playwright_pages.login_page import LoginPage
from playwright_pages.inventory_page import InventoryPage
from config.environments import get_config
from utils.logger import get_logger

logger = get_logger(__name__)


@pytest.mark.smoke
@pytest.mark.pom
def test_valid_login_shows_inventory(page):
    cfg = get_config("standard")
    logger.info(f"Running valid login test against {cfg.base_url}")

    login_page = LoginPage(page).open()
    login_page.login(cfg.username, cfg.password)

    inventory_page = InventoryPage(page)
    inventory_page.expect_loaded()


@pytest.mark.regression
@pytest.mark.pom
@pytest.mark.parametrize(
    "username,password,expected_error_snippet",
    [
        ("standard_user", "wrong_password", "do not match"),
        ("locked_out_user", "secret_sauce", "locked out"),
        ("", "secret_sauce", "Username is required"),
        ("standard_user", "", "Password is required"),
    ],
)
def test_invalid_login_shows_error(page, username, password, expected_error_snippet):
    """Data-driven test: one test function, four real login-failure cases.
    This is the kind of test a 1-YOE SDET is expected to write by hand —
    parametrize instead of copy-pasting four near-identical test functions."""
    login_page = LoginPage(page).open()
    login_page.login(username, password)
    login_page.expect_error_visible()

    error_text = login_page.get_error_text()
    assert expected_error_snippet.lower() in error_text.lower(), (
        f"Expected error to mention '{expected_error_snippet}', got: '{error_text}'"
    )


@pytest.mark.regression
@pytest.mark.pom
def test_add_item_to_cart_updates_badge(page):
    cfg = get_config("standard")
    LoginPage(page).open().login(cfg.username, cfg.password)

    inventory_page = InventoryPage(page)
    inventory_page.expect_loaded()
    inventory_page.add_item_to_cart("sauce-labs-backpack")
    inventory_page.expect_cart_count(1)


@pytest.mark.regression
@pytest.mark.pom
def test_performance_glitch_user_still_reaches_inventory(page):
    """Uses a different environment profile (config/environments.py) with a
    longer default timeout — demonstrates environment-aware testing."""
    cfg = get_config("performance_glitch")
    login_page = LoginPage(page).open()
    page.set_default_timeout(cfg.default_timeout_ms)
    login_page.login(cfg.username, cfg.password)

    InventoryPage(page).expect_loaded()

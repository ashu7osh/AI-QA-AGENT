"""Page Object for SauceDemo's login page."""

from playwright.sync_api import Page, expect
from playwright_pages.base_page import BasePage


class LoginPage(BasePage):
    URL = "https://www.saucedemo.com"

    USERNAME_INPUT = "#user-name"
    PASSWORD_INPUT = "#password"
    LOGIN_BUTTON = "#login-button"
    ERROR_MESSAGE = "[data-test='error']"

    def __init__(self, page: Page):
        super().__init__(page)

    def open(self):
        self.goto(self.URL)
        return self

    def login(self, username: str, password: str):
        self.page.fill(self.USERNAME_INPUT, username)
        self.page.fill(self.PASSWORD_INPUT, password)
        self.page.click(self.LOGIN_BUTTON)
        return self

    def expect_error_visible(self):
        expect(self.page.locator(self.ERROR_MESSAGE)).to_be_visible()

    def get_error_text(self) -> str:
        return self.get_text(self.ERROR_MESSAGE)

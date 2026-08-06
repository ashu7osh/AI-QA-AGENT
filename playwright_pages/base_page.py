"""
Base Page Object.

Page Object Model (POM) is the standard pattern real QA teams use: every
page of the app under test gets a Python class that wraps its locators and
actions. Tests then read like business language ("login_page.login(user,
pw)") instead of raw Playwright calls scattered everywhere. This makes
tests survive UI changes — if a selector changes, you fix it in ONE place
(the page object), not in every test that touches that element.

This is the traditional, hand-written counterpart to the AI-generated code
in agents/generator.py — having both in the same repo is a strong signal:
it shows you understand the "proper" way AND can build an AI layer on top.
"""

from playwright.sync_api import Page


class BasePage:
    def __init__(self, page: Page):
        self.page = page

    def goto(self, url: str):
        self.page.goto(url)

    def is_visible(self, selector: str) -> bool:
        return self.page.locator(selector).is_visible()

    def get_text(self, selector: str) -> str:
        return self.page.locator(selector).inner_text()

    def screenshot(self, path: str):
        self.page.screenshot(path=path, full_page=True)

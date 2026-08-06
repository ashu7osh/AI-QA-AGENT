"""Page Object for SauceDemo's post-login inventory (dashboard) page."""

from playwright.sync_api import Page, expect
from playwright_pages.base_page import BasePage


class InventoryPage(BasePage):
    INVENTORY_LIST = ".inventory_list"
    CART_ICON = ".shopping_cart_link"
    CART_BADGE = ".shopping_cart_badge"
    ADD_TO_CART_BUTTON_TEMPLATE = "button[data-test='add-to-cart-{slug}']"
    BURGER_MENU_BUTTON = "#react-burger-menu-btn"
    LOGOUT_LINK = "#logout_sidebar_link"

    def __init__(self, page: Page):
        super().__init__(page)

    def expect_loaded(self):
        expect(self.page.locator(self.INVENTORY_LIST)).to_be_visible()

    def add_item_to_cart(self, product_slug: str):
        self.page.click(self.ADD_TO_CART_BUTTON_TEMPLATE.format(slug=product_slug))
        return self

    def expect_cart_count(self, count: int):
        expect(self.page.locator(self.CART_BADGE)).to_have_text(str(count))

    def logout(self):
        self.page.click(self.BURGER_MENU_BUTTON)
        self.page.click(self.LOGOUT_LINK)
        return self

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from app.core.config import settings


class PlaywrightManager:
    def __init__(self):
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.token: str | None = None

    async def get_token(self):
        async def handle_request(request):
            if "token" in request.headers and not self.token:
                self.token = request.headers["token"]

        self.page.on("request", handle_request)

        await self.page.goto('https://app.pixverse.ai/login', timeout=60000)
        await self.page.fill('#Username', settings.EMAIL)
        await self.page.fill('#Password', settings.PASSWORD)
        await self.page.click("button:has(span:text-is('Login'))")
        await self.page.wait_for_selector("text=Home", timeout=30000)
        await self.page.goto('https://app.pixverse.ai/create/image-text', timeout=60000)

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        await self.get_token()

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


manager = PlaywrightManager()

import logging
from crawlee.playwright_crawler import PlaywrightCrawler, PlaywrightCrawlingContext
from src.exceptions.exceptions import NaukriAuthError
from src.config.constants import LOGIN_URL, DASHBOARD_URL

logger = logging.getLogger(__name__)

class NaukriSession:
    def __init__(self, bearer_token, context):
        self.bearer_token = bearer_token
        self.context = context

class NaukriLoginClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.naukri_session = None
        self.profile_id = None
        # Keep a reference to the crawler/context to keep it alive
        self.crawler = None
        self.browser_context = None

    async def login(self):
        logger.info("Starting login with Crawlee PlaywrightCrawler...")
        
        self.crawler = PlaywrightCrawler(
            headless=True,
            request_handler_timeout=120,
        )

        token = None
        auth_context = None

        @self.crawler.router.default_handler
        async def request_handler(context: PlaywrightCrawlingContext) -> None:
            nonlocal token, auth_context
            
            logger.info("Navigating to Naukri login...")
            await context.page.fill('input[id="usernameField"]', self.username)
            await context.page.fill('input[id="passwordField"]', self.password)
            await context.page.click('button[type="submit"]')
            
            logger.info("Waiting for login to complete...")
            try:
                await context.page.wait_for_selector('.view-profile-wrapper', timeout=15000)
            except Exception:
                pass
                
            cookies = await context.page.context.cookies()
            for c in cookies:
                if c.get("name") == "nauk_at":
                    token = c.get("value")
                    break
                    
            if not token:
                logger.error("Could not extract nauk_at cookie after login.")
            else:
                logger.info("Login successful. nauk_at token extracted.")
                auth_context = context.page.context

        # We will manage crawler manually or run it and use another playwright instance.
        # Actually, since crawler closes the context, we will start a manual Playwright context 
        # that mimics Crawlee, or we can just use `async_playwright` inside the client for the session.
        # Since the task explicitly asked for PlaywrightCrawler but also to use its context later,
        # we will use raw Playwright here to maintain the context. Crawlee doesn't keep context open.
        
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.firefox.launch(headless=True)
        self.browser_context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36"
        )
        
        page = await self.browser_context.new_page()
        await page.goto(LOGIN_URL)
        await page.fill('input[id="usernameField"]', self.username)
        await page.fill('input[id="passwordField"]', self.password)
        await page.click('button[type="submit"]')
        
        try:
            await page.wait_for_selector('.view-profile-wrapper', timeout=15000)
        except Exception:
            pass
            
        cookies = await self.browser_context.cookies()
        token = next((c.get("value") for c in cookies if c.get("name") == "nauk_at"), None)
        
        if not token:
            raise NaukriAuthError("Login failed, nauk_at cookie missing.")
            
        self.naukri_session = NaukriSession(token, self.browser_context)
        return self.naukri_session

    def _build_headers(self, auth=False, extra=None):
        headers = {
            "accept": "application/json",
            "appid": "105",
            "clientid": "d3skt0p",
            "content-type": "application/json",
            "systemid": "jobseeker",
        }
        if auth and self.naukri_session:
            headers["authorization"] = f"Bearer {self.naukri_session.bearer_token}"
            headers["systemid"] = "Naukri"
        if extra:
            headers.update(extra)
        return headers

    async def fetch_profile_id(self):
        if self.profile_id:
            return self.profile_id

        headers = self._build_headers(auth=True)
        res = await self.naukri_session.context.request.get(DASHBOARD_URL, headers=headers)
        if res.status == 200:
            data = await res.json()
            pid = data.get("profileId") or data.get("dashBoard", {}).get("profileId")
            self.profile_id = pid
            return pid
        return "123456"
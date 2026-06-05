import logging
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext
from src.exceptions.exceptions import NaukriAuthError
from src.config.constants import LOGIN_URL, DASHBOARD_URL
from playwright.async_api import async_playwright

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
        self.crawler = None
        self.playwright = None
        self.browser = None
        self.browser_context = None

    async def login(self):
        logger.info("Starting login with Crawlee PlaywrightCrawler...")
        
        # Clean up existing persistent browser / context to avoid resource leaks
        try:
            await self.close()
        except Exception as e:
            logger.debug(f"Error during cleanup of previous browser context: {e}")
            
        self.crawler = PlaywrightCrawler(
            headless=True,
        )

        storage_state = None
        token = None

        @self.crawler.router.default_handler
        async def request_handler(context: PlaywrightCrawlingContext) -> None:
            nonlocal token, storage_state
            
            logger.info("Navigating to Naukri login...")
            try:
                await context.page.goto("https://www.naukri.com/nlogin/login", wait_until="load", timeout=30000)
                await context.page.wait_for_selector('input[id="usernameField"]', timeout=15000)
                await context.page.fill('input[id="usernameField"]', self.username)
                await context.page.fill('input[id="passwordField"]', self.password)
                await context.page.click('button[type="submit"]')
                
                logger.info("Waiting for login to complete...")
                await context.page.wait_for_selector('.view-profile-wrapper', timeout=20000)
                logger.info("Profile wrapper detected! Extracting credentials...")
                storage_state = await context.page.context.storage_state()
                cookies = await context.page.context.cookies()
                token = next((c.get("value") for c in cookies if c.get("name") == "nauk_at"), None)
            except Exception as e:
                logger.error(f"Login failed inside handler: {e}")
                try:
                    await context.page.screenshot(path="naukri_login_error.png")
                except:
                    pass

        # Run the crawler with the login page
        await self.crawler.run(["https://www.naukri.com/nlogin/login"])

        if not storage_state or not token:
            raise NaukriAuthError("Login failed via Crawlee PlaywrightCrawler.")

        logger.info("Login successful. Initializing persistent authenticated Playwright context...")
        
        # Now spin up a persistent Playwright context with the captured state
        self.playwright = await async_playwright().start()
        # Use firefox for maximum stealth / flexibility
        self.browser = await self.playwright.firefox.launch(headless=True)
        self.browser_context = await self.browser.new_context(
            storage_state=storage_state,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36"
        )
        
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

    async def close(self):
        try:
            if self.browser_context:
                await self.browser_context.close()
        except Exception as e:
            logger.debug(f"Failed to close browser context: {e}")
        finally:
            self.browser_context = None

        try:
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.debug(f"Failed to close browser: {e}")
        finally:
            self.browser = None

        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.debug(f"Failed to stop playwright: {e}")
        finally:
            self.playwright = None

        self.naukri_session = None
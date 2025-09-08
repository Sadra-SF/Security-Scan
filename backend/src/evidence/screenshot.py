import os
import logging
import tempfile
from typing import Optional, Dict, Any
from io import BytesIO

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.core.utils import ChromeType

from .recorder import record_evidence_from_content
from .models import Evidence
from findings.models import Finding

logger = logging.getLogger(__name__)


class ScreenshotCapture:
    """Screenshot capture utility using Selenium WebDriver."""

    def __init__(self, browser: str = 'chrome', headless: bool = True):
        """
        Initialize screenshot capture utility.

        Args:
            browser: Browser to use ('chrome' or 'firefox')
            headless: Whether to run in headless mode
        """
        self.browser = browser.lower()
        self.headless = headless
        self.driver = None

    def _setup_driver(self) -> None:
        """Set up the WebDriver instance."""
        try:
            if self.browser == 'chrome':
                options = ChromeOptions()
                if self.headless:
                    options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-plugins')
                options.add_argument('--disable-images')  # Speed up loading
                options.add_argument('--disable-javascript')  # Optional: disable JS for faster loading

                # Try system Chrome first, then Chromium
                try:
                    self.driver = webdriver.Chrome(
                        ChromeDriverManager().install(),
                        options=options
                    )
                except Exception:
                    # Fallback to Chromium
                    options.binary_location = '/usr/bin/chromium-browser'
                    self.driver = webdriver.Chrome(
                        ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install(),
                        options=options
                    )

            elif self.browser == 'firefox':
                options = FirefoxOptions()
                if self.headless:
                    options.add_argument('--headless')
                options.add_argument('--width=1920')
                options.add_argument('--height=1080')
                options.add_argument('--disable-gpu')

                self.driver = webdriver.Firefox(
                    GeckoDriverManager().install(),
                    options=options
                )
            else:
                raise ValueError(f"Unsupported browser: {self.browser}")

            # Set implicit wait
            self.driver.implicitly_wait(10)

        except Exception as e:
            logger.error(f"Failed to setup {self.browser} driver: {e}")
            raise

    def _teardown_driver(self) -> None:
        """Clean up the WebDriver instance."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")
            finally:
                self.driver = None

    def capture_screenshot(
        self,
        url: str,
        wait_time: int = 5,
        full_page: bool = False,
        element_selector: Optional[str] = None
    ) -> bytes:
        """
        Capture screenshot of a web page.

        Args:
            url: URL to capture
            wait_time: Time to wait for page load (seconds)
            full_page: Whether to capture full page or just viewport
            element_selector: CSS selector for specific element to capture

        Returns:
            Screenshot image data as bytes
        """
        if not self.driver:
            self._setup_driver()

        try:
            logger.info(f"Capturing screenshot of {url}")

            # Navigate to the URL
            self.driver.get(url)

            # Wait for page to load
            WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )

            # Additional wait for dynamic content
            import time
            time.sleep(2)

            if element_selector:
                # Capture specific element
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, element_selector))
                    )
                    screenshot_data = element.screenshot_as_png
                except TimeoutException:
                    logger.warning(f"Element {element_selector} not found, capturing full page")
                    screenshot_data = self.driver.get_screenshot_as_png()
            elif full_page:
                # Capture full page (scroll and stitch if needed)
                screenshot_data = self._capture_full_page()
            else:
                # Capture viewport
                screenshot_data = self.driver.get_screenshot_as_png()

            logger.info(f"Screenshot captured successfully ({len(screenshot_data)} bytes)")
            return screenshot_data

        except Exception as e:
            logger.error(f"Failed to capture screenshot of {url}: {e}")
            raise

    def _capture_full_page(self) -> bytes:
        """Capture full page by scrolling and stitching screenshots."""
        try:
            # Get page dimensions
            total_height = self.driver.execute_script(
                "return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
            )
            viewport_height = self.driver.execute_script("return window.innerHeight")
            viewport_width = self.driver.execute_script("return window.innerWidth")

            # Scroll and capture screenshots
            screenshots = []
            scroll_position = 0

            while scroll_position < total_height:
                # Scroll to position
                self.driver.execute_script(f"window.scrollTo(0, {scroll_position})")

                # Wait for scroll to complete
                import time
                time.sleep(0.5)

                # Capture current viewport
                screenshot = self.driver.get_screenshot_as_png()
                screenshots.append(screenshot)

                # Move to next viewport
                scroll_position += viewport_height

            if len(screenshots) == 1:
                return screenshots[0]
            else:
                # For now, return the first screenshot
                # In a full implementation, you'd stitch them together
                logger.warning("Full page stitching not implemented, returning first viewport")
                return screenshots[0]

        except Exception as e:
            logger.error(f"Failed to capture full page: {e}")
            # Fallback to single screenshot
            return self.driver.get_screenshot_as_png()

    def capture_and_record(
        self,
        finding: Finding,
        url: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> 'Evidence':
        """
        Capture screenshot and record as evidence.

        Args:
            finding: Finding to associate with the evidence
            url: URL to capture
            title: Title for the evidence
            metadata: Additional metadata
            **kwargs: Additional arguments for capture_screenshot

        Returns:
            Created Evidence instance
        """
        try:
            # Capture screenshot
            screenshot_data = self.capture_screenshot(url, **kwargs)

            # Prepare metadata
            evidence_metadata = {
                'url': url,
                'browser': self.browser,
                'headless': self.headless,
                'timestamp': kwargs.get('timestamp'),
                'user_agent': self.driver.execute_script("return navigator.userAgent") if self.driver else None,
                **(metadata or {})
            }

            # Generate filename
            filename = f"screenshot_{finding.id}_{url.replace('://', '_').replace('/', '_')[:50]}.png"

            # Record as evidence
            evidence = record_evidence_from_content(
                finding=finding,
                content=screenshot_data,
                filename=filename,
                kind='screenshot',
                content_type='image/png',
                metadata=evidence_metadata
            )

            logger.info(f"Screenshot evidence recorded: {evidence.id}")
            return evidence

        except Exception as e:
            logger.error(f"Failed to capture and record screenshot: {e}")
            raise

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self._teardown_driver()


def capture_screenshot_evidence(
    finding: Finding,
    url: str,
    browser: str = 'chrome',
    headless: bool = True,
    **kwargs
) -> 'Evidence':
    """
    Convenience function to capture screenshot and record as evidence.

    Args:
        finding: Finding to associate with evidence
        url: URL to capture
        browser: Browser to use
        headless: Whether to run headless
        **kwargs: Additional arguments

    Returns:
        Created Evidence instance
    """
    with ScreenshotCapture(browser=browser, headless=headless) as capturer:
        return capturer.capture_and_record(finding, url, **kwargs)
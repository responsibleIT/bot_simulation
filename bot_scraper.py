"""
Automated bot for the Bot Simulation platform
------------------------------------------------

This script uses Selenium WebDriver with ChromeDriver to automate logging into your
Bot Simulation site and posting the comment "Be aware of Dark Technology #DarkTech"
under each existing post. It is intended as a starting point for students to explore
web automation techniques. You may need to tweak the element locators (XPaths, CSS selectors)
to match your site's HTML structure.

Prerequisites:
    - Python 3.8 or higher
    - Selenium installed (see requirements.txt)
    - webdriver-manager installed (optional but recommended)
    - Chromedriver available on your PATH or managed by webdriver_manager

To run this script:

    python bot_scraper.py --email your_email@example.com

It will open a browser window, log in with the provided email, navigate to the feed,
and post the predefined comment under each post it finds.

Disclaimer:
    This script interacts with a controlled environment (your own bot simulation).
    Do not use it to automate actions on public websites without permission, as that
    can violate terms of service and may be unethical or illegal.
"""

import argparse
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    # Use webdriver_manager if available to download/manage chromedriver automatically
    from webdriver_manager.chrome import ChromeDriverManager
    USE_WDM = True
except ImportError:
    USE_WDM = False


COMMENT_TEXT = "Be aware of Dark Technology #DarkTech"


def get_driver() -> webdriver.Chrome:
    """Initialise the Chrome webdriver, using webdriver_manager if available."""
    if USE_WDM:
        return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    else:
        # Assumes chromedriver is in PATH
        return webdriver.Chrome()


def login(driver: webdriver.Chrome, base_url: str, email: str) -> None:
    """Log in or register using the provided e-mail on the bot-simulation site.

    :param driver: Selenium WebDriver instance
    :param base_url: URL of the bot simulation home page (e.g. http://localhost:8501)
    :param email: E‑mail address to log in or register
    """
    driver.get(base_url)
    wait = WebDriverWait(driver, 10)

    # Locate the email input field. Depending on the site, the placeholder or label may differ.
    email_input = wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//input[@type='text' or @placeholder='School e‑mail address' or @placeholder='Email' or contains(@placeholder,'e‑mail')]",
            )
        )
    )
    email_input.clear()
    email_input.send_keys(email)

    # Click the Log in / Register button
    login_button = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[normalize-space()='Log in / Register' or normalize-space()='Login' or contains(text(),'Log in')]",
            )
        )
    )
    login_button.click()

    # Wait a moment for login to complete. Adjust as needed based on your app.
    time.sleep(3)


def navigate_to_feed(driver: webdriver.Chrome) -> None:
    """Navigate to the Feed page using the sidebar or URL.

    This function assumes the sidebar has a link or radio button labelled "Feed".
    You may need to modify the element selectors if your navigation differs.
    """
    # Wait for sidebar to appear
    wait = WebDriverWait(driver, 10)
    try:
        feed_nav = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//div[contains(@class,'sidebar')]//div[normalize-space()='Feed' or normalize-space()='feed']",
                )
            )
        )
        feed_nav.click()
    except Exception:
        # Fallback: manually open the feed page by URL path
        driver.get(driver.current_url.rstrip('/') + '#feed')
        time.sleep(2)


def comment_on_posts(driver: webdriver.Chrome, comment: str) -> None:
    """Post the given comment under each existing post on the feed.

    :param driver: Selenium WebDriver instance
    :param comment: The comment text to post
    """
    wait = WebDriverWait(driver, 10)
    # Ensure posts have loaded. Modify the selector if your post container differs.
    posts = wait.until(
        EC.presence_of_all_elements_located(
            (
                By.XPATH,
                "//div[contains(@class,'post') or contains(@class,'card') or contains(@id,'post')]",
            )
        )
    )
    for idx, post in enumerate(posts, start=1):
        try:
            # Expand comments section if collapsible
            try:
                expander = post.find_element(
                    By.XPATH,
                    ".//summary[contains(text(),'Comments') or contains(text(),'comments')]",
                )
                expander.click()
                time.sleep(1)
            except Exception:
                pass

            # Find the comment input field within the post
            comment_box = post.find_element(
                By.XPATH,
                ".//input[@type='text' or @placeholder='Your comment' or contains(@placeholder,'comment')]",
            )
            comment_box.clear()
            comment_box.send_keys(comment)

            # Click the Add comment button
            add_btn = post.find_element(
                By.XPATH,
                ".//button[contains(text(),'Add comment') or contains(text(),'Add Comment')]",
            )
            add_btn.click()
            time.sleep(1)
            print(f"Commented on post #{idx}")
        except Exception as exc:
            print(f"Skipping a post due to error: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Automate commenting on bot simulation posts.")
    parser.add_argument(
        "--email",
        required=True,
        help="E‑mail address to log in/register with",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8501",
        help="Base URL of the bot simulation site (default: http://localhost:8501)",
    )
    parser.add_argument(
        "--comment",
        default=COMMENT_TEXT,
        help="Text to post as a comment (default: '%(default)s')",
    )
    args = parser.parse_args()

    driver = get_driver()
    try:
        login(driver, args.base_url, args.email)
        navigate_to_feed(driver)
        comment_on_posts(driver, args.comment)
        print("Done adding comments.")
        # Keep the browser open for a short time to view results
        time.sleep(5)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
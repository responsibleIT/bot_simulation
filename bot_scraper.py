"""
Automated bot for the Bot Simulation platform
------------------------------------------------
To run this script:

    python bot_scraper.py --email your_email@example.com

It will open a browser window, log in with the provided email, navigate to the feed,
and post the predefined comment under each post it finds.

Disclaimer:
    This script interacts with a controlled environment (our own bot simulation).
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
from selenium.common.exceptions import TimeoutException

try:
    # Use webdriver_manager if available to download/manage chromedriver automatically
    from webdriver_manager.chrome import ChromeDriverManager

    USE_WDM = True
except ImportError:
    USE_WDM = False


COMMENT_TEXT = "Be aware of Dark Technology #DarkTech"


# ---------------------------------------------------------------------------
# WebDriver initialisation
# ---------------------------------------------------------------------------

def get_driver() -> webdriver.Chrome:
    """Initialise the Chrome webdriver, using webdriver_manager if available."""
    if USE_WDM:
        return webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    else:
        # Assumes chromedriver is in PATH
        return webdriver.Chrome()


# ---------------------------------------------------------------------------
# Login flow
# ---------------------------------------------------------------------------

def login(driver: webdriver.Chrome, base_url: str, email: str) -> None:
    """
    Log in or register using the provided e-mail on the bot-simulation site.

    This version uses heuristic element lookup so students can see how a bot
    might search for likely targets:
      * It tries several ways to locate the e-mail field (type=email, placeholder
        mentioning 'mail', aria-label mentioning 'mail', fallback first text input).
      * It tries several ways to locate a login/register button (text containing
        'log' or 'register', then any button).

    One of these strategies should always succeed as long as the login e-mail
    input somehow references 'mail' and the button mentions login/register.
    """
    driver.get(base_url)
    wait = WebDriverWait(driver, 10)

    # Try to navigate to the Login page via the sidebar nav link.
    # Streamlit renders these links as <a data-testid="stSidebarNavLink"> with
    # a <span> child containing the page label.
    try:
        login_link = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//a[@data-testid='stSidebarNavLink']"
                    "[.//span[contains(translate(normalize-space(),'LOGIN','login'),'login')]]",
                )
            )
        )
        login_link.click()
        time.sleep(2)
    except TimeoutException:
        # If the sidebar link isn't found, we assume we are already on the login page.
        pass

    # ---------- Find an input element suitable for entering the e-mail ----------

    email_input = None

    # Strategy 1: input type="email"
    try:
        email_input = wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
        )
    except TimeoutException:
        email_input = None

    # Strategy 2: placeholder mentioning 'mail' (e.g. "Enter your school e-mail")
    if email_input is None:
        try:
            email_input = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//input[contains(translate(@placeholder,"
                        " 'MAIL','mail'),'mail')]",
                    )
                )
            )
        except TimeoutException:
            email_input = None

    # Strategy 3: aria-label mentioning 'mail' (Streamlit often uses aria-label from label)
    if email_input is None:
        try:
            email_input = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//input[contains(translate(@aria-label,"
                        " 'MAIL','mail'),'mail')]",
                    )
                )
            )
        except TimeoutException:
            email_input = None

    # Fallback: first visible text input
    if email_input is None:
        try:
            email_input = wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='text']"))
            )
        except TimeoutException:
            email_input = None

    if email_input is None:
        raise RuntimeError("Unable to locate email input field on login page.")

    try:
        email_input.clear()
    except Exception:
        # Some inputs complain if you clear before typing; it's safe to ignore.
        pass
    email_input.send_keys(email)

    # ---------- Find the login/register button ----------

    login_button = None
    button_xpaths = [
        # Any button whose visible text mentions 'log' (login / log in)
        "//button[contains(translate(., 'LOG','log'),'log')]",
        # Any button whose visible text mentions 'register'
        "//button[contains(translate(., 'REGISTER','register'),'register')]",
        # As a last resort, any clickable button
        "//button",
    ]

    for xpath in button_xpaths:
        try:
            candidate = wait.until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            if candidate:
                login_button = candidate
                break
        except TimeoutException:
            continue

    if login_button is None:
        raise RuntimeError("Unable to locate login/register button on login page.")

    login_button.click()
    # Wait a bit for login to complete / redirect
    time.sleep(3)


# ---------------------------------------------------------------------------
# Navigation to feed
# ---------------------------------------------------------------------------

def navigate_to_feed(driver: webdriver.Chrome) -> None:
    """
    Navigate to the Feed page using the sidebar or a URL.

    This assumes the sidebar has a link labelled 'Feed' (as in the Streamlit UI).
    """
    wait = WebDriverWait(driver, 10)
    try:
        feed_link = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//a[@data-testid='stSidebarNavLink']"
                    "[.//span[contains(translate(normalize-space(),'FEED','feed'),'feed')]]",
                )
            )
        )
        feed_link.click()
        time.sleep(2)
    except TimeoutException:
        # Fallback: try adding a path fragment – this is more of a demo than a guarantee.
        driver.get(driver.current_url.rstrip("/") + "/Feed")
        time.sleep(2)


# ---------------------------------------------------------------------------
# Commenting on posts
# ---------------------------------------------------------------------------

def comment_on_posts(driver: webdriver.Chrome, comment: str) -> None:
    """
    Post the given comment under each existing post on the feed.

    Instead of trying to identify the entire post card, this function looks for
    all <details> elements whose <summary> contains 'Comments'. For each such
    block, it:
      * ensures the comments section is open,
      * finds a text input whose placeholder/aria-label includes 'comment',
      * types the comment,
      * clicks a button whose text contains both 'add' and 'comment'.

    This shows students how a bot can use reasonable heuristics instead of
    relying on a single brittle selector.
    """
    wait = WebDriverWait(driver, 10)

    try:
        details_blocks = wait.until(
            EC.presence_of_all_elements_located(
                (
                    By.XPATH,
                    "//details[.//summary[contains("
                    "translate(normalize-space(),'COMMENTS','comments'),'comments')]]",
                )
            )
        )
    except TimeoutException:
        print("No comment sections (details/summary) found on the page.")
        return

    print(f"Found {len(details_blocks)} comment sections.")

    for idx, details in enumerate(details_blocks, start=1):
        try:
            # Scroll into view to avoid 'element not interactable' issues
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", details
            )
            time.sleep(0.5)

            # Open the comments section if it's collapsed
            try:
                if details.get_attribute("open") is None:
                    summary = details.find_element(By.TAG_NAME, "summary")
                    summary.click()
                    time.sleep(0.5)
            except Exception:
                pass

            # Find a comment input field inside this details block.
            comment_box = None
            comment_input_xpaths = [
                # any text input whose placeholder mentions 'comment'
                ".//input[@type='text' and "
                "contains(translate(@placeholder,'COMMENT','comment'),'comment')]",
                # placeholder may not be set but aria-label might mention comment
                ".//input[@type='text' and "
                "contains(translate(@aria-label,'COMMENT','comment'),'comment')]",
                # last resort: first text input in the details
                ".//input[@type='text']",
            ]

            for cx in comment_input_xpaths:
                try:
                    comment_box = details.find_element(By.XPATH, cx)
                    if comment_box:
                        break
                except Exception:
                    continue

            if comment_box is None:
                print(f"[Section {idx}] No suitable comment input field found; skipping.")
                continue

            try:
                comment_box.clear()
            except Exception:
                pass
            comment_box.send_keys(comment)

            # Find the 'Add comment' button: text containing both 'add' and 'comment'
            add_button = None
            add_button_xpaths = [
                ".//button[contains(translate(.,'ADDCOMMENT','addcomment'),'add')"
                " and contains(translate(.,'ADDCOMMENT','addcomment'),'comment')]",
                ".//button[contains(translate(.,'COMMENT','comment'),'comment')]",
                ".//button",
            ]
            for bx in add_button_xpaths:
                try:
                    candidate = details.find_element(By.XPATH, bx)
                    if candidate:
                        add_button = candidate
                        break
                except Exception:
                    continue

            if add_button is None:
                print(f"[Section {idx}] Could not find an 'add comment' button; skipping.")
                continue

            add_button.click()
            time.sleep(1)
            print(f"Commented in section #{idx}")

        except Exception as exc:
            print(f"Skipping a comment section due to error: {exc}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Automate commenting on bot simulation posts."
    )
    parser.add_argument(
        "--email",
        required=True,
        help="E-mail address to log in/register with",
    )
    parser.add_argument(
        "--base-url",
        default="https://botsimulator.responsible-it.nl",
        help="Base URL of the bot simulation site (default: https://botsimulator.responsible-it.nl)",
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

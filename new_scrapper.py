import json
import time
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LinkedInSeleniumScraper:
    def __init__(self, username: str, password: str, headless: bool = True):
        self.username = username
        self.password = password
        self.driver = self._init_driver(headless)
        self._login()

    def _init_driver(self, headless: bool):
        options = Options()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)
        return driver

    def _login(self):
        """Login to LinkedIn using credentials"""
        self.driver.get("https://www.linkedin.com/login")
        logger.info("Logging in to LinkedIn...")
        try:
            email_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            email_input.send_keys(self.username)

            password_input = self.driver.find_element(By.ID, "password")
            password_input.send_keys(self.password)
            password_input.send_keys(Keys.RETURN)

            # Wait until home page loads
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "global-nav-search"))
            )
            logger.info("Login successful!")
        except Exception as e:
            logger.exception("Login failed")
            raise

    def _scroll_page(self, pause: float = 2.5, max_scroll: int = 5):
        """Scroll page to load posts"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        for _ in range(max_scroll):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def _parse_time(self, time_text: str) -> datetime:
        """Convert LinkedIn time string to datetime"""
        now = datetime.now()
        time_text = time_text.lower().replace("ago", "").replace("•", "").strip()

        try:
            if "h" in time_text:  # hours
                hours = int(''.join(filter(str.isdigit, time_text)))
                return now - timedelta(hours=hours)
            elif "d" in time_text:  # days
                days = int(''.join(filter(str.isdigit, time_text)))
                return now - timedelta(days=days)
            elif "w" in time_text:  # weeks
                weeks = int(''.join(filter(str.isdigit, time_text)))
                return now - timedelta(weeks=weeks)
            elif "mo" in time_text:  # months
                months = int(''.join(filter(str.isdigit, time_text)))
                return now - timedelta(days=months * 30)
            elif "y" in time_text:  # years
                years = int(''.join(filter(str.isdigit, time_text)))
                return now - timedelta(days=years * 365)
        except:
            pass

        try:
            return datetime.strptime(time_text, "%b %d, %Y")
        except:
            return now

    def scrape_profile(self, profile_url: str, max_posts: int, time_filter: str) -> Dict[str, Any]:
        try:
            self.driver.get(profile_url)
            logger.info(f"Opening profile: {profile_url}")
            time.sleep(5)

            # Extract author info
            try:
                author_name = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
                ).text
            except:
                author_name = ""

            try:
                headline = self.driver.find_element(By.CSS_SELECTOR, ".text-body-medium").text
            except:
                headline = ""

            try:
                author_image_elem = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "div.pv-top-card__non-self-photo-wrapper img"
                )
                author_image = author_image_elem.get_attribute("src")
            except:
                author_image = ""

            author_url = profile_url

            # Navigate to posts section
            posts_tab = profile_url.rstrip("/") + "/recent-activity/all/"
            self.driver.get(posts_tab)
            logger.info(f"Opening posts tab: {posts_tab}")
            time.sleep(5)

            self._scroll_page(max_scroll=6)

            posts: List[Dict[str, Any]] = []
            post_wrappers = self.driver.find_elements(By.CSS_SELECTOR, "div.feed-shared-update-v2")

            now = datetime.now()
            if time_filter == "24h":
                cutoff = now - timedelta(hours=24)
            elif time_filter == "week":
                cutoff = now - timedelta(days=7)
            else:
                cutoff = None

            for idx, post in enumerate(post_wrappers):
                try:
                    time_text = ""
                    try:
                        sub_desc = post.find_element(By.CSS_SELECTOR, "span.update-components-actor__sub-description")
                        time_elem = sub_desc.find_element(By.CSS_SELECTOR, "span[aria-hidden='true']")
                        time_text = time_elem.text.strip()
                        time_text = time_text.split("•")[0].strip()
                    except Exception as e:
                        logger.warning(f"Could not extract timestamp: {e}")
                        time_text = ""

                    logger.info(f"Raw post time text: '{time_text}'")
                    post_time = self._parse_time(time_text)

                    if cutoff and post_time < cutoff:
                        logger.info(f"Skipping post (too old): {time_text}")
                        break

                    try:
                        content = post.find_element(By.CSS_SELECTOR, "div.update-components-text").text.strip()
                    except:
                        content = ""

                    media_url = ""
                    try:
                        img_tag = post.find_element(By.CSS_SELECTOR, "img")
                        media_url = img_tag.get_attribute("src")
                    except:
                        pass
                    if not media_url:
                        try:
                            div_bg = post.find_element(By.CSS_SELECTOR, "div[style*='background-image']")
                            style_attr = div_bg.get_attribute("style")
                            media_url = style_attr.split("url(")[1].split(")")[0].replace('"', '').replace("'", "")
                        except:
                            pass
                    if not media_url:
                        try:
                            video_tag = post.find_element(By.CSS_SELECTOR, "video")
                            media_url = video_tag.get_attribute("src")
                        except:
                            media_url = ""

                    try:
                        post_link_tag = post.find_element(
                            By.CSS_SELECTOR, "a[href*='/feed/update/'], a[href*='/posts/']"
                        )
                        post_url = post_link_tag.get_attribute("href")
                        if post_url and post_url.startswith("/"):
                            post_url = "https://www.linkedin.com" + post_url
                    except:
                        try:
                            urn = post.get_attribute("data-urn")
                            if urn and "activity" in urn:
                                post_url = f"https://www.linkedin.com/feed/update/{urn}"
                            else:
                                post_url = ""
                        except:
                            post_url = ""

                    posts.append({
                        "id": f"post-{len(posts)+1}",
                        "content": content,
                        "media": media_url,
                        "post_url": post_url,
                        "timestamp": post_time.isoformat()
                    })

                    if len(posts) >= max_posts:
                        break

                except Exception as e:
                    logger.warning(f"Error scraping post {idx+1}: {e}")

            return {
                "profile_url": profile_url,
                "author_name": author_name,
                "author_headline": headline,
                "author_image": author_image,
                "author_url": author_url,
                "posts": posts
            }

        except Exception as e:
            logger.exception("Scraping failed")
            return {"error": str(e)}

    def close(self):
        self.driver.quit()


if __name__ == "__main__":
    USERNAME = "proffessorrr21@gmail.com"
    PASSWORD = "professor212005"

    urls_input = input("Enter LinkedIn profile URLs (comma-separated): ").strip()
    profile_urls = [u.strip() for u in urls_input.split(",") if u.strip()]
    time_filter = input("Enter time filter (24h / week / all): ").strip().lower()
    max_posts = int(input("Enter max posts to scrape: ").strip())

    scraper = LinkedInSeleniumScraper(username=USERNAME, password=PASSWORD, headless=False)
    results = []

    for url in profile_urls:
        logger.info(f"🔍 Scraping profile: {url}")
        result = scraper.scrape_profile(url, max_posts=max_posts, time_filter=time_filter)
        results.append(result)

    scraper.close()

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(json.dumps(results, indent=2, ensure_ascii=False))

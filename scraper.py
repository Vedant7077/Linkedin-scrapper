import json
from playwright.sync_api import sync_playwright
import re
from datetime import datetime

# Load cookies from linkedin_cookies.json
def load_cookies():
    try:
        with open("linkedin_cookies.json", "r") as f:
            cookies = json.load(f)
        current_time = datetime.now().timestamp()
        # Filter out expired cookies
        valid_cookies = [c for c in cookies if not c.get("expirationDate") or c["expirationDate"] > current_time]
        
        if not valid_cookies:
            print("Warning: All cookies are expired or invalid")
            return None
            
        if len(valid_cookies) < len(cookies):
            print(f"Warning: {len(cookies) - len(valid_cookies)} cookies are expired")
        
        # Check for critical cookies (li_at for auth)
        cookie_names = [c["name"] for c in valid_cookies]
        print(f"Available cookies: {cookie_names}")
        
        if "li_at" not in cookie_names:
            print("Warning: Missing li_at cookie; authentication may fail")
            return None
            
        # Note: __cf_bm is often missing or expired, so we'll make it optional
        if "__cf_bm" not in cookie_names:
            print("Warning: Missing __cf_bm cookie (Cloudflare protection) - will attempt to proceed")
        
        return valid_cookies
    except FileNotFoundError:
        print("linkedin_cookies.json file not found")
        return None
    except json.JSONDecodeError:
        print("Invalid JSON in linkedin_cookies.json")
        return None

# Perform manual login to LinkedIn
def manual_login(page, username, password):
    try:
        print("Attempting manual login...")
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=60000)
        
        # Check for CAPTCHA
        if page.locator("iframe[title*='CAPTCHA']").count() > 0:
            raise Exception("CAPTCHA detected; try headless=False to solve manually or use a CAPTCHA-solving service")
        
        page.fill("input#username", username)
        page.fill("input#password", password)
        page.click("button[type='submit']")
        page.wait_for_timeout(5000)  # Wait for login to complete
        
        if "login" in page.url.lower() or page.locator("input#username").count() > 0:
            raise Exception("Manual login failed; check credentials or CAPTCHA")
        
        print("Manual login successful")
        # Save new cookies
        cookies = page.context.cookies()
        with open("linkedin_cookies.json", "w") as f:
            json.dump(cookies, f, indent=4)
        print("Saved new cookies to linkedin_cookies.json")
        return True
    except Exception as e:
        print(f"Manual login error: {str(e)}")
        return False

# Check if we need to login
def check_login_required(page):
    try:
        page_title = page.title().lower()
        page_url = page.url.lower()
        
        # Check for common login indicators
        login_indicators = [
            page.locator("input#username").count() > 0,
            "login" in page_url,
            "/authwall" in page_url,
            "join linkedin" in page_title,
            "welcome to your professional community" in page_title,
            "sign up" in page_title,
            "sign in" in page_title
        ]
        
        return any(login_indicators)
    except:
        return True  # If we can't check, assume login is required

# Scrape a LinkedIn profile for name, headline, image, and the latest original post
def scrape_profile(profile_url: str, username=None, password=None):
    print(f"Starting to scrape profile: {profile_url}")
    
    # Load cookies (but don't fail if they're missing)
    cookies = load_cookies()
    
    # Start Playwright and open a browser
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        if cookies:
            try:
                context.add_cookies(cookies)
                print("Cookies loaded successfully")
            except Exception as e:
                print(f"Failed to load cookies: {str(e)}")
                # Try to clean and reload cookies
                cleaned_cookies = []
                for cookie in cookies:
                    try:
                        # Create a minimal cookie dict with only required fields
                        clean_cookie = {
                            "name": cookie["name"],
                            "value": cookie["value"],
                            "domain": cookie["domain"],
                            "path": cookie.get("path", "/"),
                            "secure": cookie.get("secure", False),
                            "httpOnly": cookie.get("httpOnly", False)
                        }
                        
                        # Add optional fields only if they're valid
                        if cookie.get("sameSite") in ["Strict", "Lax", "None"]:
                            clean_cookie["sameSite"] = cookie["sameSite"]
                        
                        if cookie.get("expirationDate"):
                            clean_cookie["expires"] = int(cookie["expirationDate"])
                            
                        cleaned_cookies.append(clean_cookie)
                    except Exception as clean_error:
                        print(f"Skipping problematic cookie {cookie.get('name', 'unknown')}: {clean_error}")
                        continue
                
                if cleaned_cookies:
                    try:
                        context.add_cookies(cleaned_cookies)
                        print(f"Loaded {len(cleaned_cookies)} cleaned cookies")
                    except Exception as e2:
                        print(f"Failed to load even cleaned cookies: {str(e2)}")
                        cookies = None
                else:
                    cookies = None

        page = context.new_page()
        
        # Try loading the profile page
        try:
            print("Loading profile page...")
            page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
            print(f"Loaded page: {page.url}")
            page.wait_for_timeout(3000)  # Wait for redirects and dynamic content
        except Exception as e:
            print(f"Failed to load profile: {str(e)}")
            browser.close()
            return {"status": "error", "message": f"Failed to load profile: {str(e)}"}

        # Check if login is required
        if check_login_required(page):
            print("Login required detected")
            if username and password:
                if manual_login(page, username, password):
                    try:
                        page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
                        print(f"Reloaded page after login: {page.url}")
                    except Exception as e:
                        browser.close()
                        return {"status": "error", "message": f"Failed to reload after login: {str(e)}"}
                else:
                    browser.close()
                    return {"status": "error", "message": "Manual login failed; check credentials or CAPTCHA"}
            else:
                browser.close()
                return {"status": "error", "message": "Login required but no credentials provided. Please update your cookies or provide username/password."}

        # Clean up the profile URL
        normalized_profile_url = re.match(r"(https://www\.linkedin\.com/in/[^/?]+)", profile_url)
        profile_url_clean = normalized_profile_url.group(0) if normalized_profile_url else profile_url

        # Wait for page to fully load
        try:
            page.wait_for_selector("main", timeout=10000)
        except:
            print("Warning: Main content selector not found")

        # --- Extract author details ---
        author_name = None
        selectors = [
            "h1.text-heading-xlarge",
            "h1[class*='text-heading']",
            "h1[class*='top-card']", 
            ".pv-text-details__left-panel h1",
            "h1",
            ".profile-photo-edit__preview .visually-hidden"
        ]
        
        for selector in selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    author_name = element.inner_text(timeout=5000).strip()
                    if author_name and len(author_name) > 2:  # Basic validation
                        print(f"Found author_name with selector '{selector}': {author_name}")
                        break
            except Exception as e:
                print(f"Error with selector '{selector}': {str(e)}")
                continue

        if not author_name:
            print("Could not extract author name")

        # Extract headline
        headline = None
        headline_selectors = [
            ".text-body-medium.break-words",
            ".pv-text-details__left-panel .text-body-medium",
            "div[class*='text-body-medium']",
            ".pv-top-card-content .pv-text-details__left-panel .text-body-medium"
        ]
        
        for selector in headline_selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    headline = element.inner_text(timeout=5000).strip()
                    if headline:
                        print(f"Found headline with selector '{selector}': {headline[:50]}...")
                        break
            except Exception as e:
                print(f"Error extracting headline with '{selector}': {str(e)}")
                continue

        # Extract profile picture URL
        author_image = None
        image_selectors = [
            "img.pv-top-card-profile-picture__image",
            "img[alt*='profile photo']",
            ".pv-top-card-profile-picture img",
            "button.pv-top-card-profile-picture img"
        ]
        
        for selector in image_selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    author_image = element.get_attribute("src", timeout=5000)
                    if author_image:
                        print(f"Found profile image with selector '{selector}'")
                        break
            except Exception as e:
                print(f"Error extracting image with '{selector}': {str(e)}")
                continue

        # --- Load posts by scrolling to activity section ---
        print("Looking for posts...")
        
        # Try to navigate to activity section or scroll to find posts
        try:
            # Look for activity link or scroll down to find posts
            activity_link = page.locator("a[href*='/recent-activity/']").first
            if activity_link.count() > 0:
                activity_link.click()
                page.wait_for_timeout(3000)
                print("Navigated to activity section")
        except:
            print("Activity section not found, scrolling to find posts...")
            
        # Scroll to load posts
        for i in range(5):  # Scroll more times to ensure posts load
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            print(f"Scroll {i+1}/5")

        # Try to find posts
        posts_data = []
        posts = []
        
        post_selectors = [
            ".feed-shared-update-v2",
            "div[class*='feed-shared-update']",
            ".artdeco-card",
            "[data-urn*='activity']"
        ]
        
        for selector in post_selectors:
            try:
                posts = page.locator(selector).all()
                if posts:
                    print(f"Found {len(posts)} posts with selector '{selector}'")
                    break
            except Exception as e:
                print(f"Error finding posts with '{selector}': {str(e)}")
                continue

        if not posts:
            print("No posts found")
            message = "No posts found on profile"
        else:
            message = None
            # Check up to 5 posts for the latest original post
            for i, post in enumerate(posts[:5]):
                try:
                    print(f"Processing post {i+1}")
                    
                    # Check if it's a repost (skip reposts)
                    try:
                        repost_indicators = post.locator("[class*='repost'], .feed-shared-mini-update, [aria-label*='repost']").count()
                        actor_text = post.locator("span[class*='update-components-actor']").inner_text(timeout=3000).lower()
                        is_repost = (
                            repost_indicators > 0 or
                            any(keyword in actor_text for keyword in ["reposted", "shared", "repost"])
                        )
                        
                        if is_repost:
                            print(f"Skipping repost {i+1}")
                            continue
                    except Exception as e:
                        print(f"Error checking repost status: {str(e)}")

                    # Extract post text
                    title = None
                    text_selectors = [
                        ".feed-shared-text .break-words",
                        "div[class*='update-components-text'] span.break-words",
                        ".feed-shared-text span",
                        "[class*='feed-shared-text']"
                    ]
                    
                    for text_selector in text_selectors:
                        try:
                            text_element = post.locator(text_selector).first
                            if text_element.count() > 0:
                                title = text_element.inner_text(timeout=3000).strip()
                                if title:
                                    break
                        except:
                            continue

                    # Extract post image
                    image = None
                    try:
                        img_element = post.locator("img[class*='feed-shared-image']").first
                        if img_element.count() > 0:
                            image = img_element.get_attribute("src", timeout=3000)
                    except Exception as e:
                        print(f"Error extracting post image: {str(e)}")

                    # Extract post link
                    link = None
                    try:
                        data_urn = post.get_attribute("data-urn", timeout=3000)
                        if data_urn and "urn:li:activity:" in data_urn:
                            activity_id = data_urn.split(":")[-1]
                            link = f"https://www.linkedin.com/feed/update/urn:li:activity:{activity_id}"
                    except Exception as e:
                        print(f"Error extracting post link: {str(e)}")

                    # Add the post if we have content
                    if title or image:
                        posts_data.append({
                            "title": title,
                            "image": image,
                            "link": link
                        })
                        print(f"Added post with title: {title[:50] if title else 'No title'}...")
                        break  # Stop after first original post

                except Exception as e:
                    print(f"Error processing post {i+1}: {str(e)}")
                    continue

            # If no original posts found
            if not posts_data and posts:
                message = "Only reposts found"

        browser.close()

        # Build the response
        result = {
            "profile_url": profile_url_clean,
            "author_name": author_name,
            "headline": headline,
            "author_image": author_image,
            "posts": posts_data,
            "status": "success"
        }
        
        if message:
            result["message"] = message
            
        return result
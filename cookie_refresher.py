import json
from playwright.sync_api import sync_playwright
import time

def refresh_cookies():
    """
    Script to refresh LinkedIn cookies including the __cf_bm cookie.
    This should be run when your current cookies are not working.
    """
    print("Starting cookie refresh process...")
    
    with sync_playwright() as p:
        # Launch browser in non-headless mode so you can see what's happening
        browser = p.chromium.launch(
            headless=False,  # Set to False so you can see the browser
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Load existing cookies if available
        try:
            with open("linkedin_cookies.json", "r") as f:
                existing_cookies = json.load(f)
                
            # Clean existing cookies
            cleaned_cookies = []
            for cookie in existing_cookies:
                try:
                    clean_cookie = {
                        "name": cookie["name"],
                        "value": cookie["value"],
                        "domain": cookie["domain"],
                        "path": cookie.get("path", "/"),
                        "secure": cookie.get("secure", False),
                        "httpOnly": cookie.get("httpOnly", False)
                    }
                    
                    if cookie.get("sameSite") in ["Strict", "Lax", "None"]:
                        clean_cookie["sameSite"] = cookie["sameSite"]
                    
                    if cookie.get("expirationDate"):
                        clean_cookie["expires"] = int(cookie["expirationDate"])
                        
                    cleaned_cookies.append(clean_cookie)
                except:
                    continue
                    
            if cleaned_cookies:
                context.add_cookies(cleaned_cookies)
                print("Loaded existing cookies")
                
        except Exception as e:
            print(f"Could not load existing cookies: {e}")

        page = context.new_page()
        
        # Go to LinkedIn
        print("Navigating to LinkedIn...")
        page.goto("https://www.linkedin.com")
        
        print("\n" + "="*60)
        print("MANUAL STEP REQUIRED:")
        print("1. If you're not logged in, please log in manually in the browser window")
        print("2. Navigate to any LinkedIn profile or your feed")
        print("3. Wait for the page to fully load")
        print("4. Press ENTER in this terminal when ready...")
        print("="*60)
        
        input("Press ENTER when you're logged in and on LinkedIn...")
        
        # Wait a bit more for any dynamic content
        print("Waiting for page to stabilize...")
        time.sleep(5)
        
        # Get fresh cookies
        fresh_cookies = context.cookies()
        
        # Check if we got the important cookies
        cookie_names = [c["name"] for c in fresh_cookies]
        print(f"Retrieved {len(fresh_cookies)} cookies")
        print(f"Cookie names: {cookie_names}")
        
        # Check for critical cookies
        has_li_at = "li_at" in cookie_names
        has_cf_bm = "__cf_bm" in cookie_names
        
        print(f"Has li_at (auth): {has_li_at}")
        print(f"Has __cf_bm (Cloudflare): {has_cf_bm}")
        
        if not has_li_at:
            print("WARNING: No li_at cookie found. Make sure you're logged in!")
            
        if not has_cf_bm:
            print("WARNING: No __cf_bm cookie found. This might cause Cloudflare issues.")
            print("Try refreshing the LinkedIn page and running this script again immediately.")
        
        # Convert to the format expected by your scraper
        formatted_cookies = []
        for cookie in fresh_cookies:
            formatted_cookie = {
                "domain": cookie["domain"],
                "hostOnly": not cookie["domain"].startswith("."),
                "httpOnly": cookie["httpOnly"],
                "name": cookie["name"],
                "path": cookie["path"],
                "secure": cookie["secure"],
                "session": cookie.get("expires", -1) == -1,
                "storeId": None,
                "value": cookie["value"]
            }
            
            # Add expiration date if present
            if cookie.get("expires", -1) != -1:
                formatted_cookie["expirationDate"] = cookie["expires"]
                
            # Add sameSite if present
            if cookie.get("sameSite"):
                formatted_cookie["sameSite"] = cookie["sameSite"]
            else:
                formatted_cookie["sameSite"] = "None"  # Default for LinkedIn
                
            formatted_cookies.append(formatted_cookie)
        
        # Save cookies
        with open("linkedin_cookies_new.json", "w") as f:
            json.dump(formatted_cookies, f, indent=4)
            
        print(f"\nCookies saved to 'linkedin_cookies_new.json'")
        print("You can now replace your existing linkedin_cookies.json with this file")
        
        browser.close()
        
        return True

if __name__ == "__main__":
    refresh_cookies()
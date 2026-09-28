import json
from playwright.sync_api import sync_playwright
from datetime import datetime

def debug_linkedin_page(profile_url="https://www.linkedin.com/in/vedant-palekar21/"):
    """
    Debug script to see exactly what's on the LinkedIn page
    """
    
    # Load cookies
    try:
        with open("linkedin_cookies.json", "r") as f:
            cookies = json.load(f)
        
        # Clean cookies
        valid_cookies = []
        current_time = datetime.now().timestamp()
        
        for cookie in cookies:
            if cookie.get("expirationDate") and cookie["expirationDate"] <= current_time:
                continue
                
            # Fix sameSite values
            if cookie.get("sameSite") is None:
                cookie["sameSite"] = "Lax"
            elif cookie.get("sameSite") not in ["Strict", "Lax", "None"]:
                cookie["sameSite"] = "Lax"
                
            if "storeId" in cookie:
                del cookie["storeId"]
                
            valid_cookies.append(cookie)
            
        print(f"Loaded {len(valid_cookies)} cookies")
        
    except Exception as e:
        print(f"Cookie loading error: {e}")
        valid_cookies = []

    with sync_playwright() as p:
        # Launch in non-headless mode so you can see what's happening
        browser = p.chromium.launch(
            headless=False,  # Set to True if you don't want to see the browser
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        if valid_cookies:
            try:
                context.add_cookies(valid_cookies)
                print("Cookies loaded successfully")
            except Exception as e:
                print(f"Cookie loading failed: {e}")

        page = context.new_page()
        
        print(f"Loading page: {profile_url}")
        page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
        
        print(f"Final URL: {page.url}")
        print(f"Page title: {page.title()}")
        
        # Wait for page to load
        page.wait_for_timeout(3000)
        
        print("\n" + "="*60)
        print("DEBUGGING PAGE CONTENT")
        print("="*60)
        
        # Check various indicators
        indicators = {
            "Login form (input#username)": page.locator("input#username").count(),
            "Navigation bar (.global-nav)": page.locator("nav.global-nav").count(),
            "Profile top card (.pv-top-card)": page.locator(".pv-top-card").count(),
            "Profile sections (section)": page.locator("section").count(),
            "Main content (main)": page.locator("main").count(),
            "H1 tags": page.locator("h1").count(),
            "Profile URN elements ([data-urn*='profile'])": page.locator("[data-urn*='profile']").count(),
            "Join to view text": page.locator("text=Join to view").count(),
            "Sign in text": page.locator("text=Sign in").count(),
            "Profile images": page.locator("img[alt*='profile']").count(),
            "Any images": page.locator("img").count(),
        }
        
        for desc, count in indicators.items():
            print(f"{desc}: {count}")
        
        # Get page content snippet
        try:
            content = page.content()
            print(f"\nPage content length: {len(content)} characters")
            print("\nFirst 500 characters of page content:")
            print("-" * 40)
            print(content[:500])
            print("-" * 40)
            
            # Look for specific keywords
            keywords = ["authwall", "join", "sign in", "login", "profile"]
            print(f"\nKeyword analysis:")
            for keyword in keywords:
                count = content.lower().count(keyword)
                print(f"'{keyword}': {count} occurrences")
                
        except Exception as e:
            print(f"Error getting page content: {e}")
        
        # Try to get profile name if visible
        try:
            h1_elements = page.locator("h1").all()
            print(f"\nFound {len(h1_elements)} H1 elements:")
            for i, h1 in enumerate(h1_elements[:3]):  # Show first 3
                try:
                    text = h1.inner_text(timeout=2000)
                    print(f"H1 {i+1}: {text}")
                except:
                    print(f"H1 {i+1}: Could not get text")
        except Exception as e:
            print(f"Error getting H1 elements: {e}")
        
        print("\n" + "="*60)
        print("Press ENTER to close browser...")
        input()
        
        browser.close()

if __name__ == "__main__":
    debug_linkedin_page()
import requests
import json
import msgpack
import base64
import os
from urllib.parse import urlencode
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Scrapfly API configuration
SCRAPFLY_API_KEY = ""  # Replace with your Scrapfly API key
SCRAPE_API_URL = "https://api.scrapfly.io/scrape"
SCREENSHOT_API_URL = "https://api.scrapfly.io/screenshot"
HEADERS = {
    "Accept": "application/msgpack",
    "Content-Encoding": "gzip"
}

# List of X profile URLs to scrape
PROFILE_URLS = [
    "https://x.com/example_user1",
    # "https://x.com/example_user2",
    # Add more profile URLs here
]

def scrape_profile_posts(profile_url):
    """Scrape posts from a given X profile URL using Scrapfly Web Scraping API."""
    params = {
        "key": SCRAPFLY_API_KEY,
        "url": profile_url,
        "asp": "true",  # Enable Anti Scraping Protection
        "render_js": "true",  # Enable JavaScript rendering for dynamic content
        "country": "us"  # Set proxy location
    }
    
    try:
        response = requests.get(SCRAPE_API_URL, params=urlencode(params), headers=HEADERS, timeout=155)
        response.raise_for_status()
        
        # Decode msgpack response
        data = msgpack.unpackb(response.content, raw=False)
        
        # Check for large objects (CLOB/BLOB)
        result = data.get("result", {})
        content = result.get("content")
        
        if result.get("format") in ["clob", "blob"]:
            logger.info(f"Large object detected for {profile_url}. Downloading from {content}")
            content = download_large_object(content)
            if result.get("format") == "blob":
                content = base64.b64decode(content)  # Decode binary data if BLOB
        
        # Save scraped content
        output_file = f"posts_{profile_url.split('/')[-1]}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved post data to {output_file}")
        
        # Log API usage
        log_api_usage(response.headers)
        
        return data
    
    except requests.exceptions.HTTPError as e:
        handle_scrapfly_error(e, profile_url)
        return None
    except Exception as e:
        logger.error(f"Error scraping {profile_url}: {str(e)}")
        return None

def capture_profile_screenshot(profile_url):
    """Capture a screenshot of a given X profile URL using Scrapfly Screenshot API."""
    params = {
        "key": SCRAPFLY_API_KEY,
        "url": profile_url,
        "format": "png",  # Save as PNG
        "options": "block_banners,load_images,auto_scroll",  # Enable banner blocking and auto-scroll
        "rendering_wait": "3000",  # Wait 3 seconds for dynamic content
        "viewport": "1920x1080"  # Set viewport size
    }
    
    try:
        response = requests.get(SCREENSHOT_API_URL, params=urlencode(params), headers=HEADERS, timeout=155)
        response.raise_for_status()
        
        # Save screenshot
        output_file = f"screenshot_{profile_url.split('/')[-1]}.png"
        with open(output_file, "wb") as f:
            f.write(response.content)
        logger.info(f"Saved screenshot to {output_file}")
        
        # Log screenshot storage URL
        screenshot_url = response.headers.get("X-Scrapfly-Screenshot-Url")
        if screenshot_url:
            logger.info(f"Screenshot stored at: {screenshot_url}")
        
        # Log API usage
        log_api_usage(response.headers)
        
        return output_file
    
    except requests.exceptions.HTTPError as e:
        handle_scrapfly_error(e, profile_url, is_screenshot=True)
        return None
    except Exception as e:
        logger.error(f"Error capturing screenshot for {profile_url}: {str(e)}")
        return None

def download_large_object(url):
    """Download large object (CLOB/BLOB) from the provided Scrapfly URL."""
    params = {"key": SCRAPFLY_API_KEY}
    try:
        response = requests.get(url, params=urlencode(params), timeout=155)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Error downloading large object from {url}: {str(e)}")
        return None

def log_api_usage(headers):
    """Log Scrapfly API usage details from response headers."""
    logger.info("API Usage Details:")
    for header in [
        "X-Scrapfly-Api-Cost",
        "X-Scrapfly-Remaining-Api-Credit",
        "X-Scrapfly-Account-Concurrent-Usage",
        "X-Scrapfly-Account-Remaining-Concurrent-Usage",
        "X-Scrapfly-Project-Concurrent-Usage",
        "X-Scrapfly-Project-Remaining-Concurrent-Usage"
    ]:
        value = headers.get(header)
        if value:
            logger.info(f"{header}: {value}")

def handle_scrapfly_error(error, url, is_screenshot=False):
    """Handle Scrapfly API errors based on HTTP status codes."""
    status_code = error.response.status_code
    error_headers = error.response.headers
    
    logger.error(f"Error {status_code} for {url}")
    logger.error(f"Reject Code: {error_headers.get('X-Scrapfly-Reject-Code')}")
    logger.error(f"Reject Description: {error_headers.get('X-Scrapfly-Reject-Description')}")
    logger.error(f"Retryable: {error_headers.get('X-Scrapfly-Reject-Retryable')}")
    
    if status_code == 401:
        logger.error("Unauthorized: Invalid API key provided.")
    elif status_code == 429:
        logger.error("Too Many Requests: Free quota used or max concurrency reached.")
    elif status_code == 422 and is_screenshot:
        if error_headers.get("X-Scrapfly-Reject-Code") == "ERR::SCREENSHOT::INVALID_CONTENT_TYPE":
            logger.error("Invalid content type for screenshot. Only text/* content types are supported.")

def main():
    """Main function to scrape posts and capture screenshots for all profiles."""
    for profile_url in PROFILE_URLS:
        logger.info(f"Processing profile: {profile_url}")
        
        # Scrape posts
        logger.info("Scraping posts...")
        scrape_result = scrape_profile_posts(profile_url)
        
        # Capture screenshot
        logger.info("Capturing screenshot...")
        screenshot_result = capture_profile_screenshot(profile_url)
        
        if scrape_result and screenshot_result:
            logger.info(f"Successfully processed {profile_url}")
        else:
            logger.warning(f"Failed to fully process {profile_url}")

if __name__ == "__main__":
    main()
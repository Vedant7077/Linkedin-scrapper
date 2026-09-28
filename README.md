# LinkedIn Scraper & Automation

A simple project designed to extract LinkedIn profile information and recent posts. 

It provides two different ways to accomplish the exact same task:
1. **Python Script & REST API** (Custom code solution)
2. **n8n Automation Workflow** (No-code / Low-code scheduled pipeline)

---

## What Does This Project Do?

* Extracts basic profile details: Name, Headline, and Avatar/Profile Picture.
* Retrieves recent posts, post text, media images, and original post URLs.
* Structures the extracted data cleanly into JSON or directly into a database (MongoDB).

---

## Solution 1: Python Scraper & REST API

### Key Files
* **app.py**: A Flask REST API that accepts profile URLs and returns scraped profile data.
* **scraper.py**: Playwright-based scraper that handles login, cookies, and data extraction.
* **cookie_refresher.py**: Launches an interactive browser to refresh and save session cookies.
* **new_scrapper.py**: Alternative Selenium-based scraping script.

### How It Works
* The Flask server runs on port 5001.
* Send a POST request to `/scrape` with LinkedIn profile URLs.
* The script launches a browser (using saved cookies or provided login) and collects profile and post details.

### Quick Start
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
2. Start the API server:
   ```bash
   python app.py
   ```
3. Test with a sample request:
   ```bash
   curl -X POST http://localhost:5001/scrape \
     -H "Content-Type: application/json" \
     -d '{"profiles": ["https://www.linkedin.com/in/username/"]}'
   ```

---

## Solution 2: n8n Automation Workflow

The workflow file is included in this repository as:
* `n8n_linkedin_workflow.json`

### Workflow Steps
* **Schedule Trigger**: Automatically runs on a timer (e.g., daily at 10:00 AM).
* **Fetch Profiles**: Pulls target user/student records from a MongoDB collection (`students`).
* **Format URLs**: Cleans usernames and converts them into full LinkedIn profile URLs while removing duplicates.
* **Scrape Posts**: Calls the Apify LinkedIn actor with a 24-hour filter to grab only fresh posts.
* **Check Status & Wait**: Polls until the scraping run completes successfully.
* **Format & Store**: Cleans the resulting fields and saves the posts directly into the MongoDB `blogs` collection with a `pending` status.

---

## How n8n Saves Time Compared to Custom Code

Both solutions achieve the same end result, but the n8n workflow offers key advantages:

* **No Server Maintenance**: Runs automatically in your n8n workspace without having to keep a Python process or server running 24/7.
* **Zero Browser Headaches**: Eliminates the need to constantly deal with ChromeDriver versions, Playwright dependencies, and headless browser crashes.
* **Bypasses Anti-Bot & Cookie Expirations**: Uses Apify's managed actors so you do not need to manually log in, solve CAPTCHAs, or refresh session cookies (`li_at`).
* **Built-in Scheduling & Retries**: Has automatic daily timers, error handling, and retry loops out of the box.
* **Direct Database Integration**: Reads directly from your MongoDB `students` collection and writes results straight to `blogs` with no custom database glue code required.

---

## How to Import the n8n Workflow

1. Open your n8n web dashboard.
2. Click **Add Workflow** -> Select **Import from File...**
3. Choose `n8n_linkedin_workflow.json`.
4. Connect your own MongoDB and Apify credentials in the respective nodes.
5. Activate the workflow.

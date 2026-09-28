import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode

class LinkedInJobsAPI:
    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    def query(self, queryOptions: dict):
        """
        Query LinkedIn Jobs API (unofficial) and return structured job objects.
        """
        params = {
            "keywords": queryOptions.get("keyword", ""),
            "location": queryOptions.get("location", ""),
            "start": int(queryOptions.get("page", "0")) * int(queryOptions.get("limit", "10")),
            "count": queryOptions.get("limit", "10"),
        }

        # Send GET request with headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = requests.get(self.BASE_URL, params=params, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed request {response.status_code}")

        # Parse HTML (LinkedIn returns HTML list items, not JSON)
        soup = BeautifulSoup(response.text, "html.parser")
        job_cards = soup.find_all("li")

        jobs = []
        for job in job_cards:
            # Extract job details
            title_tag = job.find("h3", {"class": "base-search-card__title"})
            company_tag = job.find("h4", {"class": "base-search-card__subtitle"})
            logo_tag = job.find("img", {"class": "artdeco-entity-image"})
            location_tag = job.find("span", {"class": "job-search-card__location"})
            date_tag = job.find("time")
            link_tag = job.find("a", {"class": "base-card__full-link"})

            job_obj = {
                "position": title_tag.get_text(strip=True) if title_tag else None,
                "company": company_tag.get_text(strip=True) if company_tag else None,
                "companyLogo": logo_tag["data-delayed-url"] if logo_tag and logo_tag.has_attr("data-delayed-url") else "",
                "location": location_tag.get_text(strip=True) if location_tag else None,
                "date": date_tag["datetime"] if date_tag and date_tag.has_attr("datetime") else None,
                "agoTime": date_tag.get_text(strip=True) if date_tag else None,
                "salary": "",  # LinkedIn rarely exposes salary directly
                "jobUrl": link_tag["href"] if link_tag else None,
            }

            jobs.append(job_obj)

        return jobs


# ---------- Example Usage ----------
if __name__ == "__main__":
    api = LinkedInJobsAPI()
    queryOptions = {
        "keyword": "software engineer",
        "location": "India",
        "dateSincePosted": "past week",   # currently unused, but can be mapped
        "jobType": "full time",           # currently unused, but can be mapped
        "remoteFilter": "remote",         # currently unused, but can be mapped
        "salary": "100000",               # currently unused
        "experienceLevel": "entry level", # currently unused
        "limit": "10",
        "page": "0",
        "has_verification": False,
        "under_10_applicants": False
    }

    jobs = api.query(queryOptions)
    for j in jobs:
        print(j)

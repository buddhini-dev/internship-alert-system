```python
import hashlib
import logging
import time
from typing import Any, Dict, List

import feedparser
import requests
from bs4 import BeautifulSoup

from config import config


logger = logging.getLogger(__name__)


# ============================================================
# SOURCE URLS
# ============================================================

REMOTE_OK_API = "https://remoteok.com/api"

ITPRO_INTERNSHIP_RSS = (
    "https://itpro.lk/rss/all/internship"
)

TOPJOBS_RECENT_URL = (
    "https://www.topjobs.lk/recentjobs.jsp"
)


# ============================================================
# REQUEST HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}


# ============================================================
# JOB ID
# ============================================================

def create_job_id(
    title: str,
    company: str,
    url: str
) -> str:

    raw = (
        f"{title}|{company}|{url}"
        .lower()
        .strip()
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# REMOTEOK
# ============================================================

def fetch_remoteok() -> List[Dict[str, Any]]:

    for attempt in range(
        1,
        config.MAX_RETRIES + 1
    ):

        try:

            logger.info(
                "Fetching RemoteOK "
                "(attempt %s/%s)",
                attempt,
                config.MAX_RETRIES
            )

            response = requests.get(
                REMOTE_OK_API,
                headers=HEADERS,
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            jobs = []

            for item in data:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                title = (
                    item.get("position")
                    or ""
                ).strip()

                company = (
                    item.get("company")
                    or ""
                ).strip()

                url = (
                    item.get("url")
                    or ""
                ).strip()

                if not title or not url:
                    continue

                job_id = create_job_id(
                    title,
                    company,
                    url
                )

                jobs.append(
                    {
                        "id": job_id,
                        "title": title,
                        "company": company,
                        "url": url,
                        "description": (
                            item.get(
                                "description",
                                ""
                            )
                        ),
                        "location": (
                            item.get(
                                "location",
                                "Remote"
                            )
                        ),
                        "tags": item.get(
                            "tags",
                            []
                        ),
                        "date": item.get(
                            "date"
                        ),
                        "source": "RemoteOK",
                    }
                )

            logger.info(
                "RemoteOK returned %s jobs",
                len(jobs)
            )

            return jobs

        except requests.RequestException as error:

            logger.warning(
                "RemoteOK request failed: %s",
                error
            )

            if attempt < config.MAX_RETRIES:

                time.sleep(
                    config.REQUEST_DELAY
                )

        except ValueError as error:

            logger.error(
                "RemoteOK JSON error: %s",
                error
            )

            return []

    return []


# ============================================================
# ITPRO.LK
# ============================================================

def fetch_itpro() -> List[Dict[str, Any]]:

    logger.info(
        "Fetching ITPro.lk internship RSS feed"
    )

    try:

        response = requests.get(
            ITPRO_INTERNSHIP_RSS,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        feed = feedparser.parse(
            response.content
        )

        jobs = []

        for entry in feed.entries:

            title = (
                entry.get("title")
                or ""
            ).strip()

            url = (
                entry.get("link")
                or ""
            ).strip()

            if not title or not url:
                continue

            description = (
                entry.get(
                    "summary",
                    ""
                )
            )

            soup = BeautifulSoup(
                description,
                "html.parser"
            )

            description = soup.get_text(
                " ",
                strip=True
            )

            company = (
                entry.get(
                    "author",
                    ""
                )
                or "ITPro.lk Listing"
            )

            published = (
                entry.get(
                    "published",
                    ""
                )
            )

            job_id = create_job_id(
                title,
                company,
                url
            )

            jobs.append(
                {
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "url": url,
                    "description": description,
                    "location": "Sri Lanka",
                    "tags": [],
                    "date": published,
                    "source": "ITPro.lk",
                }
            )

        logger.info(
            "ITPro.lk returned %s jobs",
            len(jobs)
        )

        return jobs

    except requests.RequestException as error:

        logger.error(
            "ITPro.lk request failed: %s",
            error
        )

        return []

    except Exception as error:

        logger.error(
            "ITPro.lk RSS parsing failed: %s",
            error
        )

        return []


# ============================================================
# TOPJOBS
# ============================================================

def fetch_topjobs() -> List[Dict[str, Any]]:

    logger.info(
        "Fetching TopJobs recent jobs"
    )

    try:

        response = requests.get(
            TOPJOBS_RECENT_URL,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        jobs = []

        # ----------------------------------------------------
        # Inspect all links on the Recent Jobs page.
        # TopJobs can use different HTML structures, so
        # we inspect the link and surrounding containers.
        # ----------------------------------------------------

        for link in soup.find_all(
            "a",
            href=True
        ):

            title = link.get_text(
                " ",
                strip=True
            )

            href = link.get(
                "href",
                ""
            ).strip()

            if not title or not href:
                continue

            # ------------------------------------------------
            # Build full URL
            # ------------------------------------------------

            full_url = href

            if href.startswith("/"):

                full_url = (
                    "https://www.topjobs.lk"
                    + href
                )

            elif href.startswith("./"):

                full_url = (
                    "https://www.topjobs.lk/"
                    + href[2:]
                )

            elif href.startswith(
                "www.topjobs.lk"
            ):

                full_url = (
                    "https://"
                    + href
                )

            if not full_url.startswith(
                "http"
            ):
                continue

            # ------------------------------------------------
            # Make sure this looks like a job link.
            # ------------------------------------------------

            href_lower = href.lower()

            job_link = any(
                part in href_lower
                for part in [
                    "job",
                    "vacancy",
                    "jobs",
                    "jobdetails",
                ]
            )

            if not job_link:
                continue

            # ------------------------------------------------
            # Get surrounding text.
            # ------------------------------------------------

            parent_text = ""

            parent = link.parent

            if parent:

                parent_text = (
                    parent.get_text(
                        " ",
                        strip=True
                    )
                )

            # Check grandparent as well.
            grandparent = (
                parent.parent
                if parent
                else None
            )

            if grandparent:

                grandparent_text = (
                    grandparent.get_text(
                        " ",
                        strip=True
                    )
                )

                if len(
                    grandparent_text
                ) > len(
                    parent_text
                ):

                    parent_text = (
                        grandparent_text
                    )

            # ------------------------------------------------
            # Combine title + surrounding text.
            # ------------------------------------------------

            combined_text = (
                f"{title} "
                f"{parent_text}"
            ).lower()

            # ------------------------------------------------
            # Identify possible technology/
            # internship listings.
            #
            # Exact filtering happens later in main.py.
            # ------------------------------------------------

            possible_role = any(
                keyword in combined_text
                for keyword in [
                    "intern",
                    "internship",
                    "trainee",
                    "software",
                    "developer",
                    "data scientist",
                    "data science",
                    "data engineer",
                    "data engineering",
                    "machine learning",
                    "artificial intelligence",
                    "ai/ml",
                    "ml engineer",
                    "cloud engineer",
                    "cloud",
                    "devops",
                ]
            )

            if not possible_role:
                continue

            # ------------------------------------------------
            # Try to identify company.
            # ------------------------------------------------

            company = (
                "TopJobs Listing"
            )

            separators = [
                " - ",
                " | ",
                " – ",
                " — ",
            ]

            for separator in separators:

                if separator in parent_text:

                    parts = (
                        parent_text.split(
                            separator,
                            1
                        )
                    )

                    if len(parts) == 2:

                        possible_company = (
                            parts[1].strip()
                        )

                        if (
                            possible_company
                            and len(
                                possible_company
                            ) < 150
                        ):

                            company = (
                                possible_company
                            )

                            break

            # ------------------------------------------------
            # Create unique ID.
            # ------------------------------------------------

            job_id = create_job_id(
                title,
                company,
                full_url
            )

            jobs.append(
                {
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "url": full_url,
                    "description": parent_text,
                    "location": "Sri Lanka",
                    "tags": [],
                    "date": None,
                    "source": "TopJobs",
                }
            )

        # ----------------------------------------------------
        # Remove duplicates.
        # ----------------------------------------------------

        unique_jobs = {}

        for job in jobs:

            unique_jobs[
                job["id"]
            ] = job

        jobs = list(
            unique_jobs.values()
        )

        logger.info(
            "TopJobs returned %s possible jobs",
            len(jobs)
        )

        return jobs

    except requests.RequestException as error:

        logger.error(
            "TopJobs request failed: %s",
            error
        )

        return []

    except Exception as error:

        logger.error(
            "TopJobs parsing failed: %s",
            error
        )

        return []


# ============================================================
# FETCH ALL SOURCES
# ============================================================

def fetch_all_jobs() -> List[Dict[str, Any]]:

    all_jobs = []

    # --------------------------------------------------------
    # RemoteOK
    # --------------------------------------------------------

    remoteok_jobs = fetch_remoteok()

    all_jobs.extend(
        remoteok_jobs
    )

    # --------------------------------------------------------
    # ITPro.lk
    # --------------------------------------------------------

    itpro_jobs = fetch_itpro()

    all_jobs.extend(
        itpro_jobs
    )

    # --------------------------------------------------------
    # TopJobs
    # --------------------------------------------------------

    topjobs_jobs = fetch_topjobs()

    all_jobs.extend(
        topjobs_jobs
    )

    # --------------------------------------------------------
    # Remove duplicates across all sources.
    # --------------------------------------------------------

    unique_jobs = {}

    for job in all_jobs:

        job_id = job.get(
            "id"
        )

        if job_id:

            unique_jobs[
                job_id
            ] = job

    combined_jobs = list(
        unique_jobs.values()
    )

    logger.info(
        "Combined jobs from all sources: %s",
        len(combined_jobs)
    )

    return combined_jobs
```

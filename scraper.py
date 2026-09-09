import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import feedparser
import requests
from bs4 import BeautifulSoup

from config import config


logger = logging.getLogger(__name__)

REMOTE_OK_API = "https://remoteok.com/api"

ITPRO_INTERNSHIP_RSS = (
    "https://itpro.lk/rss/all/internship"
)

TOPJOBS_RECENT_URL = (
    "https://www.topjobs.lk/recentjobs.jsp"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}


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

                if not isinstance(item, dict):
                    continue

                title = (
                    item.get("position") or ""
                ).strip()

                company = (
                    item.get("company") or ""
                ).strip()

                url = (
                    item.get("url") or ""
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
                entry.get("title") or ""
            ).strip()

            url = (
                entry.get("link") or ""
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

        # TopJobs publishes a recent-jobs page.
        # We inspect links and nearby text to identify
        # relevant technology/internship postings.

        for link in soup.find_all(
            "a",
            href=True
        ):

            title = link.get_text(
                " ",
                strip=True
            )

            if not title:
                continue

            href = link.get(
                "href",
                ""
            ).strip()

            full_url = href

            if href.startswith("/"):
                full_url = (
                    "https://www.topjobs.lk"
                    + href
                )

            if not full_url.startswith(
                "http"
            ):
                continue

            title_lower = title.lower()

            possible_role = any(
                keyword in title_lower
                for keyword in [
                    "intern",
                    "internship",
                    "software",
                    "developer",
                    "data",
                    "machine learning",
                    "artificial intelligence",
                    "ai",
                    "engineer",
                    "qa",
                    "devops",
                    "cloud",
                ]
            )

            if not possible_role:
                continue

            parent_text = ""

            if link.parent:
                parent_text = link.parent.get_text(
                    " ",
                    strip=True
                )

            company = (
                "TopJobs Listing"
            )

            if " - " in parent_text:

                parts = parent_text.split(
                    " - ",
                    1
                )

                if len(parts) == 2:
                    possible_company = (
                        parts[1].strip()
                    )

                    if possible_company:
                        company = (
                            possible_company
                        )

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

        # Remove duplicate IDs
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


def fetch_all_jobs() -> List[Dict[str, Any]]:

    all_jobs = []

    remoteok_jobs = fetch_remoteok()
    all_jobs.extend(
        remoteok_jobs
    )

    itpro_jobs = fetch_itpro()
    all_jobs.extend(
        itpro_jobs
    )

    topjobs_jobs = fetch_topjobs()
    all_jobs.extend(
        topjobs_jobs
    )

    # Remove duplicates across sources.
    unique_jobs = {}

    for job in all_jobs:

        job_id = job.get("id")

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

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

from config import config


logger = logging.getLogger(__name__)

REMOTE_OK_API = "https://remoteok.com/api"


def create_job_id(title: str, company: str, url: str) -> str:
    """
    Creates a stable ID for a job.
    """

    raw = f"{title}|{company}|{url}".lower().strip()

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def parse_remoteok_date(date_string: str):
    """
    Convert RemoteOK date to datetime.
    """

    if not date_string:
        return None

    try:
        date_string = date_string.replace("Z", "+00:00")

        return datetime.fromisoformat(date_string)

    except ValueError:
        return None


def fetch_remoteok() -> List[Dict[str, Any]]:
    """
    Fetch jobs from RemoteOK public JSON feed.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(compatible; InternshipAlertSystem/1.0)"
        )
    }

    for attempt in range(1, config.MAX_RETRIES + 1):

        try:
            logger.info(
                "Fetching jobs from RemoteOK "
                "(attempt %s/%s)",
                attempt,
                config.MAX_RETRIES
            )

            response = requests.get(
                REMOTE_OK_API,
                headers=headers,
                timeout=30
            )

            response.raise_for_status()

            data = response.json()

            jobs = []

            for item in data:

                # RemoteOK feed may contain metadata objects.
                if not isinstance(item, dict):
                    continue

                if not item.get("position"):
                    continue

                title = item.get("position", "").strip()
                company = item.get("company", "").strip()
                url = item.get("url", "").strip()

                if not url:
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
                        "description": item.get(
                            "description", ""
                        ),
                        "location": item.get(
                            "location", "Remote"
                        ),
                        "tags": item.get("tags", []),
                        "date": item.get("date"),
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
                time.sleep(config.REQUEST_DELAY)

        except ValueError as error:

            logger.error(
                "Could not parse RemoteOK JSON: %s",
                error
            )

            break

    return []


def fetch_all_jobs() -> List[Dict[str, Any]]:
    """
    Main scraper entry point.
    """

    jobs = fetch_remoteok()

    return jobs

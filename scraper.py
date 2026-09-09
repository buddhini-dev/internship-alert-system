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

XPRESSJOBS_INTERNSHIP_URL = (
    "https://xpress.jobs/jobs?Sectors=27"
)

INTERNJOBS_URL = (
    "https://internjobs.lk/"
)

WELLFOUND_REMOTE_URL = (
    "https://wellfound.com/remote"
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
    ),
    "Accept-Language": (
        "en-US,en;q=0.9"
    ),
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
# HELPER: CLEAN TEXT
# ============================================================

def clean_text(
    value: Any
) -> str:

    if value is None:
        return ""

    return BeautifulSoup(
        str(value),
        "html.parser"
    ).get_text(
        " ",
        strip=True
    )


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

            description = clean_text(
                entry.get(
                    "summary",
                    ""
                )
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

            parent_text = ""

            parent = link.parent

            if parent:

                parent_text = (
                    parent.get_text(
                        " ",
                        strip=True
                    )
                )

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

            combined_text = (
                f"{title} "
                f"{parent_text}"
            ).lower()

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
# XPRESSJOBS
# ============================================================

def fetch_xpressjobs() -> List[Dict[str, Any]]:

    logger.info(
        "Fetching XpressJobs internship listings"
    )

    try:

        response = requests.get(
            XPRESSJOBS_INTERNSHIP_URL,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        jobs = []

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

            # XpressJobs job links commonly contain
            # /Jobs/View/
            if (
                "/Jobs/View/"
                not in href
                and "/Jobs/view/"
                not in href
            ):
                continue

            if href.startswith("/"):

                full_url = (
                    "https://xpress.jobs"
                    + href
                )

            elif href.startswith("http"):

                full_url = href

            else:

                full_url = (
                    "https://xpress.jobs/"
                    + href.lstrip("/")
                )

            # Get nearby text.
            parent_text = ""

            if link.parent:

                parent_text = (
                    link.parent.get_text(
                        " ",
                        strip=True
                    )
                )

            grandparent = (
                link.parent.parent
                if link.parent
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

            combined_text = (
                f"{title} "
                f"{parent_text}"
            ).lower()

            # The final filtering is done in main.py.
            # Here we only reject obviously irrelevant
            # listings.
            technology_or_internship = any(
                keyword in combined_text
                for keyword in [
                    "intern",
                    "internship",
                    "trainee",
                    "software",
                    "developer",
                    "data",
                    "machine learning",
                    "artificial intelligence",
                    "ai",
                    "engineer",
                ]
            )

            if not technology_or_internship:
                continue

            company = (
                "XpressJobs Listing"
            )

            # Try common company separators.
            for separator in [
                " | ",
                " - ",
                " – ",
                " — ",
            ]:

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
                    "source": "XpressJobs",
                }
            )

        unique_jobs = {}

        for job in jobs:

            unique_jobs[
                job["id"]
            ] = job

        jobs = list(
            unique_jobs.values()
        )

        logger.info(
            "XpressJobs returned %s possible jobs",
            len(jobs)
        )

        return jobs

    except requests.RequestException as error:

        logger.error(
            "XpressJobs request failed: %s",
            error
        )

        return []

    except Exception as error:

        logger.error(
            "XpressJobs parsing failed: %s",
            error
        )

        return []


# ============================================================
# INTERNJOBS.LK
# ============================================================

def fetch_internjobs() -> List[Dict[str, Any]]:

    logger.info(
        "Fetching InternJobs.lk listings"
    )

    try:

        response = requests.get(
            INTERNJOBS_URL,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        jobs = []

        # Search for links that look like job pages.
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

            href_lower = href.lower()

            # Ignore navigation and blog links.
            possible_job = any(
                keyword in href_lower
                for keyword in [
                    "/job",
                    "/jobs",
                    "/intern",
                    "/internship",
                    "/vacancy",
                ]
            )

            if not possible_job:
                continue

            if href.startswith("/"):

                full_url = (
                    "https://internjobs.lk"
                    + href
                )

            elif href.startswith("http"):

                full_url = href

            else:

                full_url = (
                    "https://internjobs.lk/"
                    + href.lstrip("/")
                )

            parent_text = ""

            if link.parent:

                parent_text = (
                    link.parent.get_text(
                        " ",
                        strip=True
                    )
                )

            grandparent = (
                link.parent.parent
                if link.parent
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

            combined_text = (
                f"{title} "
                f"{parent_text}"
            ).lower()

            possible_role = any(
                keyword in combined_text
                for keyword in [
                    "intern",
                    "internship",
                    "software",
                    "developer",
                    "data scientist",
                    "data science",
                    "data engineer",
                    "machine learning",
                    "artificial intelligence",
                    "ai",
                    "engineer",
                ]
            )

            if not possible_role:
                continue

            company = (
                "InternJobs.lk Listing"
            )

            for separator in [
                " | ",
                " - ",
                " – ",
                " — ",
            ]:

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
                    "source": "InternJobs.lk",
                }
            )

        unique_jobs = {}

        for job in jobs:

            unique_jobs[
                job["id"]
            ] = job

        jobs = list(
            unique_jobs.values()
        )

        logger.info(
            "InternJobs.lk returned %s possible jobs",
            len(jobs)
        )

        return jobs

    except requests.RequestException as error:

        logger.error(
            "InternJobs.lk request failed: %s",
            error
        )

        return []

    except Exception as error:

        logger.error(
            "InternJobs.lk parsing failed: %s",
            error
        )

        return []


# ============================================================
# WELLFOUND
# ============================================================

def fetch_wellfound() -> List[Dict[str, Any]]:

    logger.info(
        "Fetching Wellfound remote jobs"
    )

    try:

        response = requests.get(
            WELLFOUND_REMOTE_URL,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        jobs = []

        # Wellfound contains many links, so only inspect
        # links that look like job pages.
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

            if "/jobs/" not in href:
                continue

            if href.startswith("/"):

                full_url = (
                    "https://wellfound.com"
                    + href
                )

            elif href.startswith("http"):

                full_url = href

            else:

                continue

            title_lower = title.lower()

            possible_role = any(
                keyword in title_lower
                for keyword in [
                    "software",
                    "developer",
                    "engineering",
                    "engineer",
                    "machine learning",
                    "ml",
                    "ai",
                    "data scientist",
                    "data science",
                    "data engineer",
                ]
            )

            if not possible_role:
                continue

            internship_related = any(
                keyword in title_lower
                for keyword in [
                    "intern",
                    "internship",
                    "trainee",
                    "student",
                ]
            )

            # We primarily want internships.
            # Some Wellfound internship listings don't
            # put "intern" in the visible short title,
            # so inspect nearby text as well.
            parent_text = ""

            if link.parent:

                parent_text = (
                    link.parent.get_text(
                        " ",
                        strip=True
                    )
                )

            combined_text = (
                f"{title} "
                f"{parent_text}"
            ).lower()

            if not internship_related:

                internship_related = any(
                    keyword in combined_text
                    for keyword in [
                        "internship",
                        "intern ",
                        " internship ",
                        "no experience required",
                    ]
                )

            if not internship_related:
                continue

            company = (
                "Wellfound Listing"
            )

            # The surrounding company information
            # varies by page layout. Keep a safe default
            # rather than inventing a company.
            if link.parent:

                parent_links = (
                    link.parent.find_all(
                        "a",
                        href=True
                    )
                )

                for candidate in parent_links:

                    candidate_text = (
                        candidate.get_text(
                            " ",
                            strip=True
                        )
                    )

                    if (
                        candidate_text
                        and candidate_text != title
                        and len(
                            candidate_text
                        ) < 100
                    ):

                        company = (
                            candidate_text
                        )

                        break

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
                    "location": "Remote",
                    "tags": [],
                    "date": None,
                    "source": "Wellfound",
                }
            )

        unique_jobs = {}

        for job in jobs:

            unique_jobs[
                job["id"]
            ] = job

        jobs = list(
            unique_jobs.values()
        )

        logger.info(
            "Wellfound returned %s possible jobs",
            len(jobs)
        )

        return jobs

    except requests.RequestException as error:

        logger.error(
            "Wellfound request failed: %s",
            error
        )

        return []

    except Exception as error:

        logger.error(
            "Wellfound parsing failed: %s",
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
    # XpressJobs
    # --------------------------------------------------------

    xpressjobs_jobs = fetch_xpressjobs()

    all_jobs.extend(
        xpressjobs_jobs
    )

    # --------------------------------------------------------
    # InternJobs.lk
    # --------------------------------------------------------

    internjobs_jobs = fetch_internjobs()

    all_jobs.extend(
        internjobs_jobs
    )

    # --------------------------------------------------------
    # Wellfound
    # --------------------------------------------------------

    wellfound_jobs = fetch_wellfound()

    all_jobs.extend(
        wellfound_jobs
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


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        )
    )

    jobs = fetch_all_jobs()

    print(
        f"Fetched {len(jobs)} total jobs."
    )

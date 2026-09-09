import hashlib
import logging
import time
from typing import Any, Dict, List
from urllib.parse import quote, urljoin

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

WELLFOUND_ROLE_URLS = [
    "https://wellfound.com/role/software-developer",
    "https://wellfound.com/role/data-scientist",
    "https://wellfound.com/role/data-engineer",
    "https://wellfound.com/role/machine-learning-engineer",
]

# Google News RSS is used only as a discovery fallback
# for sites that block GitHub Actions directly.
GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search?q="
)

LINKEDIN_SEARCH_QUERIES = [
    'site:linkedin.com/jobs/view "software engineer" "intern"',
    'site:linkedin.com/jobs/view "software developer" "intern"',
    'site:linkedin.com/jobs/view "data science" "intern"',
    'site:linkedin.com/jobs/view "data scientist" "intern"',
    'site:linkedin.com/jobs/view "machine learning" "intern"',
    'site:linkedin.com/jobs/view "AI" "intern"',
    'site:linkedin.com/jobs/view "data engineer" "intern"',
]

XPRESSJOBS_SEARCH_QUERIES = [
    'site:xpress.jobs "software engineer" intern',
    'site:xpress.jobs "software developer" intern',
    'site:xpress.jobs "data science" intern',
    'site:xpress.jobs "data scientist" intern',
    'site:xpress.jobs "machine learning" intern',
    'site:xpress.jobs "data engineer" intern',
]


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
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": (
        "en-US,en;q=0.9"
    ),
    "Connection": "keep-alive",
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
# HELPER: BUILD JOB
# ============================================================

def make_job(
    title: str,
    company: str,
    url: str,
    description: str,
    location: str,
    source: str,
    date: Any = None,
    tags: Any = None,
) -> Dict[str, Any]:

    job_id = create_job_id(
        title,
        company,
        url
    )

    return {
        "id": job_id,
        "title": title.strip(),
        "company": company.strip()
        if company
        else "Unknown",
        "url": url.strip(),
        "description": description or "",
        "location": location or "Unknown",
        "tags": tags or [],
        "date": date,
        "source": source,
    }


# ============================================================
# HELPER: UNIQUE JOBS
# ============================================================

def unique_jobs(
    jobs: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    unique = {}

    for job in jobs:

        job_id = job.get("id")

        if job_id:
            unique[job_id] = job

    return list(
        unique.values()
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

                jobs.append(
                    make_job(
                        title=title,
                        company=company,
                        url=url,
                        description=item.get(
                            "description",
                            ""
                        ),
                        location=item.get(
                            "location",
                            "Remote"
                        ),
                        source="RemoteOK",
                        date=item.get(
                            "date"
                        ),
                        tags=item.get(
                            "tags",
                            []
                        ),
                    )
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

            jobs.append(
                make_job(
                    title=title,
                    company=company,
                    url=url,
                    description=description,
                    location="Sri Lanka",
                    source="ITPro.lk",
                    date=published,
                )
            )

        logger.info(
            "ITPro.lk returned %s jobs",
            len(jobs)
        )

        return unique_jobs(jobs)

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

            full_url = urljoin(
                "https://www.topjobs.lk/",
                href
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

            if link.parent:

                parent_text = (
                    link.parent.get_text(
                        " ",
                        strip=True
                    )
                )

            if link.parent and link.parent.parent:

                grandparent_text = (
                    link.parent.parent.get_text(
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
                    "devops",
                ]
            )

            if not possible_role:
                continue

            company = "TopJobs Listing"

            for separator in [
                " - ",
                " | ",
                " – ",
                " — ",
            ]:

                if separator in parent_text:

                    parts = parent_text.split(
                        separator,
                        1
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

            jobs.append(
                make_job(
                    title=title,
                    company=company,
                    url=full_url,
                    description=parent_text,
                    location="Sri Lanka",
                    source="TopJobs",
                )
            )

        jobs = unique_jobs(jobs)

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
# XPRESSJOBS DIRECT
# ============================================================

def fetch_xpressjobs_direct() -> List[Dict[str, Any]]:

    logger.info(
        "Fetching XpressJobs internship listings directly"
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

            href_lower = href.lower()

            if (
                "/jobs/view/"
                not in href_lower
            ):
                continue

            full_url = urljoin(
                "https://xpress.jobs/",
                href
            )

            parent_text = ""

            if link.parent:

                parent_text = (
                    link.parent.get_text(
                        " ",
                        strip=True
                    )
                )

            if link.parent and link.parent.parent:

                grandparent_text = (
                    link.parent.parent.get_text(
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

            for separator in [
                " | ",
                " - ",
                " – ",
                " — ",
            ]:

                if separator in parent_text:

                    parts = parent_text.split(
                        separator,
                        1
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

            jobs.append(
                make_job(
                    title=title,
                    company=company,
                    url=full_url,
                    description=parent_text,
                    location="Sri Lanka",
                    source="XpressJobs",
                )
            )

        jobs = unique_jobs(jobs)

        logger.info(
            "XpressJobs direct returned %s jobs",
            len(jobs)
        )

        return jobs

    except requests.RequestException as error:

        logger.warning(
            "XpressJobs direct request failed: %s",
            error
        )

        return []

    except Exception as error:

        logger.warning(
            "XpressJobs direct parsing failed: %s",
            error
        )

        return []


# ============================================================
# GOOGLE NEWS RSS DISCOVERY
# ============================================================

def fetch_google_news_results(
    queries: List[str],
    source_name: str,
    source_domains: List[str],
) -> List[Dict[str, Any]]:

    jobs = []

    for query in queries:

        try:

            encoded_query = quote(
                query
            )

            url = (
                GOOGLE_NEWS_RSS
                + encoded_query
            )

            logger.info(
                "%s discovery search: %s",
                source_name,
                query
            )

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=30
            )

            response.raise_for_status()

            feed = feedparser.parse(
                response.content
            )

            for entry in feed.entries:

                title = clean_text(
                    entry.get(
                        "title",
                        ""
                    )
                )

                link = (
                    entry.get(
                        "link",
                        ""
                    )
                    or ""
                ).strip()

                description = clean_text(
                    entry.get(
                        "summary",
                        ""
                    )
                )

                combined = (
                    f"{title} "
                    f"{description}"
                ).lower()

                # We only want our intended source.
                source_match = any(
                    domain.lower()
                    in combined
                    or domain.lower()
                    in link.lower()
                    for domain in source_domains
                )

                if not source_match:
                    continue

                # Google News may return its own redirect.
                # Keep only obvious source URLs.
                source_url = link

                for domain in source_domains:

                    if domain.lower() in link.lower():

                        source_url = link
                        break

                if not source_url.startswith(
                    "http"
                ):
                    continue

                company = (
                    f"{source_name} Listing"
                )

                jobs.append(
                    make_job(
                        title=title,
                        company=company,
                        url=source_url,
                        description=description,
                        location=(
                            "Remote"
                            if source_name
                            == "LinkedIn"
                            else "Sri Lanka"
                        ),
                        source=source_name,
                        date=entry.get(
                            "published"
                        ),
                    )
                )

            time.sleep(
                1
            )

        except requests.RequestException as error:

            logger.warning(
                "%s discovery request failed: %s",
                source_name,
                error
            )

        except Exception as error:

            logger.warning(
                "%s discovery parsing failed: %s",
                source_name,
                error
            )

    jobs = unique_jobs(jobs)

    logger.info(
        "%s discovery returned %s possible jobs",
        source_name,
        len(jobs)
    )

    return jobs


# ============================================================
# XPRESSJOBS FALLBACK
# ============================================================

def fetch_xpressjobs() -> List[Dict[str, Any]]:

    direct_jobs = (
        fetch_xpressjobs_direct()
    )

    if direct_jobs:
        return direct_jobs

    logger.info(
        "Using XpressJobs discovery fallback"
    )

    return fetch_google_news_results(
        queries=XPRESSJOBS_SEARCH_QUERIES,
        source_name="XpressJobs",
        source_domains=[
            "xpress.jobs"
        ],
    )


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

            full_url = urljoin(
                INTERNJOBS_URL,
                href
            )

            parent_text = ""

            if link.parent:

                parent_text = (
                    link.parent.get_text(
                        " ",
                        strip=True
                    )
                )

            if link.parent and link.parent.parent:

                grandparent_text = (
                    link.parent.parent.get_text(
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

                    parts = parent_text.split(
                        separator,
                        1
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

            jobs.append(
                make_job(
                    title=title,
                    company=company,
                    url=full_url,
                    description=parent_text,
                    location="Sri Lanka",
                    source="InternJobs.lk",
                )
            )

        jobs = unique_jobs(jobs)

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
        "Fetching Wellfound role pages"
    )

    jobs = []

    for role_url in WELLFOUND_ROLE_URLS:

        try:

            response = requests.get(
                role_url,
                headers=HEADERS,
                timeout=30
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            for link in soup.find_all(
                "a",
                href=True
            ):

                href = link.get(
                    "href",
                    ""
                ).strip()

                title = link.get_text(
                    " ",
                    strip=True
                )

                if not title:
                    continue

                if "/jobs/" not in href:
                    continue

                full_url = urljoin(
                    "https://wellfound.com/",
                    href
                )

                parent_text = ""

                if link.parent:

                    parent_text = (
                        link.parent.get_text(
                            " ",
                            strip=True
                        )
                    )

                if link.parent and link.parent.parent:

                    grandparent_text = (
                        link.parent.parent.get_text(
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

                role_match = any(
                    keyword in combined_text
                    for keyword in [
                        "software",
                        "developer",
                        "engineering",
                        "engineer",
                        "machine learning",
                        "ml",
                        "artificial intelligence",
                        "ai",
                        "data scientist",
                        "data science",
                        "data engineer",
                    ]
                )

                if not role_match:
                    continue

                internship_match = any(
                    keyword in combined_text
                    for keyword in [
                        "intern",
                        "internship",
                        "trainee",
                        "student",
                        "no experience",
                    ]
                )

                if not internship_match:
                    continue

                company = (
                    "Wellfound Listing"
                )

                # Try to identify company from
                # nearby links/text.
                if link.parent:

                    for candidate in (
                        link.parent.find_all(
                            "a",
                            href=True
                        )
                    ):

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

                jobs.append(
                    make_job(
                        title=title,
                        company=company,
                        url=full_url,
                        description=parent_text,
                        location="Remote / Global",
                        source="Wellfound",
                    )
                )

        except requests.RequestException as error:

            logger.warning(
                "Wellfound role page failed "
                "(%s): %s",
                role_url,
                error
            )

        except Exception as error:

            logger.warning(
                "Wellfound parsing failed "
                "(%s): %s",
                role_url,
                error
            )

    jobs = unique_jobs(jobs)

    logger.info(
        "Wellfound returned %s possible jobs",
        len(jobs)
    )

    return jobs


# ============================================================
# LINKEDIN
# ============================================================

def fetch_linkedin() -> List[Dict[str, Any]]:

    logger.info(
        "Fetching LinkedIn internship discoveries"
    )

    jobs = fetch_google_news_results(
        queries=LINKEDIN_SEARCH_QUERIES,
        source_name="LinkedIn",
        source_domains=[
            "linkedin.com/jobs"
        ],
    )

    # Make sure we only keep actual LinkedIn
    # job URLs, not generic LinkedIn pages.
    filtered = []

    for job in jobs:

        url = job.get(
            "url",
            ""
        ).lower()

        if (
            "linkedin.com/jobs/view"
            in url
        ):

            filtered.append(
                job
            )

    logger.info(
        "LinkedIn returned %s possible jobs",
        len(filtered)
    )

    return unique_jobs(
        filtered
    )


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
    # LinkedIn
    # --------------------------------------------------------

    linkedin_jobs = fetch_linkedin()

    all_jobs.extend(
        linkedin_jobs
    )

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    combined_jobs = unique_jobs(
        all_jobs
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

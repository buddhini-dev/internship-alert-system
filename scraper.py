import logging
import time
import hashlib
from typing import Dict, List
from urllib.parse import quote

import feedparser
import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}

REQUEST_TIMEOUT = 20


# ============================================================
# ROLE SEARCHES
# ============================================================

ROLE_SEARCHES = {
    "Data Science": [
        "data science intern",
        "data scientist intern",
        "data science internship",
        "data scientist internship",
        "data science trainee",
        "junior data scientist",
        "graduate data scientist",
    ],

    "Software Engineering": [
        "software engineer intern",
        "software engineering intern",
        "software developer intern",
        "software development intern",
        "software engineer internship",
        "software developer internship",
        "junior software engineer",
        "graduate software engineer",
        "backend developer intern",
        "backend engineering intern",
        "backend intern",
        "full stack intern",
        "full stack developer intern",
        "web developer intern",
        "application developer intern",
    ],

    "AI/ML": [
        "machine learning intern",
        "machine learning internship",
        "machine learning engineer intern",
        "ml engineer intern",
        "ml internship",
        "ai intern",
        "ai internship",
        "ai engineer intern",
        "ai/ml intern",
        "artificial intelligence intern",
        "deep learning intern",
        "generative ai intern",
        "llm intern",
        "nlp intern",
        "computer vision intern",
        "mlops intern",
        "applied ai intern",
    ],

    "Data Engineering": [
        "data engineer intern",
        "data engineering intern",
        "data engineer internship",
        "data engineering internship",
        "junior data engineer",
        "graduate data engineer",
        "analytics engineer intern",
        "big data intern",
        "big data engineer intern",
        "etl developer intern",
        "etl engineer intern",
        "data pipeline intern",
        "data warehouse intern",
        "data platform intern",
    ],

    "Analytics": [
        "data analyst intern",
        "junior data analyst",
        "business analyst intern",
        "business analytics intern",
        "business intelligence intern",
        "bi developer intern",
        "reporting analyst intern",
        "analytics intern",
        "product analytics intern",
        "decision science intern",
    ],

    "Database": [
        "database administrator intern",
        "database engineer intern",
        "sql developer intern",
        "database intern",
        "data architect intern",
    ],

    "Cloud": [
        "cloud engineering intern",
        "cloud engineer intern",
        "cloud computing intern",
        "aws intern",
        "azure intern",
        "gcp intern",
        "cloud operations intern",
    ],

    "DevOps": [
        "devops intern",
        "devops engineer intern",
        "site reliability engineer intern",
        "sre intern",
        "platform engineer intern",
    ],

    "Research": [
        "research intern ai",
        "research intern machine learning",
        "research assistant ai",
        "research assistant data science",
    ],

    "Related Data Roles": [
        "data operations intern",
        "data quality intern",
        "data governance intern",
        "quantitative analyst intern",
        "quant intern",
    ],
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def make_job_id(source: str, title: str, company: str, url: str) -> str:
    raw = f"{source}|{title}|{company}|{url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def clean_text(value: str) -> str:
    if not value:
        return ""

    soup = BeautifulSoup(str(value), "html.parser")

    return " ".join(soup.get_text(" ").split())


def request_page(url: str):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        return response

    except requests.RequestException as error:
        logger.warning(
            "Request failed: %s | %s",
            url,
            error,
        )

        return None


def add_job(
    jobs: List[Dict],
    source: str,
    title: str,
    company: str = "Unknown",
    location: str = "Unknown",
    url: str = "",
    description: str = "",
    date=None,
    category: str = None,
    tags=None,
):
    title = clean_text(title)
    company = clean_text(company)
    location = clean_text(location)
    description = clean_text(description)

    if not title or not url:
        return

    job_id = make_job_id(
        source,
        title,
        company,
        url,
    )

    jobs.append(
        {
            "id": job_id,
            "title": title,
            "company": company or "Unknown",
            "location": location or "Unknown",
            "url": url,
            "description": description,
            "date": date,
            "source": source,
            "category": category,
            "tags": tags or [],
        }
    )


# ============================================================
# REMOTEOK
# ============================================================

def fetch_remoteok() -> List[Dict]:
    jobs = []

    logger.info("Fetching RemoteOK...")

    response = request_page(
        "https://remoteok.com/api"
    )

    if response is None:
        return jobs

    try:
        data = response.json()

        for item in data:
            if not isinstance(item, dict):
                continue

            title = item.get("position", "")
            company = item.get("company", "")
            location = item.get("location", "")
            url = item.get("url", "")

            if not url:
                slug = item.get("slug", "")
                if slug:
                    url = f"https://remoteok.com/remote-jobs/{slug}"

            description = item.get("description", "")
            date = item.get("date")

            tags = item.get("tags", [])

            add_job(
                jobs=jobs,
                source="RemoteOK",
                title=title,
                company=company,
                location=location or "Remote",
                url=url,
                description=description,
                date=date,
                tags=tags,
            )

        logger.info(
            "RemoteOK: %s jobs fetched",
            len(jobs),
        )

    except Exception as error:
        logger.warning(
            "RemoteOK parsing failed: %s",
            error,
        )

    return jobs


# ============================================================
# ITPro.lk
# ============================================================

def fetch_itpro() -> List[Dict]:
    jobs = []

    logger.info("Fetching ITPro.lk...")

    urls = [
        "https://itpro.lk/jobs/",
        "https://itpro.lk/",
    ]

    for page_url in urls:
        response = request_page(page_url)

        if response is None:
            continue

        try:
            soup = BeautifulSoup(
                response.text,
                "html.parser",
            )

            links = soup.find_all("a", href=True)

            for link in links:
                title = link.get_text(" ", strip=True)

                if not title:
                    continue

                href = link.get("href", "")

                if href.startswith("/"):
                    href = "https://itpro.lk" + href

                if "itpro.lk" not in href:
                    continue

                combined = title.lower()

                if not any(
                    word in combined
                    for searches in ROLE_SEARCHES.values()
                    for word in searches
                ):
                    continue

                add_job(
                    jobs=jobs,
                    source="ITPro.lk",
                    title=title,
                    company="Unknown",
                    location="Sri Lanka",
                    url=href,
                    description=title,
                )

        except Exception as error:
            logger.warning(
                "ITPro parsing failed: %s",
                error,
            )

    jobs = deduplicate_jobs(jobs)

    logger.info(
        "ITPro.lk: %s jobs fetched",
        len(jobs),
    )

    return jobs


# ============================================================
# TOPJOBS
# ============================================================

def fetch_topjobs() -> List[Dict]:
    jobs = []

    logger.info("Fetching TopJobs...")

    search_urls = []

    for searches in ROLE_SEARCHES.values():
        for query in searches:
            search_urls.append(
                "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp"
            )

    # Main public page
    response = request_page(
        "https://www.topjobs.lk/"
    )

    if response is None:
        return jobs

    try:
        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        links = soup.find_all("a", href=True)

        for link in links:
            title = link.get_text(
                " ",
                strip=True,
            )

            href = link.get("href", "")

            if not title or not href:
                continue

            title_lower = title.lower()

            if not any(
                keyword in title_lower
                for searches in ROLE_SEARCHES.values()
                for keyword in searches
            ):
                continue

            if href.startswith("/"):
                href = "https://www.topjobs.lk" + href

            add_job(
                jobs=jobs,
                source="TopJobs",
                title=title,
                company="Unknown",
                location="Sri Lanka",
                url=href,
                description=title,
            )

    except Exception as error:
        logger.warning(
            "TopJobs parsing failed: %s",
            error,
        )

    jobs = deduplicate_jobs(jobs)

    logger.info(
        "TopJobs: %s jobs fetched",
        len(jobs),
    )

    return jobs


# ============================================================
# INTERNSJOBS.LK
# ============================================================

def fetch_internjobs() -> List[Dict]:
    jobs = []

    logger.info("Fetching InternJobs.lk...")

    response = request_page(
        "https://internjobs.lk/"
    )

    if response is None:
        return jobs

    try:
        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        links = soup.find_all("a", href=True)

        for link in links:
            title = link.get_text(
                " ",
                strip=True,
            )

            href = link.get("href", "")

            if not title or not href:
                continue

            if href.startswith("/"):
                href = "https://internjobs.lk" + href

            combined = title.lower()

            if not any(
                keyword in combined
                for searches in ROLE_SEARCHES.values()
                for keyword in searches
            ):
                continue

            add_job(
                jobs=jobs,
                source="InternJobs.lk",
                title=title,
                company="Unknown",
                location="Sri Lanka",
                url=href,
                description=title,
            )

    except Exception as error:
        logger.warning(
            "InternJobs parsing failed: %s",
            error,
        )

    jobs = deduplicate_jobs(jobs)

    logger.info(
        "InternJobs.lk: %s jobs fetched",
        len(jobs),
    )

    return jobs


# ============================================================
# WELLFOUND
# ============================================================

def fetch_wellfound() -> List[Dict]:
    jobs = []

    logger.info("Fetching Wellfound role pages...")

    role_pages = [
        (
            "Software Engineering",
            "https://wellfound.com/role/software-engineer"
        ),
        (
            "Data Science",
            "https://wellfound.com/role/data-scientist"
        ),
        (
            "AI/ML",
            "https://wellfound.com/role/machine-learning-engineer"
        ),
        (
            "Data Engineering",
            "https://wellfound.com/role/data-engineer"
        ),
    ]

    for category, page_url in role_pages:
        response = request_page(page_url)

        if response is None:
            continue

        try:
            soup = BeautifulSoup(
                response.text,
                "html.parser",
            )

            links = soup.find_all(
                "a",
                href=True,
            )

            for link in links:
                title = link.get_text(
                    " ",
                    strip=True,
                )

                href = link.get("href", "")

                if not title or not href:
                    continue

                if "/jobs/" not in href:
                    continue

                if href.startswith("/"):
                    href = "https://wellfound.com" + href

                combined = title.lower()

                if not any(
                    keyword in combined
                    for keyword in ROLE_SEARCHES.get(
                        category,
                        []
                    )
                ):
                    continue

                add_job(
                    jobs=jobs,
                    source="Wellfound",
                    title=title,
                    company="Unknown",
                    location="Remote",
                    url=href,
                    description=title,
                    category=category,
                )

        except Exception as error:
            logger.warning(
                "Wellfound parsing failed for %s: %s",
                category,
                error,
            )

    jobs = deduplicate_jobs(jobs)

    logger.info(
        "Wellfound: %s jobs fetched",
        len(jobs),
    )

    return jobs


# ============================================================
# GOOGLE NEWS RSS SEARCH
# Used for XpressJobs + LinkedIn discovery
# ============================================================

def fetch_google_news_search(
    query: str,
    source: str,
    site_filter: str,
) -> List[Dict]:

    jobs = []

    encoded_query = quote(
        f'{query} site:{site_filter}'
    )

    rss_url = (
        "https://news.google.com/rss/search?"
        f"q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    )

    response = request_page(rss_url)

    if response is None:
        return jobs

    try:
        feed = feedparser.parse(
            response.content
        )

        for entry in feed.entries:

            title = clean_text(
                entry.get("title", "")
            )

            description = clean_text(
                entry.get("description", "")
            )

            link = entry.get("link", "")

            if not title or not link:
                continue

            combined = (
                f"{title} "
                f"{description}"
            ).lower()

            # Make sure the result is actually relevant
            # to the search we requested.
            role_words = query.lower().split()

            if not any(
                word in combined
                for word in role_words
                if len(word) > 2
            ):
                continue

            date = entry.get(
                "published",
                None,
            )

            add_job(
                jobs=jobs,
                source=source,
                title=title,
                company=source,
                location="Sri Lanka / Remote",
                url=link,
                description=description,
                date=date,
            )

    except Exception as error:
        logger.warning(
            "Google News RSS parsing failed: %s",
            error,
        )

    return jobs


def fetch_xpressjobs() -> List[Dict]:
    jobs = []

    logger.info(
        "Fetching XpressJobs using direct + discovery methods..."
    )

    # Try direct page first.
    response = request_page(
        "https://xpress.jobs/"
    )

    if response is not None:
        try:
            soup = BeautifulSoup(
                response.text,
                "html.parser",
            )

            links = soup.find_all(
                "a",
                href=True,
            )

            for link in links:
                title = link.get_text(
                    " ",
                    strip=True,
                )

                href = link.get(
                    "href",
                    "",
                )

                if not title or not href:
                    continue

                combined = title.lower()

                if not any(
                    keyword in combined
                    for searches in ROLE_SEARCHES.values()
                    for keyword in searches
                ):
                    continue

                if href.startswith("/"):
                    href = "https://xpress.jobs" + href

                add_job(
                    jobs=jobs,
                    source="XpressJobs",
                    title=title,
                    company="Unknown",
                    location="Sri Lanka",
                    url=href,
                    description=title,
                )

        except Exception as error:
            logger.warning(
                "XpressJobs direct parsing failed: %s",
                error,
            )

    # Google News discovery for EVERY role category.
    for category, searches in ROLE_SEARCHES.items():

        for query in searches:

            logger.info(
                "XpressJobs search: %s",
                query,
            )

            results = fetch_google_news_search(
                query=query,
                source="XpressJobs",
                site_filter="xpress.jobs",
            )

            for job in results:
                job["category"] = category

            jobs.extend(results)

            time.sleep(0.5)

    jobs = deduplicate_jobs(jobs)

    logger.info(
        "XpressJobs: %s jobs fetched",
        len(jobs),
    )

    return jobs

# ============================================================
# DEDUPLICATION
# ============================================================

def deduplicate_jobs(
    jobs: List[Dict],
) -> List[Dict]:

    unique = {}
    seen_urls = set()

    for job in jobs:

        url = job.get("url", "").strip()

        title = job.get(
            "title",
            "",
        ).strip().lower()

        company = job.get(
            "company",
            "",
        ).strip().lower()

        if not title:
            continue

        # Prefer URL when available.
        if url:
            key = url.lower()
        else:
            key = (
                f"{title}|{company}"
            )

        if key in seen_urls:
            continue

        seen_urls.add(key)
        unique[key] = job

    return list(unique.values())


# ============================================================
# MAIN FETCH FUNCTION
# ============================================================

def fetch_all_jobs() -> List[Dict]:

    logger.info(
        "========== Fetching ALL internship sources =========="
    )

    all_jobs = []

    # --------------------------------------------------------
    # Fetch each source
    # --------------------------------------------------------

    fetchers = [
    ("RemoteOK", fetch_remoteok),
    ("ITPro.lk", fetch_itpro),
    ("TopJobs", fetch_topjobs),
    ("InternJobs.lk", fetch_internjobs),
    ("Wellfound", fetch_wellfound),
    ("XpressJobs", fetch_xpressjobs),
    ]

    for source_name, fetcher in fetchers:

        try:
            source_jobs = fetcher()

            logger.info(
                "%s returned %s jobs",
                source_name,
                len(source_jobs),
            )

            all_jobs.extend(source_jobs)

        except Exception as error:

            logger.exception(
                "%s scraper failed: %s",
                source_name,
                error,
            )

    # --------------------------------------------------------
    # Remove duplicates
    # --------------------------------------------------------

    all_jobs = deduplicate_jobs(
        all_jobs
    )

    logger.info(
        "Total unique jobs fetched: %s",
        len(all_jobs),
    )

    # --------------------------------------------------------
    # Print category discovery statistics
    # --------------------------------------------------------

    logger.info(
        "========== Role Discovery Summary =========="
    )

    for category in ROLE_SEARCHES:

        count = 0

        for job in all_jobs:

            text = (
                f"{job.get('title', '')} "
                f"{job.get('description', '')} "
                f"{' '.join(job.get('tags', []))}"
            ).lower()

            if any(
                keyword.lower() in text
                for keyword in ROLE_SEARCHES[category]
            ):
                count += 1

        logger.info(
            "%s: %s possible matches",
            category,
            count,
        )

    logger.info(
        "============================================"
    )

    return all_jobs

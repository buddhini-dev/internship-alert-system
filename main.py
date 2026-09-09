import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import config
from database import (
    ensure_database,
    load_seen_jobs,
    mark_seen,
    save_seen_jobs,
)
from notifier import send_email
from scraper import fetch_all_jobs


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


logger = logging.getLogger(__name__)


ROLE_PRIORITY = {
    "Data Science": 1,
    "Software Engineering": 2,
    "AI/ML": 3,
    "Data Engineering": 4,
}


def normalize_text(value: str) -> str:
    return (value or "").lower().strip()


def determine_category(job: Dict) -> Optional[str]:

    title = normalize_text(
        job.get("title", "")
    )

    description = normalize_text(
        job.get("description", "")
    )

    tags = job.get("tags", [])

    if isinstance(tags, list):
        tag_text = " ".join(
            str(tag).lower()
            for tag in tags
        )
    else:
        tag_text = str(tags).lower()

    combined = (
        f"{title} "
        f"{description} "
        f"{tag_text}"
    )

    # Exclude analyst roles first.
    for excluded in config.EXCLUDED_KEYWORDS:

        if excluded in title:
            return None

    # Check preferred categories.
    for category, keywords in config.ROLE_KEYWORDS.items():

        for keyword in keywords:

            if keyword.lower() in combined:

                # Do not classify generic analyst positions.
                if (
                    "analyst" in title
                    and "data scientist" not in title
                ):
                    return None

                return category

    return None


def is_internship(job: Dict) -> bool:

    title = normalize_text(
        job.get("title", "")
    )

    description = normalize_text(
        job.get("description", "")
    )

    combined = (
        f"{title} {description}"
    )

    internship_keywords = [
        "intern",
        "internship",
        "trainee",
        "student",
        "graduate",
        "co-op",
        "co op",
        "apprentice",
    ]

    return any(
        keyword in combined
        for keyword in internship_keywords
    )


def parse_job_date(job: Dict):

    date_value = job.get("date")

    if not date_value:
        return None

    try:

        if isinstance(date_value, str):

            date_value = date_value.replace(
                "Z",
                "+00:00"
            )

            return datetime.fromisoformat(
                date_value
            )

    except ValueError:
        return None

    return None


def is_recent(job: Dict) -> bool:

    job_date = parse_job_date(job)

    if job_date is None:
        # If source does not provide a usable date,
        # keep the job rather than silently discarding it.
        return True

    now = datetime.now(timezone.utc)

    if job_date.tzinfo is None:
        job_date = job_date.replace(
            tzinfo=timezone.utc
        )

    age_days = (
        now - job_date
    ).total_seconds() / 86400

    return age_days <= config.MAX_JOB_AGE_DAYS


def process_jobs(
    jobs: List[Dict],
    seen_jobs
) -> List[Dict]:

    matching_jobs = []

    for job in jobs:

        job_id = job.get("id")

        if not job_id:
            continue

        if job_id in seen_jobs:
            continue

        category = determine_category(job)

        if category is None:
            continue

        if not is_internship(job):
            continue

        if not is_recent(job):
            continue

        job["category"] = category

        matching_jobs.append(job)

    # Highest priority first.
    matching_jobs.sort(
        key=lambda job: (
            ROLE_PRIORITY.get(
                job.get("category"),
                99
            ),
            job.get("title", "").lower()
        )
    )

    return matching_jobs[
        :config.MAX_JOBS_PER_EMAIL
    ]


def main():

    logger.info(
        "========== Internship Alert System =========="
    )

    config.validate()

    ensure_database()

    seen_jobs = load_seen_jobs()

    logger.info(
        "Previously seen jobs: %s",
        len(seen_jobs)
    )

    jobs = fetch_all_jobs()

    logger.info(
        "Total jobs fetched: %s",
        len(jobs)
    )

    new_jobs = process_jobs(
        jobs,
        seen_jobs
    )

    logger.info(
        "New matching internships: %s",
        len(new_jobs)
    )

    if new_jobs:

        for job in new_jobs:

            logger.info(
                "MATCH | %s | %s | %s",
                job.get("category"),
                job.get("title"),
                job.get("company"),
            )

            mark_seen(
                job["id"],
                seen_jobs
            )

        send_email(new_jobs)

    else:

        logger.info(
            "No new matching internships found."
        )

    save_seen_jobs(seen_jobs)

    logger.info(
        "Database/state saved."
    )

    logger.info(
        "========== Finished =========="
    )


if __name__ == "__main__":
    main()

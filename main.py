import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config import config
from database import (
    ensure_database,
    load_seen_jobs,
    mark_seen,
    save_seen_jobs,
)
from notifier import (
    send_email,
    send_test_email,
)
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


def normalize_text(
    value: str
) -> str:

    return (
        value or ""
    ).lower().strip()


def determine_category(
    job: Dict
) -> Optional[str]:

    title = normalize_text(
        job.get(
            "title",
            ""
        )
    )

    description = normalize_text(
        job.get(
            "description",
            ""
        )
    )

    tags = job.get(
        "tags",
        []
    )

    if isinstance(tags, list):

        tag_text = " ".join(
            str(tag).lower()
            for tag in tags
        )

    else:

        tag_text = str(
            tags
        ).lower()

    combined = (
        f"{title} "
        f"{description} "
        f"{tag_text}"
    )

    # Explicit exclusions
    for excluded in config.EXCLUDED_KEYWORDS:

        if excluded in title:

            return None

    # Category matching
    for category, keywords in (
        config.ROLE_KEYWORDS.items()
    ):

        for keyword in keywords:

            if keyword.lower() in combined:

                # Don't accidentally include
                # analyst roles.
                if (
                    "analyst" in title
                    and "data scientist"
                    not in title
                ):
                    return None

                return category

    return None


def is_internship(
    job: Dict
) -> bool:

    title = normalize_text(
        job.get(
            "title",
            ""
        )
    )

    description = normalize_text(
        job.get(
            "description",
            ""
        )
    )

    combined = (
        f"{title} "
        f"{description}"
    )

    strong_internship_keywords = [
        "intern",
        "internship",
        "trainee",
        "co-op",
        "co op",
        "apprentice",
    ]

    student_keywords = [
        "student",
        "undergraduate",
        "undergrad",
        "graduate",
        "fresh graduate",
        "recent graduate",
    ]

    entry_level_keywords = [
        "entry level",
        "entry-level",
    ]

    if any(
        keyword in combined
        for keyword in strong_internship_keywords
    ):
        return True

    if any(
        keyword in combined
        for keyword in student_keywords
    ):
        return True

    # Entry-level is accepted only when
    # the job is clearly one of our target
    # technology roles.
    if any(
        keyword in combined
        for keyword in entry_level_keywords
    ):

        target_role_words = [
            "software",
            "developer",
            "data scientist",
            "data science",
            "machine learning",
            "ml engineer",
            "ai engineer",
            "artificial intelligence",
            "data engineer",
        ]

        return any(
            word in combined
            for word in target_role_words
        )

    return False


def parse_job_date(
    job: Dict
):

    date_value = job.get(
        "date"
    )

    if not date_value:
        return None

    if isinstance(
        date_value,
        datetime
    ):
        return date_value

    try:

        date_string = str(
            date_value
        )

        date_string = (
            date_string
            .replace(
                "Z",
                "+00:00"
            )
        )

        return datetime.fromisoformat(
            date_string
        )

    except ValueError:

        return None


def is_recent(
    job: Dict
) -> bool:

    job_date = parse_job_date(
        job
    )

    # Some sources don't provide
    # a machine-readable date.
    # Don't discard those jobs.
    if job_date is None:
        return True

    now = datetime.now(
        timezone.utc
    )

    if job_date.tzinfo is None:

        job_date = (
            job_date.replace(
                tzinfo=timezone.utc
            )
        )

    age_days = (
        now - job_date
    ).total_seconds() / 86400

    return (
        age_days
        <= config.MAX_JOB_AGE_DAYS
    )


def process_jobs(
    jobs: List[Dict],
    seen_jobs
) -> List[Dict]:

    matching_jobs = []

    for job in jobs:

        job_id = job.get(
            "id"
        )

        if not job_id:
            continue

        if job_id in seen_jobs:
            continue

        category = determine_category(
            job
        )

        if category is None:
            continue

        if not is_internship(
            job
        ):
            continue

        if not is_recent(
            job
        ):
            continue

        job["category"] = category

        matching_jobs.append(
            job
        )

    matching_jobs.sort(
        key=lambda job: (
            ROLE_PRIORITY.get(
                job.get(
                    "category"
                ),
                99
            ),
            job.get(
                "title",
                ""
            ).lower()
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

    # ------------------------------------------------
    # TEST EMAIL MODE
    # ------------------------------------------------

    test_email = (
        os.getenv(
            "TEST_EMAIL",
            "false"
        ).lower()
        == "true"
    )

    if test_email:

        logger.info(
            "TEST_EMAIL mode enabled."
        )

        send_test_email()

        logger.info(
            "Test email completed."
        )

        return

    # ------------------------------------------------
    # NORMAL MODE
    # ------------------------------------------------

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
                "MATCH | %s | %s | %s | %s",
                job.get(
                    "category"
                ),
                job.get(
                    "title"
                ),
                job.get(
                    "company"
                ),
                job.get(
                    "source"
                ),
            )

        # IMPORTANT:
        # Send the email FIRST.
        #
        # Only if email succeeds do we
        # mark jobs as seen.
        send_email(
            new_jobs
        )

        for job in new_jobs:

            mark_seen(
                job["id"],
                seen_jobs
            )

        logger.info(
            "Jobs marked as seen after "
            "successful email delivery."
        )

    else:

        logger.info(
            "No new matching internships found."
        )

    save_seen_jobs(
        seen_jobs
    )

    logger.info(
        "Database/state saved."
    )

    logger.info(
        "========== Finished =========="
    )


if __name__ == "__main__":
    main()

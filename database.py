import json
import os
from typing import Set


DATA_DIR = "data"
SEEN_JOBS_FILE = os.path.join(DATA_DIR, "seen_jobs.json")


def ensure_database():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as file:
            json.dump([], file, indent=2)


def load_seen_jobs() -> Set[str]:
    ensure_database()

    try:
        with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return set(data)

    except (json.JSONDecodeError, OSError):
        return set()


def save_seen_jobs(seen_jobs: Set[str]):
    ensure_database()

    with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as file:
        json.dump(
            sorted(seen_jobs),
            file,
            indent=2,
            ensure_ascii=False
        )


def is_seen(job_id: str, seen_jobs: Set[str]) -> bool:
    return job_id in seen_jobs


def mark_seen(job_id: str, seen_jobs: Set[str]):
    seen_jobs.add(job_id)

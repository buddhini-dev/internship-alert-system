import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Email
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT")

    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

    # Job filtering
    MAX_JOB_AGE_DAYS = int(os.getenv("MAX_JOB_AGE_DAYS", "14"))
    MAX_JOBS_PER_EMAIL = int(os.getenv("MAX_JOBS_PER_EMAIL", "20"))

    # Scraper
    REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "2"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

    # Your preferred roles
    ROLE_KEYWORDS = {
        "Data Science": [
            "data scientist",
            "data science",
            "data science intern",
            "data scientist intern",
        ],
        "Software Engineering": [
            "software engineer",
            "software engineering",
            "software developer",
            "software development",
            "software engineer intern",
            "software developer intern",
        ],
        "AI/ML": [
            "machine learning",
            "machine learning engineer",
            "ml engineer",
            "artificial intelligence",
            "ai engineer",
            "ai/ml",
            "deep learning",
            "machine learning intern",
            "ai intern",
            "ml intern",
        ],
        "Data Engineering": [
            "data engineer",
            "data engineering",
            "data engineer intern",
        ],
    }

    # Roles explicitly excluded
    EXCLUDED_KEYWORDS = [
        "data analyst",
        "business analyst",
        "financial analyst",
        "marketing analyst",
    ]

    @classmethod
    def validate(cls):
        missing = []

        if not cls.EMAIL_USER:
            missing.append("EMAIL_USER")

        if not cls.EMAIL_PASSWORD:
            missing.append("EMAIL_PASSWORD")

        if not cls.EMAIL_RECIPIENT:
            missing.append("EMAIL_RECIPIENT")

        if missing:
            raise ValueError(
                "Missing environment variables: "
                + ", ".join(missing)
            )


config = Config()

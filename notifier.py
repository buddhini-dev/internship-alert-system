import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

from config import config


logger = logging.getLogger(__name__)


def build_email_html(jobs: List[Dict]) -> str:

    if not jobs:
        return """
        <html>
        <body>
            <h2>Internship Alert System</h2>
            <p>No new matching internships were found.</p>
        </body>
        </html>
        """

    job_sections = []

    for job in jobs:

        title = html.escape(job.get("title", "Unknown"))
        company = html.escape(job.get("company", "Unknown"))
        location = html.escape(
            job.get("location", "Remote")
        )
        source = html.escape(
            job.get("source", "Unknown")
        )
        url = html.escape(
            job.get("url", "#"),
            quote=True
        )

        category = html.escape(
            job.get("category", "Other")
        )

        job_sections.append(
            f"""
            <div style="
                border:1px solid #ddd;
                border-radius:8px;
                padding:15px;
                margin-bottom:15px;
            ">

                <h3>{title}</h3>

                <p>
                    <strong>Company:</strong>
                    {company}
                </p>

                <p>
                    <strong>Category:</strong>
                    {category}
                </p>

                <p>
                    <strong>Location:</strong>
                    {location}
                </p>

                <p>
                    <strong>Source:</strong>
                    {source}
                </p>

                <p>
                    <a href="{url}">
                        Apply / View Job
                    </a>
                </p>

            </div>
            """
        )

    return f"""
    <html>
    <body>

        <h2>🚨 New Internship Alerts</h2>

        <p>
            Found <strong>{len(jobs)}</strong>
            new matching job(s).
        </p>

        {''.join(job_sections)}

        <hr>

        <p>
            Internship Alert System
        </p>

    </body>
    </html>
    """


def send_email(jobs: List[Dict]):

    if not jobs:
        logger.info("No email needed because there are no new jobs.")
        return

    subject = (
        f"🚨 {len(jobs)} New Internship "
        f"Opportunity"
        f"{'ies' if len(jobs) != 1 else 'y'}"
    )

    html_body = build_email_html(jobs)

    message = MIMEMultipart("alternative")

    message["From"] = config.EMAIL_USER
    message["To"] = config.EMAIL_RECIPIENT
    message["Subject"] = subject

    message.attach(
        MIMEText(html_body, "html")
    )

    logger.info(
        "Sending email to %s",
        config.EMAIL_RECIPIENT
    )

    with smtplib.SMTP(
        config.SMTP_SERVER,
        config.SMTP_PORT
    ) as server:

        server.starttls()

        server.login(
            config.EMAIL_USER,
            config.EMAIL_PASSWORD
        )

        server.sendmail(
            config.EMAIL_USER,
            config.EMAIL_RECIPIENT,
            message.as_string()
        )

    logger.info("Email sent successfully.")

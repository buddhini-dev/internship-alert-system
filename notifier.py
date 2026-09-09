import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List

from config import config


logger = logging.getLogger(__name__)


def build_email_html(
    jobs: List[Dict]
) -> str:

    job_sections = []

    for job in jobs:

        title = html.escape(
            job.get(
                "title",
                "Unknown"
            )
        )

        company = html.escape(
            job.get(
                "company",
                "Unknown"
            )
        )

        location = html.escape(
            job.get(
                "location",
                "Sri Lanka"
            )
        )

        source = html.escape(
            job.get(
                "source",
                "Unknown"
            )
        )

        category = html.escape(
            job.get(
                "category",
                "Other"
            )
        )

        url = html.escape(
            job.get(
                "url",
                "#"
            ),
            quote=True
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
            Found
            <strong>{len(jobs)}</strong>
            new matching internship(s).
        </p>

        {''.join(job_sections)}

        <hr>

        <p>
            Sources:
            RemoteOK, ITPro.lk, TopJobs
        </p>

        <p>
            Internship Alert System
        </p>

    </body>
    </html>
    """


def send_email(
    jobs: List[Dict]
):

    if not jobs:

        logger.info(
            "No jobs to email."
        )

        return

    if len(jobs) == 1:

        subject = (
            "🚨 1 New Internship Opportunity"
        )

    else:

        subject = (
            f"🚨 {len(jobs)} New "
            "Internship Opportunities"
        )

    html_body = build_email_html(
        jobs
    )

    message = MIMEMultipart(
        "alternative"
    )

    message["From"] = config.EMAIL_USER
    message["To"] = config.EMAIL_RECIPIENT
    message["Subject"] = subject

    message.attach(
        MIMEText(
            html_body,
            "html"
        )
    )

    logger.info(
        "Connecting to Gmail SMTP..."
    )

    with smtplib.SMTP(
        config.SMTP_SERVER,
        config.SMTP_PORT,
        timeout=30
    ) as server:

        server.ehlo()

        server.starttls()

        server.ehlo()

        logger.info(
            "Logging into Gmail..."
        )

        server.login(
            config.EMAIL_USER,
            config.EMAIL_PASSWORD
        )

        logger.info(
            "Sending email to %s",
            config.EMAIL_RECIPIENT
        )

        server.sendmail(
            config.EMAIL_USER,
            config.EMAIL_RECIPIENT,
            message.as_string()
        )

    logger.info(
        "Email sent successfully."
    )


def send_test_email():

    subject = (
        "🧪 Internship Alert System "
        "— Test Email"
    )

    html_body = """
    <html>
    <body>

        <h2>🧪 Internship Alert System</h2>

        <p>
            Your test email was sent successfully.
        </p>

        <p>
            Gmail SMTP is working correctly.
        </p>

        <hr>

        <p>
            The system is ready to send
            internship alerts.
        </p>

    </body>
    </html>
    """

    message = MIMEMultipart(
        "alternative"
    )

    message["From"] = config.EMAIL_USER
    message["To"] = config.EMAIL_RECIPIENT
    message["Subject"] = subject

    message.attach(
        MIMEText(
            html_body,
            "html"
        )
    )

    logger.info(
        "Sending TEST email to %s",
        config.EMAIL_RECIPIENT
    )

    with smtplib.SMTP(
        config.SMTP_SERVER,
        config.SMTP_PORT,
        timeout=30
    ) as server:

        server.ehlo()

        server.starttls()

        server.ehlo()

        logger.info(
            "Logging into Gmail..."
        )

        server.login(
            config.EMAIL_USER,
            config.EMAIL_PASSWORD
        )

        server.sendmail(
            config.EMAIL_USER,
            config.EMAIL_RECIPIENT,
            message.as_string()
        )

    logger.info(
        "TEST email sent successfully."
    )

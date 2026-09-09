# Internship Alert System

An automated internship monitoring system built with Python and GitHub Actions.

## Features

- Automatically checks job listings
- Filters internship and student opportunities
- Prioritizes:
  1. Data Science
  2. Software Engineering
  3. AI/ML
  4. Data Engineering
- Excludes Data Analyst roles
- Sends email alerts through Gmail
- Prevents duplicate alerts
- Runs automatically every 6 hours
- Uses GitHub Actions
- No backend server required

## Tech Stack

- Python
- Requests
- Gmail SMTP
- GitHub Actions
- JSON state storage

## Job Source

RemoteOK public job feed.

## Setup

Configure these GitHub Secrets:

- EMAIL_USER
- EMAIL_PASSWORD
- EMAIL_RECIPIENT

Then run the workflow manually from GitHub Actions.

## Security

Never commit:

- Gmail passwords
- Gmail App Passwords
- `.env` files
- API keys
- Other credentials

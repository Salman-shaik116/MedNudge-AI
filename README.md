

---

# Mednudge AI (Django)

Mednudge AI is a Django web app for:

- Uploading medical reports (TXT/DOCX/PDF/Images) and generating an AI-assisted summary/insights.
- An “AI Doctor” chat that provides general health guidance and triage suggestions (not a diagnosis).
- User dashboard with saved reports, reminders, and a public weekly progress tracker.
- Admin-only doctor registration + appointment booking flow (with meeting link).

This repository contains a deploy-ready configuration for Render (see build script and render config).

## Contents

- Overview
- Project architecture
- Supported report formats
- Local setup (Windows)
- Environment variables
- Common routes
- Deploy on Render
- Troubleshooting
- Disclaimer

## Overview

The Django project lives in [docusai_project](docusai_project). The main Django app is [website](website), and the report/LLM pipeline lives in [mediscanner](mediscanner).

## Project architecture

High-level modules:

- Django project config: [docusai_project/settings.py](docusai_project/settings.py)
- URL routing: [docusai_project/urls.py](docusai_project/urls.py) and [website/urls.py](website/urls.py)
- Web app (templates/static/views/models): [website](website)
- Report extraction + OCR + LLM calls: [mediscanner](mediscanner)

Request flow (report analysis):

1. User uploads a file on the upload page.
2. [website/views.py](website/views.py) calls `mediscanner.analyzer.analyze_medical_report`.
3. [mediscanner/file_extractor.py](mediscanner/file_extractor.py) extracts text (PDF/DOCX/TXT) or runs OCR for images.
4. [mediscanner/agent.py](mediscanner/agent.py) sends a prompt to an LLM via [mediscanner/llm.py](mediscanner/llm.py).
5. The analysis is saved as a `MedicalReport` record and shown to the user.

## Supported report formats

Text extraction supports:

- `.txt`
- `.docx`
- `.pdf`
- images: `.png`, `.jpg`, `.jpeg` (OCR via Tesseract)

See [mediscanner/file_extractor.py](mediscanner/file_extractor.py) for the exact behavior and error messages.

## Local setup (Windows)

Prerequisites:

- Python 3.11.x (Render uses 3.11.9 via [runtime.txt](runtime.txt))
- (Optional, for image OCR) Tesseract OCR engine installed on your machine

### 1) Create a virtual environment

From the project folder:

```powershell
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

### 3) Configure environment variables

For local development, you can create a `.env` file (loaded by [docusai_project/settings.py](docusai_project/settings.py)). The repo includes an example you can copy:

- Copy [.env.example](.env.example) to `.env` and fill in values

Minimum recommended values:

```env
# Django
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Timezone (recommended)
# Default is Asia/Kolkata if not set.
TIME_ZONE=Asia/Kolkata

# Email (SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_sender_email@example.com
EMAIL_HOST_PASSWORD=your_smtp_password

# AI provider (pick one)
AI_PROVIDER=groq
GROQ_API_KEY=your_groq_key
# GROQ_MODEL=llama-3.1-8b-instant

# OR use xAI (Grok)
# AI_PROVIDER=xai
# XAI_API_KEY=your_xai_key
# XAI_MODEL=grok-beta
# XAI_BASE_URL=https://api.x.ai/v1

# OCR (only needed if Tesseract is not auto-detected on Windows)
# TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe

# Optional: Web Push notifications (only needed if you want push while the tab is closed)
# VAPID_PUBLIC_KEY=your_vapid_public_key
# VAPID_PRIVATE_KEY=your_vapid_private_key
# VAPID_CLAIMS_SUB=mailto:admin@example.com
```

Email notes:

- Some flows send email via SMTP in [website/views.py](website/views.py). Configure email via env vars: `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` (plus optional `EMAIL_HOST`/`EMAIL_PORT`/`EMAIL_USE_TLS`).

Database behavior:

- If `DATABASE_URL` is set, it is used (common for Render Postgres).
- Otherwise, if no `DB_*` variables are set, the app defaults to SQLite (`db.sqlite3`).
- If you set `DB_ENGINE`/`DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`, Django uses that database (MySQL defaults are supported via PyMySQL).

### 4) Run migrations and start the server

```powershell
python manage.py migrate
python manage.py runserver
```

App will be available at `http://127.0.0.1:8000/`.

### 5) (Optional) Create an admin user

```powershell
python manage.py createsuperuser
```

Admin is at `http://127.0.0.1:8000/admin/`.

## Environment variables

Key settings used by the code:

- `SECRET_KEY`: Django secret key
- `DEBUG`: `True`/`False` (string)
- `ALLOWED_HOSTS`: comma-separated hosts
- `DATABASE_URL`: full database URL (Render Postgres)
- `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`: optional explicit DB config
- `TIME_ZONE`: Django timezone (default: `Asia/Kolkata`)

Email (SMTP):

- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`: required for email sending
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`: optional SMTP connection settings

AI provider:

- `AI_PROVIDER`: `groq` or `xai` (alias `grok` is accepted)
- `GROQ_API_KEY` (required for Groq)
- `GROQ_MODEL` (optional)
- `XAI_API_KEY` or `GROK_API_KEY` (required for xAI)
- `XAI_MODEL` (optional)
- `XAI_BASE_URL` (optional)

OCR:

- `TESSERACT_CMD`: absolute path to `tesseract.exe` if Windows auto-detection doesn’t find it

Render superuser provisioning (used by [create_superuser.py](create_superuser.py) and [render.yaml](render.yaml)):

- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

Web Push notifications (optional):

- `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`: required if you want Web Push notifications
- `VAPID_CLAIMS_SUB`: `mailto:...` claim (optional; defaults to `mailto:admin@example.com`)

## Common routes

Routes are defined in [website/urls.py](website/urls.py). A few important ones:

- `/` Home
- `/upload/` Upload a report
- `/analyze/` POST endpoint to analyze an uploaded report
- `/reports/` Logged-in user’s saved reports
- `/ai-doctor/` AI Doctor UI
- `/api/ai-doctor/chat/` AI Doctor chat API (requires authentication)
- `/dashboard/` Logged-in dashboard
- `/progress/<tracker_id>/` Public weekly tracker page
- `/api/progress/<tracker_id>/update/` and `/api/progress/<tracker_id>/get/` tracker sync APIs
- `/forgot-password/` Password reset (email 6-digit code)
- `/reminder/` Reminder dashboard
- `/doctor-register/` Doctor registration (admin/staff only)
- `/doctors-list/` Doctors list + booking
- `/book-appointment/<doctor_id>/` Book an appointment
- `/appointment-meeting/<appointment_id>/` Appointment meeting page

## Authentication notes

- Sign-in is **email + password** (not username).
- Forgot password flow:
	1) Enter your email on `/forgot-password/`
	2) Receive a 6-digit code via SMTP
	3) Set a new password

Make sure your Django user records have an email address set (admin can manage users at `/admin/`).

## Notifications (local)

There are 2 notification modes:

1) In-page reminders (recommended for local dev)
	 - Open `/reminder/` and keep it open.
	 - “Due reminders” auto-refreshes and shows reminders when their time arrives.
	 - Click **Enable** to allow desktop pop-ups from your browser.

2) Web Push (optional)
	 - Requires `VAPID_PUBLIC_KEY` + `VAPID_PRIVATE_KEY`.
	 - Requires a secure context (HTTPS). `localhost` is allowed.
	 - Run the sender periodically (like a cron job):

		 ```bash
		 python manage.py send_due_push_notifications
		 ```

## Deploy on Render

Render deployment is configured via [render.yaml](render.yaml) and [build.sh](build.sh).

What Render does during build:

- Installs the Tesseract engine (Linux) if `apt-get` is available
- Installs Python dependencies
- Runs `collectstatic`
- Runs `migrate`
- Runs [create_superuser.py](create_superuser.py) to provision an admin user from env vars

Recommended Render environment variables:

- `DATABASE_URL` (Render “Internal Database URL”)
- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS=your-app-name.onrender.com`
- AI keys (`GROQ_API_KEY` or `XAI_API_KEY`) and optional model variables

Notes:

- On free tiers, instances may sleep; first request can be slow.
- Media uploads are stored on the instance filesystem by default (see `MEDIA_ROOT` in [docusai_project/settings.py](docusai_project/settings.py)). For production-grade persistence you typically move media storage to an external service.

See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for a step-by-step guide.

## Troubleshooting

### OCR fails for images

- Install Tesseract on Windows:
	- `winget install --id UB-Mannheim.TesseractOCR -e`
- Restart your terminal/server after installing.
- If Python still can’t find Tesseract, set `TESSERACT_CMD` in `.env`.
- Optional self-check:
	- `python manage.py shell -c "from mediscanner.ocr_check import run_check; run_check()"`

### AI Doctor / analysis says “misconfigured”

- Ensure the correct provider and key are set.
	- For Groq: `AI_PROVIDER=groq` + `GROQ_API_KEY`
	- For xAI: `AI_PROVIDER=xai` + `XAI_API_KEY` (or `GROK_API_KEY`)

### Static files missing on Render

- [build.sh](build.sh) runs `collectstatic` and WhiteNoise is enabled in [docusai_project/settings.py](docusai_project/settings.py).
- Confirm `DEBUG=False` and redeploy.

## Disclaimer

This project provides general health information and automated report summarization for educational/informational purposes only. It is not a medical device and does not replace professional medical advice, diagnosis, or treatment. If you think you may have a medical emergency, seek urgent care immediately.

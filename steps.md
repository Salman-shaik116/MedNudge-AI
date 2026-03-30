# Mednudge AI — Full Setup Guide (Windows/macOS/Linux)

This guide is meant to be “copy/paste runnable” and detailed enough to run the project on a fresh computer.

## 0) What this project is
- Backend: Django
- App: `website`
- AI module: `mediscanner`
- Uploads supported: `.pdf`, `.docx`, `.txt`, and images `.png/.jpg/.jpeg` (images use OCR)
- Python version: `python-3.11.9` (see `runtime.txt`)

## 1) Prerequisites (install these first)
### Required
- Git
- Python 3.11.x (recommended: 3.11.9)

Database:

- Default local setup uses **SQLite** automatically (no DB install needed)
- You can optionally use MySQL/Postgres by setting `DB_*` or `DATABASE_URL` in `.env`

### For image uploads (OCR)
- **Tesseract OCR engine** installed on your OS
  - Windows: install “Tesseract-OCR” and confirm `tesseract.exe` exists.
  - macOS: install via Homebrew.
  - Linux: install via apt/yum.

## 2) Get the code (clone)
Open a terminal and run:
```bash
git clone <YOUR_GITHUB_REPO_URL>
cd docusai_projectlastreview/docusai_projectfor_render_db01
```

## 3) Create a virtual environment (venv)
### Windows (PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## 4) Install Python dependencies
```bash
pip install -r requirements.txt
```

## 5) Create your local `.env` (important)
This repo includes a safe template: `.env.example`.

1) Copy it to `.env`
- Windows (PowerShell):
  ```powershell
  Copy-Item .env.example .env
  ```
- macOS/Linux:
  ```bash
  cp .env.example .env
  ```

2) Edit `.env` and set at least:
- `SECRET_KEY`
- (Optional) DB settings (`DB_*` or `DATABASE_URL`) — leave unset to use SQLite
- AI provider credentials (Groq or xAI)

If you want notifications and password reset to work locally, also set:

- `TIME_ZONE` (recommended, example: `Asia/Kolkata`)
- SMTP vars: `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (and optional host/port/TLS)

Notes:
- `.env` is ignored by git (so secrets won’t be committed).
- Avoid spaces around `=` in `.env` (use `KEY=value`).

## 6) Database setup (local)
### Option A (fastest): SQLite (default)
If you do **not** set any `DB_*` or `DATABASE_URL` variables, the project automatically uses SQLite.

You don’t need to install MySQL for this option.

### Option B: MySQL (recommended if you want to match the original setup)
1) Install MySQL Server and ensure it’s running.
2) Create the database:
```sql
CREATE DATABASE signup_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
3) Put your MySQL credentials in `.env`:
- `DB_ENGINE=django.db.backends.mysql`
- `DB_NAME=signup_db`
- `DB_USER=...`
- `DB_PASSWORD=...`
- `DB_HOST=127.0.0.1`
- `DB_PORT=3306`

### Option C: Use `DATABASE_URL`
If you prefer one connection string (Render/Postgres/etc), set `DATABASE_URL` in `.env` and leave `DB_*` unused.

## 7) Run migrations
From the folder that contains `manage.py`:
```bash
python manage.py migrate
```

If you see MySQL driver errors:
- Make sure MySQL server is running
- Confirm your `.env` DB values are correct

## 8) Create an admin user (superuser)
```bash
python manage.py createsuperuser
```

Notes:

- The sign-in page uses **email + password**.
- If you create users via the admin site, ensure the user has an email set.

## 9) Start the server
```bash
python manage.py runserver
```
Then open:
- http://127.0.0.1:8000/

Admin:
- http://127.0.0.1:8000/admin/

## 10) Forgot password (email 6-digit code)

1) Configure SMTP in `.env`:

```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_sender_email@example.com
EMAIL_HOST_PASSWORD=your_smtp_password
```

2) Run the server and open:

- http://127.0.0.1:8000/forgot-password/

3) Enter your email → receive a 6-digit code → set a new password.

## 11) Notifications (local)

There are 2 notification modes:

### Mode A: In-page + desktop pop-ups (recommended for local)

1) Create a reminder plan from a report (or add items on the Reminder page).
2) Open the reminder dashboard and keep it open:

- http://127.0.0.1:8000/reminder/

3) In “Due reminders”, click **Enable** and allow notifications.
4) Add an item for today with a time 1–2 minutes in the future to test quickly.

### Mode B: Web Push while tab is closed (optional)

Requires VAPID keys in `.env`:

```env
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...
VAPID_CLAIMS_SUB=mailto:admin@example.com
```

Then run the sender command (repeat periodically):

```bash
python manage.py send_due_push_notifications
```

## 10) OCR setup (for image uploads)
Image uploads (`.png/.jpg/.jpeg`) use `pytesseract` + the system **Tesseract** engine.

### Windows
1) Install Tesseract (common path):
- `C:\Program Files\Tesseract-OCR\tesseract.exe`

2) If OCR still fails, set this in `.env`:
```env
TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
```

### macOS
```bash
brew install tesseract
```

### Ubuntu/Debian Linux
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr
```

### Quick OCR verification
Run the project’s OCR check (from the `manage.py` folder):
```bash
python mediscanner/ocr_check.py
```
You should see output indicating Tesseract is detected.

## 11) AI Provider setup (Groq vs xAI/Grok)
The app can use either provider.

### Use Groq
In `.env`:
```env
AI_PROVIDER=groq
GROQ_API_KEY=your_key
GROQ_MODEL=llama-3.1-70b-versatile
```

### Use xAI (Grok)
In `.env`:
```env
AI_PROVIDER=xai
XAI_API_KEY=your_key
XAI_MODEL=grok-2-latest
XAI_BASE_URL=https://api.x.ai/v1
```

If the AI responses look “generic” or you get model errors, it’s almost always:
- Wrong provider selected (`AI_PROVIDER`)
- Wrong key for that provider
- Model name not available to your account

## 12) Common troubleshooting
### “Access denied for user …” (MySQL)
- Re-check `DB_USER`/`DB_PASSWORD` in `.env`
- Confirm MySQL is running and reachable on `DB_HOST:DB_PORT`

### “TesseractNotFoundError” / OCR fails
- Confirm Tesseract is installed
- Set `TESSERACT_CMD` in `.env` (Windows especially)

### “Module not found” errors
- Make sure the venv is activated
- Re-run `pip install -r requirements.txt`

## 13) Uploading the project to GitHub (safe steps)
From the `docusai_projectfor_render_db01` folder:

1) Check secrets are not staged
```bash
git status
```
Make sure `.env` is **not** listed.

2) Initialize git (if not already)
```bash
git init
```

3) Add and commit
```bash
git add .
git commit -m "Initial commit"
```

4) Create a GitHub repo (on GitHub website), then connect and push:
```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
git branch -M main
git push -u origin main
```

If GitHub blocks a push because it detected secrets, stop and rotate the exposed keys before retrying.

## 14) (Optional) Render deployment
There’s already a deployment guide here:
- `RENDER_DEPLOYMENT.md`

Use it if you want production hosting.

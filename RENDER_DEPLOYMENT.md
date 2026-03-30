# Render Deployment Guide for Mednudge AI

## Prerequisites
- GitHub account
- Render account (sign up at render.com)
- Git installed locally

## Step 1: Push to GitHub

```bash
# From the folder that contains manage.py
# Example:
# cd docusai_projectlastreview/docusai_projectfor_render_db01

git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```

## Step 2: Create PostgreSQL Database on Render

1. Go to https://dashboard.render.com
2. Click "New +" → "PostgreSQL"
3. Configure:
   - Name: `docusai-db`
   - Database: `docusai_db`
   - User: `docusai_user`
   - Region: Choose closest to you
   - Plan: Free
4. Click "Create Database"
5. **IMPORTANT**: Copy the "Internal Database URL" (starts with `postgresql://`)

## Step 3: Create Web Service on Render

1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - Name: `docusai` (or your preferred name)
   - Region: Same as database
   - Branch: `main`
   - Runtime: `Python 3`
   - Build Command: `./build.sh`
   - Start Command: `gunicorn docusai_project.wsgi:application`
   - Instance Type: Free

## Step 4: Set Environment Variables

In the web service "Environment" tab, add:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Paste Internal Database URL from Step 2 |
| `SECRET_KEY` | Generate new: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `your-app-name.onrender.com` |
| `PYTHON_VERSION` | `3.11.9` |
| `TIME_ZONE` | Optional (recommended), e.g. `Asia/Kolkata` |
| `AI_PROVIDER` | `groq` or `xai` (or `grok`) |
| `GROQ_API_KEY` | Your Groq API key (if using Groq) |
| `XAI_API_KEY` | Your xAI (Grok) API key (if using xAI) |
| `XAI_MODEL` | Optional, e.g. `grok-beta` (set if your account uses a different model name) |
| `XAI_BASE_URL` | Optional, default `https://api.x.ai/v1` |
| `EMAIL_HOST` | SMTP host (default: `smtp.gmail.com`) |
| `EMAIL_PORT` | SMTP port (default: `587`) |
| `EMAIL_USE_TLS` | `True` (recommended) |
| `EMAIL_HOST_USER` | Sender email address / SMTP username |
| `EMAIL_HOST_PASSWORD` | SMTP password (for Gmail: an App Password) |

Optional (Web Push notifications):

| Key | Value |
|-----|-------|
| `VAPID_PUBLIC_KEY` | Your VAPID public key |
| `VAPID_PRIVATE_KEY` | Your VAPID private key |
| `VAPID_CLAIMS_SUB` | Optional, e.g. `mailto:admin@example.com` |

Notes for Gmail:

- Use an App Password (not your normal password).
- The account used in `EMAIL_HOST_USER` will be the sender shown in emails.

## Step 5: Deploy

1. Click "Create Web Service"
2. Wait 5-10 minutes for deployment
3. Check logs for any errors

## Step 6: Create Superuser

This project can provision a superuser automatically during build using these env vars:

- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

If you prefer to create it manually (or create additional admins):

1. Go to your web service → "Shell" tab
2. Run: `python manage.py createsuperuser`
3. Follow prompts

## Step 7: Access Your Application

- App URL: `https://your-app-name.onrender.com`
- Admin: `https://your-app-name.onrender.com/admin`

## Notifications on Render

There are 2 modes:

1) In-page reminders
    - Users see due reminders on the Reminder dashboard (`/reminder/`) while the page is open.

2) Web Push notifications (optional)
    - Requires VAPID env vars (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`).
    - Requires running the sender management command periodically:

       ```bash
       python manage.py send_due_push_notifications
       ```

    - Render does not automatically run this on a schedule for you unless you set up a scheduler/job.
       Use a scheduler option available to you (Render cron job if enabled for your plan, or an external scheduler).

## Troubleshooting

### Build fails
- Check build logs in Render dashboard
- Verify all dependencies in requirements.txt

### Database connection error
- Verify DATABASE_URL is correct
- Check database is in same region as web service

### Static files not loading
- Ensure `python manage.py collectstatic` runs in build.sh
- Check STATIC_ROOT and STATIC_URL in settings.py

### App sleeps (Free tier)
- Free tier apps sleep after 15 min inactivity
- First request takes 30-60 seconds to wake up
- Consider upgrading for production use

## Important Notes

1. **Free Tier Limits**: 750 hours/month, app sleeps after inactivity
2. **Database**: PostgreSQL is used (Render's managed option)
3. **Media Files**: For production, use AWS S3 or Cloudinary
4. **Environment Variables**: Never commit .env file to GitHub
5. **Monitoring**: Check Render logs regularly

## Next Steps

- Set up custom domain (optional)
- Configure email backend for notifications
- Set up media file storage (S3/Cloudinary)
- Enable HTTPS (automatic on Render)
- Set up monitoring and alerts

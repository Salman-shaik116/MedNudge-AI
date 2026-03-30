import json
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.urls import reverse

from pywebpush import webpush, WebPushException

from website.models import InAppNotification, PushSubscription


class Command(BaseCommand):
    help = "Send a daily summary push notification to each user with notifications today."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default="",
            help="ISO date (YYYY-MM-DD) to summarize; defaults to today in server timezone.",
        )

    def handle(self, *args, **options):
        vapid_private = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
        vapid_sub = os.environ.get("VAPID_CLAIMS_SUB", "mailto:admin@example.com").strip()

        if not vapid_private:
            self.stderr.write("Missing VAPID_PRIVATE_KEY env var.")
            return

        date_str = (options.get("date") or "").strip()
        if date_str:
            try:
                summary_date = timezone.datetime.fromisoformat(date_str).date()
            except Exception:
                self.stderr.write("Invalid --date. Use YYYY-MM-DD")
                return
        else:
            summary_date = timezone.localdate()

        User = get_user_model()
        users = User.objects.all().only("id")

        sent = 0
        cleaned = 0

        for user in users:
            subs = list(PushSubscription.objects.filter(user_id=user.id))
            if not subs:
                continue

            start = timezone.make_aware(
                timezone.datetime.combine(summary_date, timezone.datetime.min.time()),
                timezone.get_current_timezone(),
            )
            end = start + timezone.timedelta(days=1)

            qs = InAppNotification.objects.filter(user_id=user.id, scheduled_for__gte=start, scheduled_for__lt=end)
            total = qs.count()
            if total == 0:
                continue

            taken = qs.filter(taken_at__isnull=False).count()
            now = timezone.now()
            missed_before = now - timezone.timedelta(minutes=15)
            missed = qs.filter(
                notification_type="medicine",
                scheduled_for__lt=missed_before,
                taken_at__isnull=True,
                snoozed_until__isnull=True,
            ).count()

            title = "Daily Summary"
            body = f"Today: {total} reminders • Taken: {taken} • Missed meds: {missed}"

            payload = json.dumps(
                {
                    "title": title,
                    "body": body,
                    "url": reverse("website:reminder"),
                }
            )

            ok = False
            for sub in subs:
                subscription_info = {
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                }
                try:
                    webpush(
                        subscription_info=subscription_info,
                        data=payload,
                        vapid_private_key=vapid_private,
                        vapid_claims={"sub": vapid_sub},
                    )
                    ok = True
                except WebPushException as exc:
                    status_code = getattr(getattr(exc, "response", None), "status_code", None)
                    if status_code in (404, 410):
                        sub.delete()
                        cleaned += 1
                except Exception:
                    continue

            if ok:
                sent += 1

        self.stdout.write(f"Sent {sent} summaries. Cleaned {cleaned} subscriptions.")

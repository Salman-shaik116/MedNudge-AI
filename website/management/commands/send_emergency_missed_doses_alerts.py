import json
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.urls import reverse

from pywebpush import webpush, WebPushException

from website.models import InAppNotification, PushSubscription


class Command(BaseCommand):
    help = "Send an emergency push alert if multiple medicine doses are missed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--consecutive-threshold",
            type=int,
            default=2,
            help="Number of consecutive missed medicine reminders required to alert.",
        )
        parser.add_argument(
            "--window-hours",
            type=int,
            default=24,
            help="Lookback window for missed doses.",
        )
        parser.add_argument(
            "--dedupe-hours",
            type=int,
            default=6,
            help="Don't send another emergency alert within this many hours.",
        )
        parser.add_argument(
            "--grace-minutes",
            type=int,
            default=15,
            help="How long after scheduled time before counting as missed (> grace).",
        )

    def handle(self, *args, **options):
        vapid_private = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
        vapid_sub = os.environ.get("VAPID_CLAIMS_SUB", "mailto:admin@example.com").strip()

        if not vapid_private:
            self.stderr.write("Missing VAPID_PRIVATE_KEY env var.")
            return

        consecutive_threshold = max(1, int(options.get("consecutive_threshold") or 2))
        window_hours = max(1, int(options.get("window_hours") or 24))
        dedupe_hours = max(1, int(options.get("dedupe_hours") or 6))
        grace_minutes = max(0, int(options.get("grace_minutes") or 15))

        now = timezone.now()
        window_start = now - timezone.timedelta(hours=window_hours)
        missed_before = now - timezone.timedelta(minutes=grace_minutes)
        dedupe_after = now - timezone.timedelta(hours=dedupe_hours)

        User = get_user_model()
        users = User.objects.all().only("id")

        sent = 0
        cleaned = 0

        for user in users:
            subs = list(PushSubscription.objects.filter(user_id=user.id))
            if not subs:
                continue

            # Dedupe: if an emergency was sent recently, skip.
            recent_emergency_exists = InAppNotification.objects.filter(
                user_id=user.id,
                notification_type="general",
                title__startswith="Emergency alert:",
                delivered_at__gte=dedupe_after,
            ).exists()
            if recent_emergency_exists:
                continue

            recent_meds = InAppNotification.objects.filter(
                user_id=user.id,
                notification_type="medicine",
                scheduled_for__gte=window_start,
                scheduled_for__lt=missed_before,
            ).order_by("-scheduled_for")

            # Count consecutive missed doses starting from the most recent eligible reminder.
            # Streak breaks as soon as we see a taken or snoozed dose.
            consecutive_missed = 0
            for n in recent_meds[:50]:
                is_missed = (n.taken_at is None) and (n.snoozed_until is None)
                if is_missed:
                    consecutive_missed += 1
                    if consecutive_missed >= consecutive_threshold:
                        break
                else:
                    break

            if consecutive_missed < consecutive_threshold:
                continue

            title = f"Emergency alert: missed {consecutive_missed} doses"
            body = "You have missed multiple medicine reminders. Please check your plan or contact a clinician if needed."

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
                # Record an emergency notification row so we can dedupe.
                InAppNotification.objects.create(
                    user_id=user.id,
                    report=None,
                    notification_type="general",
                    title=title,
                    body=body,
                    scheduled_for=now,
                    delivered_at=now,
                )
                sent += 1

        self.stdout.write(f"Sent {sent} emergency alerts. Cleaned {cleaned} subscriptions.")

import json
import os

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.urls import reverse

from pywebpush import webpush, WebPushException

from website.models import InAppNotification, PushSubscription


class Command(BaseCommand):
    help = "Send due InAppNotification rows via Web Push and mark them delivered."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Max notifications to send per run.",
        )

    def handle(self, *args, **options):
        vapid_public = os.environ.get("VAPID_PUBLIC_KEY", "").strip()
        vapid_private = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
        vapid_sub = os.environ.get("VAPID_CLAIMS_SUB", "mailto:admin@example.com").strip()

        if not vapid_public or not vapid_private:
            self.stderr.write(
                "Missing VAPID keys. Set VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY env vars."
            )
            return

        now = timezone.now()
        limit = max(1, int(options.get("limit") or 200))

        due = (
            InAppNotification.objects.filter(
                delivered_at__isnull=True,
                taken_at__isnull=True,
                snoozed_until__isnull=True,
                scheduled_for__lte=now,
            )
            .order_by("scheduled_for")
            .select_related("report")
            [:limit]
        )

        sent_count = 0
        cleaned_subs = 0

        for notif in due:
            subs = list(PushSubscription.objects.filter(user_id=notif.user_id))
            if not subs:
                continue

            url = reverse("website:reminder")
            if notif.report_id:
                url = f"{url}?report_id={notif.report_id}"

            payload = json.dumps(
                {
                    "title": notif.title,
                    "body": notif.body,
                    "url": url,
                    "type": notif.notification_type,
                    "notification_id": notif.id,
                }
            )

            at_least_one_success = False
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
                    at_least_one_success = True
                except WebPushException as exc:
                    status_code = getattr(getattr(exc, "response", None), "status_code", None)
                    if status_code in (404, 410):
                        sub.delete()
                        cleaned_subs += 1
                    continue
                except Exception:
                    continue

            if at_least_one_success:
                notif.delivered_at = timezone.now()
                notif.save(update_fields=["delivered_at"])
                sent_count += 1

        self.stdout.write(
            f"Sent {sent_count} notifications. Cleaned {cleaned_subs} subscriptions."
        )

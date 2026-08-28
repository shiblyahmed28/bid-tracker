import datetime

from celery import shared_task
from django.utils import timezone

from .services import notify_deadline


@shared_task
def send_deadline_alerts_task():
    """Daily Beat task at 08:00 Asia/Dhaka (§16) — every bid whose
    submission_date is exactly 7 days out gets exactly one alert, ever
    (deadline_alert_sent_at dedupes)."""
    from apps.bids.models import Bid

    target_date = timezone.localdate() + datetime.timedelta(days=7)
    bids = Bid.objects.filter(submission_date=target_date, deadline_alert_sent_at__isnull=True)
    sent = 0
    for bid in bids:
        notify_deadline(bid)
        bid.deadline_alert_sent_at = timezone.now()
        bid.save(update_fields=["deadline_alert_sent_at"])
        sent += 1
    return sent

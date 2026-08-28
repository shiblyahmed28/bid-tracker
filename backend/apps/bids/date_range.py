from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date


def get_date_range(request):
    """§12/§17: every dashboard panel is driven by one shared submission-date
    control. Default when neither bound is given: today-7 to today+7."""
    today = timezone.localdate()
    default_from = today - timedelta(days=7)
    default_to = today + timedelta(days=7)

    date_from = parse_date(request.query_params.get("from") or "") or default_from
    date_to = parse_date(request.query_params.get("to") or "") or default_to
    return date_from, date_to

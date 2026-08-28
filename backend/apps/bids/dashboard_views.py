"""§12 dashboard endpoints. Everything is computed in the database via
annotate/aggregate — never looped in Python — and BDT/USD are always kept
as separate sums, never added together (§8, §20)."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncQuarter
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAuthenticatedViewer

from .date_range import get_date_range
from .models import Bid

BREAKDOWN_FIELDS = {
    "client": "client__name",
    "bid_manager": "bid_manager__canonical_name",
    "team": "team__name",
    "result": "result",
}

# §12: pick the trend/runway bucket from the span.
DAILY_MAX_DAYS = 31
MONTHLY_MAX_DAYS = 800


def bucket_mode_for_span(span_days):
    if span_days <= DAILY_MAX_DAYS:
        return "daily"
    if span_days <= MONTHLY_MAX_DAYS:
        return "monthly"
    return "quarterly"


def trunc_for_mode(mode):
    return {"daily": TruncDate, "monthly": TruncMonth, "quarterly": TruncQuarter}[mode]("submission_date")


def money_by_currency(queryset, amount_field, currency_field):
    totals = queryset.aggregate(
        bdt=Sum(amount_field, filter=Q(**{currency_field: "BDT"})),
        usd=Sum(amount_field, filter=Q(**{currency_field: "USD"})),
    )
    return {"BDT": totals["bdt"] or Decimal("0"), "USD": totals["usd"] or Decimal("0")}


def compute_summary(date_from, date_to):
    qs = Bid.objects.filter(submission_date__gte=date_from, submission_date__lte=date_to)

    total = qs.count()
    submitted = qs.filter(submission_status="SUBMITTED").count()
    not_submitted = qs.filter(submission_status="NOT SUBMITTED").count()

    result_counts = {row["result"]: row["n"] for row in qs.values("result").annotate(n=Count("id"))}
    # Lowest counts as a win, Disqualified as a loss — same grouping as
    # DashboardBreakdownView's won/lost, so every panel agrees with the KPIs.
    won = result_counts.get("WON", 0) + result_counts.get("LOWEST", 0)
    lost = result_counts.get("LOST", 0) + result_counts.get("DISQUALIFIED", 0)
    pending = result_counts.get("PENDING", 0)
    decided = won + lost
    win_rate_pct = round(won / decided * 100, 1) if decided else None

    # Bank guarantees not yet expired, among bids in range — a different
    # question from "total security amount for bids in range" (security_locked
    # below sums every bid regardless of whether its guarantee has expired).
    today = timezone.localdate()
    live_qs = qs.filter(bg_expiry_date__gte=today)
    security_live = {
        "count": live_qs.filter(security_amount__isnull=False).count(),
        "locked": money_by_currency(live_qs, "security_amount", "security_currency"),
    }

    return {
        "from": date_from,
        "to": date_to,
        "total": total,
        "submitted": submitted,
        "not_submitted": not_submitted,
        "won": won,
        "lost": lost,
        "pending": pending,
        "awaiting_result": pending,
        "win_rate_pct": win_rate_pct,
        "result_breakdown": {(k or "(blank)"): v for k, v in result_counts.items()},
        "security_locked": money_by_currency(qs, "security_amount", "security_currency"),
        "security_live": security_live,
    }


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticatedViewer]

    def get(self, request):
        date_from, date_to = get_date_range(request)
        return Response(compute_summary(date_from, date_to))


class DashboardTrendView(APIView):
    """Adaptive bucketing (§12) — never renders 365 daily bars."""

    permission_classes = [IsAuthenticatedViewer]

    def get(self, request):
        date_from, date_to = get_date_range(request)
        span_days = (date_to - date_from).days
        mode = bucket_mode_for_span(span_days)

        qs = (
            Bid.objects.filter(submission_date__gte=date_from, submission_date__lte=date_to)
            .annotate(bucket=trunc_for_mode(mode))
            .values("bucket")
            .annotate(
                count=Count("id"),
                # The submitted/not_submitted split is what the "Submitted vs
                # not submitted" stacked chart needs, and what the runway
                # panel falls back to for spans too long for a day rail (§12).
                submitted=Count("id", filter=Q(submission_status="SUBMITTED")),
                not_submitted=Count("id", filter=Q(submission_status="NOT SUBMITTED")),
            )
            .order_by("bucket")
        )

        return Response(
            {
                "from": date_from,
                "to": date_to,
                "bucket": mode,
                "points": [
                    {
                        "bucket": row["bucket"],
                        "count": row["count"],
                        "submitted": row["submitted"],
                        "not_submitted": row["not_submitted"],
                    }
                    for row in qs
                ],
            }
        )


class DashboardBreakdownView(APIView):
    permission_classes = [IsAuthenticatedViewer]

    def get(self, request):
        date_from, date_to = get_date_range(request)
        by = request.query_params.get("by", "client")
        field = BREAKDOWN_FIELDS.get(by)
        if field is None:
            return Response(
                {"detail": f"Invalid 'by'. Choose one of {sorted(BREAKDOWN_FIELDS)}."}, status=400
            )

        qs = (
            Bid.objects.filter(submission_date__gte=date_from, submission_date__lte=date_to)
            .annotate(label=F(field))
            .values("label")
            .annotate(
                count=Count("id"),
                # Same Won+Lowest / Lost+Disqualified grouping as the summary
                # KPIs — one consistent definition of "won"/"lost" everywhere.
                won=Count("id", filter=Q(result__in=["WON", "LOWEST"])),
                lost=Count("id", filter=Q(result__in=["LOST", "DISQUALIFIED"])),
            )
            .order_by("-count")
        )

        return Response(
            {
                "from": date_from,
                "to": date_to,
                "by": by,
                "breakdown": [
                    {
                        "label": row["label"] or "(blank)",
                        "count": row["count"],
                        "won": row["won"],
                        "lost": row["lost"],
                    }
                    for row in qs
                ],
            }
        )


class DashboardDeadlinesView(APIView):
    """The submission runway (§12): a day-by-day rail for short spans, a
    bucketed volume strip for longer ones. The sheet has zero future
    submission dates (§12's known gap) — `marker` still distinguishes
    submitted/open/passed so the frontend can surface that instead of an
    empty rail."""

    permission_classes = [IsAuthenticatedViewer]

    def get(self, request):
        date_from, date_to = get_date_range(request)
        span_days = (date_to - date_from).days
        today = timezone.localdate()

        qs = Bid.objects.filter(
            submission_date__gte=date_from, submission_date__lte=date_to
        ).select_related("client")

        if span_days <= DAILY_MAX_DAYS:
            items = []
            for bid in qs.order_by("submission_date"):
                if bid.submission_status == "SUBMITTED":
                    marker = "submitted"
                elif bid.submission_date and bid.submission_date < today:
                    marker = "passed"
                else:
                    marker = "open"
                items.append(
                    {
                        "id": bid.id,
                        "reference": bid.reference,
                        "client": bid.client.name,
                        "stage": bid.stage,
                        "submission_date": bid.submission_date,
                        "submission_status": bid.submission_status,
                        "result": bid.result,
                        "marker": marker,
                    }
                )
            payload = {"mode": "rail", "items": items}
        else:
            mode = "monthly" if span_days <= MONTHLY_MAX_DAYS else "quarterly"
            bucketed = (
                qs.annotate(bucket=trunc_for_mode(mode))
                .values("bucket")
                .annotate(count=Count("id"))
                .order_by("bucket")
            )
            payload = {"mode": "bucketed", "bucket": mode, "buckets": list(bucketed)}

        payload.update({"from": date_from, "to": date_to})
        return Response(payload)


class DashboardBgExposureView(APIView):
    """GET /dashboard/bg-exposure/?days=60 (§17) — bank guarantees expiring
    within `days` of today. `from`/`to`, if given, additionally scope which
    bids are considered by submission date, same as every other panel (§12);
    `days` is what actually drives the expiry window."""

    permission_classes = [IsAuthenticatedViewer]

    def get(self, request):
        days = int(request.query_params.get("days", 60))
        today = timezone.localdate()
        horizon = today + timedelta(days=days)

        qs = Bid.objects.filter(
            bg_expiry_date__isnull=False, bg_expiry_date__gte=today, bg_expiry_date__lte=horizon
        )

        if request.query_params.get("from") or request.query_params.get("to"):
            date_from, date_to = get_date_range(request)
            qs = qs.filter(submission_date__gte=date_from, submission_date__lte=date_to)

        qs = qs.select_related("client").order_by("bg_expiry_date")
        security_locked = money_by_currency(qs, "security_amount", "security_currency")

        items = [
            {
                "id": bid.id,
                "reference": bid.reference,
                "client": bid.client.name,
                "bg_expiry_date": bid.bg_expiry_date,
                "bg_bank": bid.bg_bank,
                "security_amount_raw": bid.security_amount_raw,
                "security_amount": bid.security_amount,
                "security_currency": bid.security_currency,
            }
            for bid in qs
        ]

        return Response(
            {
                "days": days,
                "as_of": today,
                "count": len(items),
                "security_locked": security_locked,
                "items": items,
            }
        )


class DashboardClassicView(APIView):
    """The old indigo layout (§19) — same underlying data as `summary`, same
    shared date control (§12); only the frontend's presentation differs."""

    permission_classes = [IsAuthenticatedViewer]

    def get(self, request):
        date_from, date_to = get_date_range(request)
        return Response(compute_summary(date_from, date_to))

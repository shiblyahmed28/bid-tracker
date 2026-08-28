import uuid

from django.conf import settings
from django.db import connection, models
from django.db.models import Count, OuterRef, Subquery
from django.utils import timezone


def next_arrival_seq():
    """Pulls from the `bids_arrival_seq` Postgres sequence — atomic under
    concurrent sync workers and manual creation, unlike a MAX()+1 query."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('bids_arrival_seq')")
        return cursor.fetchone()[0]


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Person(models.Model):
    """Sheet columns cam / sales-resource / bid-manager collapse into this
    table. Match case-insensitively on the whitespace-stripped name (§8)."""

    canonical_name = models.CharField(max_length=200, unique=True)
    aliases = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["canonical_name"]
        verbose_name_plural = "people"

    def __str__(self):
        return self.canonical_name


class Client(models.Model):
    name = models.CharField(max_length=255)
    canonical_name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class BidQuerySet(models.QuerySet):
    def with_serial(self):
        """Display position, recomputed on every query — never stored, and
        closes gaps on delete. A correlated subquery (this bid's 1-based rank
        by arrival_seq among all non-deleted bids) rather than a Window(),
        because SQL computes window functions after WHERE: annotating with
        Window() and then filtering the result (e.g. the register's column
        filters) would silently rank only the filtered rows instead of the
        whole table. A subquery has its own independent WHERE, so serial
        stays correct regardless of what the outer queryset filters on."""
        rank = (
            self.model.objects.filter(arrival_seq__lte=OuterRef("arrival_seq"))
            .order_by()
            .values("is_deleted")
            .annotate(rank=Count("pk"))
            .values("rank")
        )
        return self.annotate(serial=Subquery(rank))


class BidManager(models.Manager):
    def get_queryset(self):
        return BidQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def with_serial(self):
        return self.get_queryset().with_serial()


class Bid(models.Model):
    class Source(models.TextChoices):
        SHEET = "sheet", "Sheet"
        APP = "app", "App"

    class Currency(models.TextChoices):
        BDT = "BDT", "BDT"
        USD = "USD", "USD"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=20, unique=True, editable=False)
    arrival_seq = models.BigIntegerField(unique=True, default=next_arrival_seq, editable=False)

    uid = models.UUIDField(null=True, blank=True, unique=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.APP)
    sheet_row = models.IntegerField(null=True, blank=True)

    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="bids")
    description = models.TextField(blank=True)

    cam = models.ForeignKey(
        Person, null=True, blank=True, on_delete=models.PROTECT, related_name="bids_as_cam"
    )
    sales_resource = models.ForeignKey(
        Person, null=True, blank=True, on_delete=models.PROTECT, related_name="bids_as_sales_resource"
    )
    bid_manager = models.ForeignKey(
        Person, null=True, blank=True, on_delete=models.PROTECT, related_name="bids_as_bid_manager"
    )

    # New fields (§7) — app-native, never touched by sync.
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.PROTECT, related_name="bids")
    engaged_resources = models.ManyToManyField(Person, blank=True, related_name="engaged_bids")
    engagement_from = models.DateField(null=True, blank=True)
    engagement_to = models.DateField(null=True, blank=True)

    stage = models.CharField(max_length=100, blank=True)
    initiation_mode = models.CharField(max_length=100, blank=True)
    procurement_type = models.CharField(max_length=100, blank=True)

    is_goods = models.BooleanField(default=False)
    is_works = models.BooleanField(default=False)
    is_service = models.BooleanField(default=False)

    tender_id = models.CharField(max_length=100, blank=True)

    # Sheet column 13 ("initiation", §5) — a real date column distinct from both
    # initiation_mode and the ignored column-14 annotation. Not in CLAUDE.md §10's
    # model listing; added so this data isn't silently dropped on sync.
    initiation_date = models.DateField(null=True, blank=True)
    published_date = models.DateField(null=True, blank=True)
    prebid_date = models.DateField(null=True, blank=True)
    prebid_time = models.TimeField(null=True, blank=True)
    submission_date = models.DateField(null=True, blank=True, db_index=True)
    submission_time = models.TimeField(null=True, blank=True)

    submission_status = models.CharField(max_length=100, blank=True)
    result = models.CharField(max_length=100, blank=True)

    security_mode = models.CharField(max_length=100, blank=True)
    security_amount_raw = models.TextField(blank=True)
    security_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    security_currency = models.CharField(max_length=3, choices=Currency.choices, blank=True)

    credit_facility_raw = models.TextField(blank=True)
    credit_facility = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    credit_facility_currency = models.CharField(max_length=3, choices=Currency.choices, blank=True)

    bg_issue_date = models.DateField(null=True, blank=True)
    bg_reference = models.CharField(max_length=100, blank=True)
    bg_bank = models.CharField(max_length=150, blank=True)
    bg_expiry_date = models.DateField(null=True, blank=True)

    remarks = models.TextField(blank=True)

    locally_overridden = models.JSONField(default=list, blank=True)
    missing_from_sheet = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deadline_alert_sent_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_bids"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_bids"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BidManager()
    all_objects = BidQuerySet.as_manager()

    class Meta:
        ordering = ["arrival_seq"]

    def __str__(self):
        return self.reference

    def save(self, *args, **kwargs):
        if not self.reference:
            year = timezone.localdate().year
            self.reference = f"SPC-{year}-{self.arrival_seq:04d}"
        super().save(*args, **kwargs)

    @property
    def engagement_days(self):
        if self.engagement_from and self.engagement_to:
            return (self.engagement_to - self.engagement_from).days
        return None

    def apply_change(self, field, value, actor):
        """The only path for manual edits. Tracks the override so the next
        sync raises a SyncConflict instead of silently clobbering it (§9),
        and writes the audit trail (§10)."""
        from apps.audit.models import AuditEntry

        is_m2m = self._meta.get_field(field).many_to_many
        if is_m2m:
            # Only engaged_resources today — never sheet-owned, but still
            # goes through apply_change so it gets an audit trail like
            # everything else. Direct attribute assignment isn't allowed for
            # M2M fields, hence the .set() special case.
            old_value = list(getattr(self, field).all())
            getattr(self, field).set(value)
        else:
            old_value = getattr(self, field)
            setattr(self, field, value)

        is_human = actor is not None
        if is_human:
            overridden = list(self.locally_overridden)
            if field not in overridden:
                overridden.append(field)
            self.locally_overridden = overridden
            self.updated_by = actor

        self.save()

        def describe(v):
            if is_m2m:
                return ", ".join(str(item) for item in v)
            return "" if v is None else str(v)

        AuditEntry.objects.create(
            actor=actor,
            actor_label="" if is_human else "System (sync)",
            action=AuditEntry.Action.BID_UPDATE,
            bid=self,
            field=field,
            old_value=describe(old_value),
            new_value=describe(value),
        )

        from apps.notifications.services import notify_field_change

        notify_field_change(self, field, describe(old_value), describe(value), actor)


class BidNote(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="bid_notes")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note on {self.bid.reference} by {self.author or 'unknown'}"

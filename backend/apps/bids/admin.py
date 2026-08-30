from django.contrib import admin

from .models import Bid, BidCostLine, BidEngagement, BidNote, Client, Person, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("canonical_name", "person_type", "organization", "email", "is_active")
    list_filter = ("person_type", "is_active")
    search_fields = ("canonical_name", "email")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "canonical_name")
    search_fields = ("name", "canonical_name")


class BidNoteInline(admin.TabularInline):
    model = BidNote
    extra = 0
    readonly_fields = ("author", "created_at")


class BidEngagementInline(admin.TabularInline):
    """engaged_resources now goes through BidEngagement (§Phase 19 item 1),
    which has extra required-ish fields — Django admin can't manage that via
    filter_horizontal any more, only via an inline on the through model."""

    model = BidEngagement
    extra = 0
    autocomplete_fields = ("person",)


class BidCostLineInline(admin.TabularInline):
    model = BidCostLine
    extra = 0
    readonly_fields = ("created_by", "created_at")


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "client",
        "team",
        "stage",
        "result",
        "bid_manager",
        "submission_date",
        "engaged_resources_list",
        "source",
        "is_deleted",
    )
    list_filter = ("team", "stage", "result", "source", "is_deleted", "missing_from_sheet")
    search_fields = ("reference", "tender_id", "client__name", "description")
    autocomplete_fields = ("client", "cam", "sales_resource", "bid_manager")
    readonly_fields = ("id", "reference", "arrival_seq", "uid", "created_at", "updated_at")
    inlines = [BidEngagementInline, BidCostLineInline, BidNoteInline]

    def get_queryset(self, request):
        return Bid.all_objects.get_queryset()

    @admin.display(description="Engaged resources")
    def engaged_resources_list(self, obj):
        return ", ".join(p.canonical_name for p in obj.engaged_resources.all())

from django.contrib import admin

from .models import (
    ChoiceList,
    ChoiceValue,
    DeadlineReminderRule,
    DeadlineReminderSent,
    NotificationPolicy,
    UserCapability,
    UserNotificationPolicyOverride,
)


class ChoiceValueInline(admin.TabularInline):
    model = ChoiceValue
    extra = 0
    readonly_fields = ("created_by_sync", "created_by", "created_at")


@admin.register(ChoiceList)
class ChoiceListAdmin(admin.ModelAdmin):
    list_display = ("key", "label", "is_locked")
    readonly_fields = ("key",)
    inlines = [ChoiceValueInline]


@admin.register(ChoiceValue)
class ChoiceValueAdmin(admin.ModelAdmin):
    list_display = ("list", "value", "label", "is_active", "created_by_sync", "sort_order")
    list_filter = ("list", "is_active", "created_by_sync")
    search_fields = ("value", "label")


@admin.register(UserCapability)
class UserCapabilityAdmin(admin.ModelAdmin):
    list_display = ("user", "capability", "granted", "granted_by", "granted_at")
    list_filter = ("capability", "granted")
    search_fields = ("user__email",)


@admin.register(NotificationPolicy)
class NotificationPolicyAdmin(admin.ModelAdmin):
    list_display = ("event_key", "label", "default_in_app", "default_email", "is_active")
    readonly_fields = ("event_key",)


@admin.register(UserNotificationPolicyOverride)
class UserNotificationPolicyOverrideAdmin(admin.ModelAdmin):
    list_display = ("user", "policy", "in_app", "email")
    search_fields = ("user__email",)


@admin.register(DeadlineReminderRule)
class DeadlineReminderRuleAdmin(admin.ModelAdmin):
    list_display = ("days_before", "is_active", "applies_to_roles")
    readonly_fields = ("days_before",)
    filter_horizontal = ("users",)


@admin.register(DeadlineReminderSent)
class DeadlineReminderSentAdmin(admin.ModelAdmin):
    list_display = ("bid", "rule", "sent_at")

    def has_add_permission(self, request):
        return False

from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditEntry
from apps.bids.models import BidEngagement, Client, Person, Team

from .capabilities import SettingsPermission
from .models import (
    ChoiceList,
    ChoiceValue,
    DeadlineReminderRule,
    NotificationPolicy,
    UserCapability,
    WelcomeEmailSettings,
)
from .serializers import (
    CapabilityReferenceSerializer,
    ChoiceListSerializer,
    ChoiceValueRenameSerializer,
    ChoiceValueReorderSerializer,
    ChoiceValueSerializer,
    DeadlineReminderRuleSerializer,
    NotificationPolicySerializer,
    PersonEngagementSerializer,
    PersonMergeSerializer,
    SettingsClientSerializer,
    SettingsPersonSerializer,
    SettingsTeamSerializer,
    UserCapabilityGrantSerializer,
    UserCapabilityOverrideSerializer,
    WelcomeEmailSettingsSerializer,
)
from .services import (
    NoEmailError,
    SamePersonError,
    SelfLockoutError,
    WelcomeEmailsDisabledError,
    clear_capability_override,
    find_duplicate_person_groups,
    grant_capability,
    merge_persons,
    rename_value,
    send_welcome_email,
)


def _audit(request, action, **kwargs):
    AuditEntry.objects.create(actor=request.user, actor_label=request.user.email, action=action, **kwargs)


class AuditedModelViewSet(viewsets.ModelViewSet):
    """Writes one AuditEntry per create/update/delete (§Phase 15D: "every
    mutation writes an audit entry"). `audit_tracked_fields` drives per-field
    diffing on update, mirroring UserViewSet's existing convention."""

    audit_create_action = AuditEntry.Action.SETTINGS_CHANGE
    audit_update_action = AuditEntry.Action.SETTINGS_CHANGE
    audit_delete_action = AuditEntry.Action.SETTINGS_CHANGE
    audit_tracked_fields = []

    def perform_create(self, serializer):
        instance = serializer.save()
        _audit(self.request, self.audit_create_action, new_value=str(instance))

    def perform_update(self, serializer):
        instance = serializer.instance
        old_values = {f: getattr(instance, f) for f in self.audit_tracked_fields}
        updated = serializer.save()
        for field in self.audit_tracked_fields:
            old, new = old_values[field], getattr(updated, field)
            if old != new:
                _audit(self.request, self.audit_update_action, field=field, old_value=str(old), new_value=str(new))

    def perform_destroy(self, instance):
        label = str(instance)
        instance.delete()
        _audit(self.request, self.audit_delete_action, old_value=label)


class ChoiceListViewSet(AuditedModelViewSet):
    """GET is access_master_settings; writes need manage_choice_lists. The
    `key` is read-only (see serializer) and locked lists can't be deleted."""

    queryset = ChoiceList.objects.all()
    serializer_class = ChoiceListSerializer
    permission_classes = [SettingsPermission("manage_choice_lists")]
    lookup_field = "key"
    # No POST: the 8 lists are seeded by migration (§Phase 15A) and `key` is
    # read-only, so creating a new list via this serializer isn't meaningful
    # yet — only managing the seeded ones (label/description edits, deleting
    # a never-locked one) is in scope this phase.
    http_method_names = ["get", "patch", "delete", "head", "options"]
    audit_tracked_fields = ["label", "description"]

    def perform_destroy(self, instance):
        if instance.is_locked:
            from rest_framework.exceptions import ValidationError

            raise ValidationError("This list is locked and cannot be deleted.")
        super().perform_destroy(instance)


class ChoiceValueListCreateView(generics.ListCreateAPIView):
    serializer_class = ChoiceValueSerializer
    permission_classes = [SettingsPermission("manage_choice_lists")]

    def get_choice_list(self):
        return get_object_or_404(ChoiceList, key=self.kwargs["list_key"])

    def get_queryset(self):
        return ChoiceValue.objects.filter(list=self.get_choice_list())

    def perform_create(self, serializer):
        choice_list = self.get_choice_list()
        instance = serializer.save(
            list=choice_list,
            created_by=self.request.user,
            sort_order=serializer.validated_data.get("sort_order", choice_list.values.count()),
        )
        _audit(
            self.request,
            AuditEntry.Action.CHOICE_VALUE_CREATE,
            field=choice_list.key,
            new_value=f"{instance.value} ({instance.label})",
        )


class ChoiceValueDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ChoiceValueSerializer
    permission_classes = [SettingsPermission("manage_choice_lists")]

    def get_queryset(self):
        return ChoiceValue.objects.filter(list__key=self.kwargs["list_key"])

    def perform_update(self, serializer):
        instance = serializer.instance
        tracked = ["label", "sort_order", "is_active", "is_default"]
        old_values = {f: getattr(instance, f) for f in tracked}
        updated = serializer.save()
        for field in tracked:
            old, new = old_values[field], getattr(updated, field)
            if old != new:
                _audit(
                    self.request,
                    AuditEntry.Action.CHOICE_VALUE_UPDATE,
                    field=f"{updated.list.key}.{updated.value}.{field}",
                    old_value=str(old),
                    new_value=str(new),
                )


class ChoiceValueRenameView(APIView):
    """POST /settings/choice-lists/{key}/values/{id}/rename/ — renames the
    value everywhere it's used on a Bid, in one transaction (§Phase 15A)."""

    permission_classes = [SettingsPermission("manage_choice_lists")]

    def post(self, request, list_key, pk):
        choice_value = get_object_or_404(ChoiceValue, pk=pk, list__key=list_key)
        serializer = ChoiceValueRenameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_count, result_value = rename_value(
            choice_value, serializer.validated_data["new_value"], serializer.validated_data["new_label"], request.user
        )
        return Response(
            {"updated_bids": updated_count, "value": ChoiceValueSerializer(result_value).data}, status=200
        )


class ChoiceValueReorderView(APIView):
    """POST /settings/choice-lists/{key}/reorder/ — {"order": [id, id, ...]}."""

    permission_classes = [SettingsPermission("manage_choice_lists")]

    def post(self, request, list_key):
        choice_list = get_object_or_404(ChoiceList, key=list_key)
        serializer = ChoiceValueReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ids = serializer.validated_data["order"]
        values = {v.id: v for v in ChoiceValue.objects.filter(list=choice_list, id__in=ids)}
        for index, value_id in enumerate(ids):
            if value_id in values:
                values[value_id].sort_order = index
        ChoiceValue.objects.bulk_update(values.values(), ["sort_order"])
        _audit(request, AuditEntry.Action.CHOICE_VALUE_UPDATE, field=choice_list.key, new_value="reordered")
        return Response(status=204)


class CapabilitiesReferenceView(APIView):
    """GET /settings/capabilities/ — the fixed capability list + role defaults."""

    permission_classes = [SettingsPermission()]

    def get(self, request):
        return Response(CapabilityReferenceSerializer({}).data)


class UserCapabilitiesView(APIView):
    """GET effective capabilities + overrides for one user; POST to grant or
    revoke one (§Phase 15B — guards self-lockout and are audited)."""

    permission_classes = [SettingsPermission("manage_users")]

    def get(self, request, user_id):
        from apps.accounts.models import User
        from .capabilities import CAPABILITIES, role_default_capabilities

        target = get_object_or_404(User, pk=user_id)
        overrides = {o.capability: o for o in target.capability_overrides.all()}
        defaults = role_default_capabilities(target.role)

        effective = []
        for capability in CAPABILITIES:
            override = overrides.get(capability)
            effective.append(
                {
                    "capability": capability,
                    "granted": override.granted if override else capability in defaults,
                    "source": "override" if override else "role_default",
                }
            )
        return Response(
            {
                "user": user_id,
                "role": target.role,
                "effective": effective,
                "overrides": UserCapabilityOverrideSerializer(overrides.values(), many=True).data,
            }
        )

    def post(self, request, user_id):
        from apps.accounts.models import User

        target = get_object_or_404(User, pk=user_id)
        serializer = UserCapabilityGrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            grant_capability(
                target, serializer.validated_data["capability"], serializer.validated_data["granted"], request.user
            )
        except SelfLockoutError as exc:
            return Response({"detail": str(exc)}, status=400)

        return self.get(request, user_id)

    def delete(self, request, user_id):
        """Clears an explicit override, reverting to the role default — the
        third state of the tri-state capability matrix (§Phase 16)."""
        from apps.accounts.models import User

        target = get_object_or_404(User, pk=user_id)
        capability = request.query_params.get("capability")
        if not capability:
            return Response({"detail": "capability is required."}, status=400)

        try:
            clear_capability_override(target, capability, request.user)
        except SelfLockoutError as exc:
            return Response({"detail": str(exc)}, status=400)

        return self.get(request, user_id)


class NotificationPolicyViewSet(AuditedModelViewSet):
    queryset = NotificationPolicy.objects.all()
    serializer_class = NotificationPolicySerializer
    permission_classes = [SettingsPermission("manage_notification_policy")]
    http_method_names = ["get", "patch", "head", "options"]
    audit_update_action = AuditEntry.Action.NOTIFICATION_POLICY_UPDATE
    audit_tracked_fields = ["default_in_app", "default_email", "applies_to_roles", "is_active"]


class DeadlineReminderRuleViewSet(AuditedModelViewSet):
    queryset = DeadlineReminderRule.objects.all()
    serializer_class = DeadlineReminderRuleSerializer
    permission_classes = [SettingsPermission("manage_notification_policy")]
    http_method_names = ["get", "patch", "head", "options"]
    audit_update_action = AuditEntry.Action.DEADLINE_RULE_UPDATE
    audit_tracked_fields = ["is_active", "applies_to_roles"]


class SettingsClientViewSet(AuditedModelViewSet):
    queryset = Client.objects.all()
    serializer_class = SettingsClientSerializer
    permission_classes = [SettingsPermission("manage_choice_lists")]
    audit_tracked_fields = ["name"]


class SettingsPersonViewSet(AuditedModelViewSet):
    """The "Engaged Resources" management screen (§Phase 20 item 2, label
    change only — the model stays Person). ?person_type=&is_active= filter
    the list; every field but the read-only ones is inline-editable."""

    queryset = Person.objects.all()
    serializer_class = SettingsPersonSerializer
    permission_classes = [SettingsPermission("manage_choice_lists")]
    audit_tracked_fields = [
        "canonical_name", "email", "person_type", "organization", "phone", "is_active", "user"
    ]

    def get_queryset(self):
        qs = super().get_queryset()
        person_type = self.request.query_params.get("person_type")
        if person_type:
            qs = qs.filter(person_type=person_type)
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() in ("1", "true", "yes"))
        return qs


class PersonDuplicatesView(APIView):
    """GET /settings/people/duplicates/ (§Phase 20 item 3) — likely-duplicate
    groups by normalized name, for the merge tool. The phase spec's own
    guidance: run this before turning on welcome emails."""

    permission_classes = [SettingsPermission("manage_choice_lists")]

    def get(self, request):
        groups = find_duplicate_person_groups()
        return Response([{"people": SettingsPersonSerializer(people, many=True).data} for people in groups])


class PersonMergeView(APIView):
    """POST /settings/people/{id}/merge/ — {"duplicate_id": N}. `id` in the
    URL is the surviving record; duplicate_id is absorbed into it and
    deactivated, never hard-deleted (§Phase 20 item 3)."""

    permission_classes = [SettingsPermission("manage_choice_lists")]

    def post(self, request, pk):
        survivor = get_object_or_404(Person, pk=pk)
        serializer = PersonMergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        duplicate = get_object_or_404(Person, pk=serializer.validated_data["duplicate_id"])

        try:
            result = merge_persons(survivor, duplicate, request.user)
        except SamePersonError as exc:
            return Response({"detail": str(exc)}, status=400)

        return Response({"survivor": SettingsPersonSerializer(survivor).data, **result})


class PersonEngagementsView(APIView):
    """GET /settings/people/{id}/engagements/ (§Phase 20 item 4) — every bid
    this person was engaged on, with days/dates/convenience_bill and totals."""

    permission_classes = [SettingsPermission("manage_choice_lists")]

    def get(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        engagements = (
            BidEngagement.objects.filter(person=person)
            .select_related("bid", "bid__client")
            .order_by("-bid__submission_date")
        )
        totals = engagements.aggregate(days=Sum("days"), convenience_bill=Sum("convenience_bill"))
        return Response(
            {
                "person": SettingsPersonSerializer(person).data,
                "engagements": PersonEngagementSerializer(engagements, many=True).data,
                "totals": {
                    "days": totals["days"] or 0,
                    "convenience_bill": totals["convenience_bill"] or Decimal("0"),
                },
            }
        )


class WelcomeEmailSettingsView(APIView):
    """GET/PATCH /settings/welcome-email/ — the global switch (§Phase 20
    item 5), default OFF. Gated by manage_welcome_emails — a distinct,
    narrower capability than manage_choice_lists, since flipping this on
    starts sending real email to external people."""

    permission_classes = [SettingsPermission("manage_welcome_emails")]

    def get(self, request):
        return Response(WelcomeEmailSettingsSerializer(WelcomeEmailSettings.load()).data)

    def patch(self, request):
        obj = WelcomeEmailSettings.load()
        was_enabled = obj.enabled
        serializer = WelcomeEmailSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(updated_by=request.user)

        if obj.enabled != was_enabled:
            _audit(
                request,
                AuditEntry.Action.WELCOME_EMAIL_SETTINGS,
                field="enabled",
                old_value=str(was_enabled),
                new_value=str(obj.enabled),
            )
        return Response(WelcomeEmailSettingsSerializer(obj).data)


class SendWelcomeEmailView(APIView):
    """POST /settings/engagements/{id}/welcome-email/ — always admin-
    triggered (§Phase 20 item 5), never called automatically from the bid
    create/edit flow. Works for both the first send and a deliberate
    resend; the frontend only changes the button's label based on whether
    welcome_email_sent_at is already set."""

    permission_classes = [SettingsPermission("manage_welcome_emails")]

    def post(self, request, pk):
        engagement = get_object_or_404(
            BidEngagement.objects.select_related("bid", "bid__client", "person"), pk=pk
        )
        try:
            send_welcome_email(engagement, request.user)
        except (WelcomeEmailsDisabledError, NoEmailError) as exc:
            return Response({"detail": str(exc)}, status=400)

        return Response(PersonEngagementSerializer(engagement).data)


class SettingsTeamViewSet(AuditedModelViewSet):
    queryset = Team.objects.all()
    serializer_class = SettingsTeamSerializer
    permission_classes = [SettingsPermission("manage_choice_lists")]
    audit_tracked_fields = ["name", "is_active"]

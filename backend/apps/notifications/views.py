from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAuthenticatedViewer
from apps.bids.pagination import StandardPagination
from apps.settings_admin.capabilities import HasCapability

from .models import Notification, NotificationSubscription, SentEmail
from .serializers import NotificationSerializer, NotificationSettingsSerializer, SentEmailSerializer


class NotificationListView(generics.ListAPIView):
    """GET /notifications/ — the caller's own feed, newest first (§16)."""

    permission_classes = [IsAuthenticatedViewer]
    serializer_class = NotificationSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticatedViewer]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        if not notification.read:
            notification.read = True
            notification.save(update_fields=["read"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticatedViewer]

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, read=False).update(read=True)
        return Response({"updated": updated}, status=200)


class SentEmailListView(generics.ListAPIView):
    """GET /notifications/sent-log/ — admin-only "did that person get
    notified?" log (§Phase 21 item 4). Filterable by ?kind=&success=
    (true|false)&recipient=(contains)&bid=(uuid)."""

    permission_classes = [HasCapability("view_email_log")]
    serializer_class = SentEmailSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = SentEmail.objects.all()
        params = self.request.query_params

        kind = params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)

        success = params.get("success")
        if success is not None:
            qs = qs.filter(success=success.lower() in ("1", "true", "yes"))

        recipient = params.get("recipient")
        if recipient:
            qs = qs.filter(to_email__icontains=recipient)

        bid = params.get("bid")
        if bid:
            qs = qs.filter(bid_id=bid)

        return qs


class NotificationSettingsView(APIView):
    """GET/PATCH /notifications/settings/ — master switches plus every
    field's effective on/off state (§16)."""

    permission_classes = [IsAuthenticatedViewer]

    def get(self, request):
        return Response(NotificationSettingsSerializer.represent(request.user))

    def patch(self, request):
        serializer = NotificationSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        master_fields = ["notifications_muted", "email_digest", "email_deadline", "email_newbid"]
        changed = [f for f in master_fields if f in data]
        for field in changed:
            setattr(user, field, data[field])
        if changed:
            user.save(update_fields=changed)

        for field_name, enabled in data.get("fields", {}).items():
            NotificationSubscription.objects.update_or_create(
                user=user, field_name=field_name, defaults={"enabled": enabled}
            )

        return Response(NotificationSettingsSerializer.represent(user))

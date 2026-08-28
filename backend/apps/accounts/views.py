from rest_framework import generics, viewsets
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.audit.models import AuditEntry

from .models import User
from .permissions import IsAdmin, IsAuthenticatedViewer
from .serializers import MeSerializer, UserSerializer
from .utils import get_client_ip, get_user_agent

USER_TRACKED_FIELDS = ["email", "full_name", "phone", "role", "is_active", "must_change_password"]


class LoginView(TokenObtainPairView):
    """Wraps simplejwt's login to record every attempt in the audit log (§15)."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get(User.USERNAME_FIELD, "")
        ip = get_client_ip(request)
        user_agent = get_user_agent(request)

        try:
            response = super().post(request, *args, **kwargs)
        except AuthenticationFailed:
            AuditEntry.objects.create(
                actor=None,
                actor_label=email or "unknown",
                action=AuditEntry.Action.SIGN_IN_FAILED,
                ip=ip,
                user_agent=user_agent,
            )
            raise

        user = User.objects.filter(email__iexact=email).first()
        AuditEntry.objects.create(
            actor=user,
            actor_label=user.email if user else email,
            action=AuditEntry.Action.SIGN_IN,
            ip=ip,
            user_agent=user_agent,
        )
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticatedViewer]

    def post(self, request):
        raw_refresh = request.data.get("refresh")
        if not raw_refresh:
            return Response({"detail": "refresh is required."}, status=400)
        try:
            token = RefreshToken(raw_refresh)
            token.blacklist()
        except TokenError:
            return Response({"detail": "Invalid or expired token."}, status=400)

        AuditEntry.objects.create(
            actor=request.user,
            actor_label=request.user.email,
            action=AuditEntry.Action.SIGN_OUT,
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        return Response(status=205)


class MeView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticatedViewer]
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


class UserViewSet(viewsets.ModelViewSet):
    """Admin-only user CRUD (§17). Nobody — including an admin — may change their own role."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        user = serializer.save()
        AuditEntry.objects.create(
            actor=self.request.user,
            actor_label=self.request.user.email,
            action=AuditEntry.Action.USER_CREATE,
            new_value=f"{user.email} ({user.role})",
            ip=get_client_ip(self.request),
            user_agent=get_user_agent(self.request),
        )

    def perform_update(self, serializer):
        instance = serializer.instance
        if instance.pk == self.request.user.pk and "role" in serializer.validated_data:
            if serializer.validated_data["role"] != instance.role:
                raise ValidationError("You cannot change your own role.")

        old_values = {field: getattr(instance, field) for field in USER_TRACKED_FIELDS}
        user = serializer.save()

        ip = get_client_ip(self.request)
        user_agent = get_user_agent(self.request)
        for field in USER_TRACKED_FIELDS:
            old, new = old_values[field], getattr(user, field)
            if old != new:
                AuditEntry.objects.create(
                    actor=self.request.user,
                    actor_label=self.request.user.email,
                    action=AuditEntry.Action.ROLE_CHANGE
                    if field == "role"
                    else AuditEntry.Action.USER_UPDATE,
                    field=field,
                    old_value=str(old),
                    new_value=str(new),
                    ip=ip,
                    user_agent=user_agent,
                )

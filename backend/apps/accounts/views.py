from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenViewBase

from apps.audit.models import AuditEntry

from .models import User, UserSession
from .permissions import IsAdmin, IsAuthenticatedViewer
from .serializers import (
    LoginSerializer,
    MeSerializer,
    SessionAwareTokenRefreshSerializer,
    UserSerializer,
    UserSessionSerializer,
)
from .utils import blacklist_jti, get_client_ip, get_user_agent, parse_user_agent

USER_TRACKED_FIELDS = ["email", "full_name", "phone", "role", "is_active", "must_change_password"]


def _current_session_jti(request):
    return request.auth.get("session_jti") if request.auth else None


class LoginView(TokenObtainPairView):
    """Authenticates, opens a UserSession (§10/§14) and records every attempt in the
    audit log (§15). Fully re-implements TokenViewBase.post rather than wrapping
    super().post(), because it needs the serializer instance afterwards to read
    serializer.user / serializer.refresh_jti.
    """

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        email = request.data.get(User.USERNAME_FIELD, "")
        ip = get_client_ip(request)
        user_agent = get_user_agent(request)

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            self._log_failed(email, ip, user_agent)
            raise InvalidToken(e.args[0])
        except AuthenticationFailed:
            self._log_failed(email, ip, user_agent)
            raise

        user = serializer.user
        device_type, device_brand, os_name, browser = parse_user_agent(user_agent)
        UserSession.objects.create(
            user=user,
            refresh_jti=serializer.refresh_jti,
            ip=ip,
            user_agent=user_agent,
            device_type=device_type,
            device_brand=device_brand,
            os=os_name,
            browser=browser,
        )
        AuditEntry.objects.create(
            actor=user,
            actor_label=user.email,
            action=AuditEntry.Action.SIGN_IN,
            ip=ip,
            user_agent=user_agent,
        )
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

    @staticmethod
    def _log_failed(email, ip, user_agent):
        AuditEntry.objects.create(
            actor=None,
            actor_label=email or "unknown",
            action=AuditEntry.Action.SIGN_IN_FAILED,
            ip=ip,
            user_agent=user_agent,
        )


class RefreshView(TokenViewBase):
    """Rotates the token pair, then follows the moved refresh_jti onto the
    matching UserSession row and bumps last_seen_at (§14 point 2).
    """

    permission_classes = [AllowAny]
    serializer_class = SessionAwareTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        UserSession.objects.filter(refresh_jti=serializer.old_jti, revoked_at__isnull=True).update(
            refresh_jti=serializer.new_jti, last_seen_at=timezone.now()
        )
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticatedViewer]

    def post(self, request):
        raw_refresh = request.data.get("refresh")
        if not raw_refresh:
            return Response({"detail": "refresh is required."}, status=400)
        try:
            token = RefreshToken(raw_refresh)
            jti = token.payload.get("jti")
            token.blacklist()
        except TokenError:
            return Response({"detail": "Invalid or expired token."}, status=400)

        UserSession.objects.filter(refresh_jti=jti, user=request.user).update(
            revoked_at=timezone.now()
        )
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


class SessionListView(generics.ListAPIView):
    """GET /auth/sessions/ — the caller's own sessions, newest first (§14)."""

    permission_classes = [IsAuthenticatedViewer]
    serializer_class = UserSessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["current_session_jti"] = _current_session_jti(self.request)
        return context


class RevokeOthersView(APIView):
    """POST /auth/sessions/revoke-others/ — sign out everywhere else (§14)."""

    permission_classes = [IsAuthenticatedViewer]

    def post(self, request):
        current_jti = _current_session_jti(request)
        sessions = UserSession.objects.filter(user=request.user, revoked_at__isnull=True)
        if current_jti:
            sessions = sessions.exclude(refresh_jti=current_jti)

        now = timezone.now()
        ip = get_client_ip(request)
        user_agent = get_user_agent(request)
        revoked_count = 0
        for session in sessions:
            blacklist_jti(session.refresh_jti, user=session.user, created_at=session.created_at)
            session.revoked_at = now
            session.save(update_fields=["revoked_at"])
            revoked_count += 1
            AuditEntry.objects.create(
                actor=request.user,
                actor_label=request.user.email,
                action=AuditEntry.Action.SESSION_REVOKE,
                field="session",
                old_value=str(session.id),
                new_value="revoked (revoke-others)",
                ip=ip,
                user_agent=user_agent,
            )
        return Response({"revoked": revoked_count}, status=200)


class SessionRevokeView(APIView):
    """POST /auth/sessions/{id}/revoke/ — own sessions, or any session if admin (§14)."""

    permission_classes = [IsAuthenticatedViewer]

    def post(self, request, pk):
        session = get_object_or_404(UserSession, pk=pk)
        if session.user_id != request.user.id and not request.user.is_admin:
            raise PermissionDenied("You may only revoke your own sessions.")

        if session.revoked_at is None:
            blacklist_jti(session.refresh_jti, user=session.user, created_at=session.created_at)
            session.revoked_at = timezone.now()
            session.save(update_fields=["revoked_at"])
            AuditEntry.objects.create(
                actor=request.user,
                actor_label=request.user.email,
                action=AuditEntry.Action.SESSION_REVOKE,
                field="session",
                old_value=str(session.id),
                new_value=f"revoked (owner={session.user.email})",
                ip=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
        return Response(status=204)


class UserSessionsView(generics.ListAPIView):
    """GET /users/{id}/sessions/ — admin only (§14, §17)."""

    permission_classes = [IsAdmin]
    serializer_class = UserSessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(user_id=self.kwargs["user_id"])


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

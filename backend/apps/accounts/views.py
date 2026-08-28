from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenViewBase

from apps.audit.models import AuditEntry

from apps.settings_admin.capabilities import HasCapability

from .models import User, UserSession
from .permissions import IsAuthenticatedViewer
from .serializers import (
    AdminPasswordResetSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    MeSerializer,
    ProfileSerializer,
    SessionAwareTokenRefreshSerializer,
    UserSerializer,
    UserSessionSerializer,
)
from .utils import blacklist_jti, get_client_ip, get_user_agent, parse_user_agent

USER_TRACKED_FIELDS = ["email", "full_name", "phone", "role", "is_active", "must_change_password"]


def _current_session_jti(request):
    return request.auth.get("session_jti") if request.auth else None


def _revoke_sessions(sessions, *, actor, note, ip, user_agent):
    """Blacklist + mark revoked every session in `sessions`, writing one
    SESSION_REVOKE audit entry each (§14/§15). Shared by "sign out everywhere
    else", "change password" and "admin reset password"."""
    now = timezone.now()
    revoked = 0
    for session in sessions:
        blacklist_jti(session.refresh_jti, user=session.user, created_at=session.created_at)
        session.revoked_at = now
        session.save(update_fields=["revoked_at"])
        revoked += 1
        AuditEntry.objects.create(
            actor=actor,
            actor_label=actor.email,
            action=AuditEntry.Action.SESSION_REVOKE,
            field="session",
            old_value=str(session.id),
            new_value=note(session),
            ip=ip,
            user_agent=user_agent,
        )
    return revoked


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


class ProfileUpdateView(generics.UpdateAPIView):
    """PATCH /auth/profile/ — full_name, email (domain-checked), phone (§14).
    Writes one audit entry per changed field, same convention as UserViewSet."""

    permission_classes = [IsAuthenticatedViewer]
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        instance = serializer.instance
        old_values = {field: getattr(instance, field) for field in ("email", "full_name", "phone")}
        user = serializer.save()

        ip = get_client_ip(self.request)
        user_agent = get_user_agent(self.request)
        for field, old in old_values.items():
            new = getattr(user, field)
            if old != new:
                AuditEntry.objects.create(
                    actor=user,
                    actor_label=user.email,
                    action=AuditEntry.Action.USER_UPDATE,
                    field=field,
                    old_value=str(old),
                    new_value=str(new),
                    ip=ip,
                    user_agent=user_agent,
                )


class ChangePasswordView(APIView):
    """POST /auth/change-password/ — current/new/confirm (§14). Revokes every
    other session but keeps the caller's own alive, and is itself audited."""

    permission_classes = [IsAuthenticatedViewer]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])

        current_jti = _current_session_jti(request)
        sessions = UserSession.objects.filter(user=request.user, revoked_at__isnull=True)
        if current_jti:
            sessions = sessions.exclude(refresh_jti=current_jti)

        ip = get_client_ip(request)
        user_agent = get_user_agent(request)
        revoked_count = _revoke_sessions(
            sessions,
            actor=request.user,
            note=lambda session: "revoked (password-changed)",
            ip=ip,
            user_agent=user_agent,
        )
        AuditEntry.objects.create(
            actor=request.user,
            actor_label=request.user.email,
            action=AuditEntry.Action.PASSWORD_CHANGE,
            ip=ip,
            user_agent=user_agent,
        )
        return Response({"revoked_sessions": revoked_count}, status=200)


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

        revoked_count = _revoke_sessions(
            sessions,
            actor=request.user,
            note=lambda session: "revoked (revoke-others)",
            ip=get_client_ip(request),
            user_agent=get_user_agent(request),
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
    """GET /users/{id}/sessions/ — requires manage_users (§14, §17)."""

    permission_classes = [HasCapability("manage_users")]
    serializer_class = UserSessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(user_id=self.kwargs["user_id"])


class UserViewSet(viewsets.ModelViewSet):
    """User CRUD, requires manage_users (§17). Nobody — including an admin — may change their own role."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [HasCapability("manage_users")]
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

        if "role" in serializer.validated_data:
            from apps.settings_admin.services import LastAdminError, guard_last_admin_demotion

            try:
                guard_last_admin_demotion(instance, serializer.validated_data["role"])
            except LastAdminError as exc:
                raise ValidationError(str(exc))

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

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        """POST /users/{id}/reset-password/ — admin only (§14/§17). The admin
        chooses the new password directly; it is never derived from or shown
        alongside the old one, which stays hashed and unreadable regardless."""
        target = self.get_object()
        serializer = AdminPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target.set_password(data["new_password"])
        if data["force_change"]:
            target.must_change_password = True
        target.save(update_fields=["password", "must_change_password"])

        ip = get_client_ip(request)
        user_agent = get_user_agent(request)

        revoked_count = 0
        if data["revoke_sessions"]:
            revoked_count = _revoke_sessions(
                UserSession.objects.filter(user=target, revoked_at__isnull=True),
                actor=request.user,
                note=lambda session: f"revoked (admin password reset, by {request.user.email})",
                ip=ip,
                user_agent=user_agent,
            )

        emailed = False
        if data["email_user"]:
            emailed = bool(
                send_mail(
                    subject="Your Spectrum Bid Tracker password was reset",
                    message=(
                        f"An administrator ({request.user.email}) reset your password.\n\n"
                        + (
                            "You will be asked to set a new password the next time you sign in.\n\n"
                            if data["force_change"]
                            else "Contact your administrator for your new password if you were not "
                            "told it directly.\n\n"
                        )
                        + "If you did not expect this, contact an administrator immediately."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[target.email],
                    fail_silently=True,
                )
            )

        AuditEntry.objects.create(
            actor=request.user,
            actor_label=request.user.email,
            action=AuditEntry.Action.PASSWORD_RESET,
            field="password",
            new_value=(
                f"{target.email} — force_change={data['force_change']}, "
                f"emailed={emailed}, sessions_revoked={revoked_count}"
            ),
            ip=ip,
            user_agent=user_agent,
        )
        return Response(
            {"force_change": data["force_change"], "emailed": emailed, "revoked_sessions": revoked_count},
            status=200,
        )

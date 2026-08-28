from django.contrib.auth.models import update_last_login
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenObtainSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, UserSession


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "role",
            "must_change_password",
            "date_joined",
            "notifications_muted",
            "email_digest",
            "email_deadline",
            "email_newbid",
        ]
        read_only_fields = fields


class ProfileSerializer(serializers.ModelSerializer):
    """PATCH /auth/profile/ — full_name, email and phone only (§14). Email keeps
    the model's domain validator and unique constraint (excluding self on update)
    since ModelSerializer copies both from the field automatically."""

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "phone", "role", "must_change_password", "date_joined"]
        read_only_fields = ["id", "role", "must_change_password", "date_joined"]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_current_password(self, value):
        if not self.context["user"].check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Must be at least 10 characters.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Does not match the new password."})
        return attrs


class AdminPasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    confirm_password = serializers.CharField(write_only=True, style={"input_type": "password"})
    force_change = serializers.BooleanField(default=True)
    email_user = serializers.BooleanField(default=True)
    revoke_sessions = serializers.BooleanField(default=True)

    def validate_new_password(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Must be at least 10 characters.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Does not match the new password."})
        return attrs


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, style={"input_type": "password"})

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "role",
            "is_active",
            "must_change_password",
            "date_joined",
            "notifications_muted",
            "email_digest",
            "email_deadline",
            "email_newbid",
            "password",
        ]
        read_only_fields = ["id", "date_joined"]

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError(
                {"password": "This field is required when creating a user."}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.full_clean(exclude=["password"])
        instance.save()
        return instance


class LoginSerializer(TokenObtainPairSerializer):
    """Stamps a `session_jti` claim (self-referencing the refresh token's own jti)
    onto both tokens, so it survives into the access token and lets later requests
    identify "this device" without ever seeing the refresh token again.
    """

    def validate(self, attrs):
        # Skip TokenObtainPairSerializer.validate — it builds tokens without our claim.
        TokenObtainSerializer.validate(self, attrs)

        refresh = self.get_token(self.user)
        refresh["session_jti"] = refresh[jwt_settings.JTI_CLAIM]
        self.refresh_jti = refresh[jwt_settings.JTI_CLAIM]

        data = {"refresh": str(refresh), "access": str(refresh.access_token)}

        if jwt_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        return data


class SessionAwareTokenRefreshSerializer(serializers.Serializer):
    """Re-stamps `session_jti` after rotation so it always matches the *current*
    refresh_jti, and exposes old/new jti so the view can update the UserSession row.
    """

    refresh = serializers.CharField()
    access = serializers.CharField(read_only=True)
    token_class = RefreshToken

    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        self.old_jti = refresh.payload.get(jwt_settings.JTI_CLAIM)

        if jwt_settings.BLACKLIST_AFTER_ROTATION:
            try:
                refresh.blacklist()
            except AttributeError:
                pass

        refresh.set_jti()
        refresh.set_exp()
        refresh.set_iat()
        refresh["session_jti"] = refresh[jwt_settings.JTI_CLAIM]
        self.new_jti = refresh[jwt_settings.JTI_CLAIM]

        return {"access": str(refresh.access_token), "refresh": str(refresh)}


class UserSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = [
            "id",
            "ip",
            "user_agent",
            "device_type",
            "device_brand",
            "os",
            "browser",
            "created_at",
            "last_seen_at",
            "revoked_at",
            "is_active",
            "is_current",
        ]
        read_only_fields = fields

    def get_is_current(self, obj):
        current_jti = self.context.get("current_session_jti")
        return bool(current_jti) and obj.refresh_jti == current_jti

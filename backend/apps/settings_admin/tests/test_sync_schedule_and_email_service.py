"""Master Settings > Sheet sync: the admin-configurable automatic sync
interval (default 8h, previously a fixed 0/8/16 Dhaka crontab) and the
global email kill switch (default on) that gates every outbound email send,
including the one path (password reset) that bypasses the shared
notifications._send() helper entirely."""

from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.audit.models import AuditEntry
from apps.bids.models import Bid, Client
from apps.notifications.emails import send_new_bid_email
from apps.notifications.models import SentEmail
from apps.settings_admin.models import EmailServiceSettings, SyncScheduleSettings
from apps.sync.models import SyncRun
from apps.sync.tasks import sync_sheet_task

from conftest import login


@pytest.fixture
def client_obj(db):
    return Client.objects.create(name="Schedule Co", canonical_name="schedule co")


@pytest.fixture
def bid(db, client_obj):
    return Bid.objects.create(client=client_obj, description="a bid", submission_date="2026-09-15")


@pytest.mark.django_db
class TestSyncScheduleSettings:
    def test_defaults_to_eight_hours(self):
        assert SyncScheduleSettings.load().interval_hours == 8

    def test_admin_can_change_it_and_it_is_audited(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.patch("/api/v1/settings/sync-schedule/", {"interval_hours": 4}, format="json")
        assert response.status_code == 200
        assert response.data["interval_hours"] == 4
        assert SyncScheduleSettings.load().interval_hours == 4
        entry = AuditEntry.objects.get(action=AuditEntry.Action.SYNC_SCHEDULE_SETTINGS)
        assert entry.old_value == "8"
        assert entry.new_value == "4"

    def test_editor_gets_403(self, api_client, editor):
        login(api_client, editor, "EditorPass123!")
        response = api_client.patch("/api/v1/settings/sync-schedule/", {"interval_hours": 4}, format="json")
        assert response.status_code == 403

    @pytest.mark.parametrize("value", [0, -1, 169, 1000])
    def test_rejects_out_of_bounds_values(self, api_client, admin_user, value):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.patch("/api/v1/settings/sync-schedule/", {"interval_hours": value}, format="json")
        assert response.status_code == 400
        assert SyncScheduleSettings.load().interval_hours == 8  # unchanged


@pytest.mark.django_db
class TestSyncSheetTaskRespectsInterval:
    def test_runs_when_no_prior_scheduled_run_exists(self, monkeypatch):
        called = {}

        def fake_run_sync(trigger):
            called["trigger"] = trigger
            return SyncRun.objects.create(trigger=trigger), {"read": 0}

        monkeypatch.setattr("apps.sync.tasks.run_sync", fake_run_sync)
        result = sync_sheet_task()
        assert called.get("trigger") == SyncRun.Trigger.SCHEDULED
        assert result == {"read": 0}

    def test_skips_when_interval_has_not_elapsed(self, monkeypatch):
        SyncRun.objects.create(trigger=SyncRun.Trigger.SCHEDULED, started_at=timezone.now())

        def fail_run_sync(trigger):
            raise AssertionError("run_sync should not be called before the interval elapses")

        monkeypatch.setattr("apps.sync.tasks.run_sync", fail_run_sync)
        result = sync_sheet_task()
        assert result == {"skipped": True}

    def test_runs_once_interval_has_elapsed(self, monkeypatch):
        stale = SyncRun.objects.create(trigger=SyncRun.Trigger.SCHEDULED)
        SyncRun.objects.filter(pk=stale.pk).update(started_at=timezone.now() - timedelta(hours=9))

        called = {}

        def fake_run_sync(trigger):
            called["trigger"] = trigger
            return SyncRun.objects.create(trigger=trigger), {"read": 0}

        monkeypatch.setattr("apps.sync.tasks.run_sync", fake_run_sync)
        result = sync_sheet_task()
        assert called.get("trigger") == SyncRun.Trigger.SCHEDULED

    def test_shorter_configured_interval_runs_sooner(self, monkeypatch):
        SyncScheduleSettings.load()
        settings_obj = SyncScheduleSettings.load()
        settings_obj.interval_hours = 2
        settings_obj.save()

        stale = SyncRun.objects.create(trigger=SyncRun.Trigger.SCHEDULED)
        SyncRun.objects.filter(pk=stale.pk).update(started_at=timezone.now() - timedelta(hours=3))

        called = {}

        def fake_run_sync(trigger):
            called["ran"] = True
            return SyncRun.objects.create(trigger=trigger), {}

        monkeypatch.setattr("apps.sync.tasks.run_sync", fake_run_sync)
        sync_sheet_task()
        assert called.get("ran") is True


@pytest.mark.django_db
class TestEmailServiceSettings:
    def test_defaults_to_enabled(self):
        assert EmailServiceSettings.load().enabled is True

    def test_admin_can_toggle_and_it_is_audited(self, api_client, admin_user):
        login(api_client, admin_user, "AdminPass123!")
        response = api_client.patch("/api/v1/settings/email-service/", {"enabled": False}, format="json")
        assert response.status_code == 200
        assert response.data["enabled"] is False
        assert EmailServiceSettings.load().enabled is False
        entry = AuditEntry.objects.get(action=AuditEntry.Action.EMAIL_SERVICE_SETTINGS)
        assert entry.old_value == "True"
        assert entry.new_value == "False"

    def test_viewer_gets_403(self, api_client, viewer):
        login(api_client, viewer, "ViewerPass123!")
        response = api_client.patch("/api/v1/settings/email-service/", {"enabled": False}, format="json")
        assert response.status_code == 403


@pytest.mark.django_db
class TestEmailServiceKillSwitchBlocksTemplatedSends:
    def test_disabled_blocks_send_and_logs_reason(self, bid):
        from apps.accounts.models import User

        user = User.objects.create_user(email="recipient@spectrum-bd.com", password="x", role=User.Role.VIEWER)
        settings_obj = EmailServiceSettings.load()
        settings_obj.enabled = False
        settings_obj.save()

        send_new_bid_email(user, bid)

        assert len(mail.outbox) == 0
        entry = SentEmail.objects.get(to_email=user.email)
        assert entry.success is False
        assert "turned off" in entry.error

    def test_enabled_sends_normally(self, bid):
        from apps.accounts.models import User

        user = User.objects.create_user(email="recipient2@spectrum-bd.com", password="x", role=User.Role.VIEWER)
        assert EmailServiceSettings.load().enabled is True  # default

        send_new_bid_email(user, bid)

        assert len(mail.outbox) == 1
        entry = SentEmail.objects.get(to_email=user.email)
        assert entry.success is True


@pytest.mark.django_db
class TestEmailServiceKillSwitchBlocksPasswordResetSend:
    def test_disabled_blocks_password_reset_email(self, api_client, admin_user):
        from apps.accounts.models import User

        target = User.objects.create_user(
            email="reset-target@spectrum-bd.com", password="OldPass123!", role=User.Role.VIEWER
        )
        settings_obj = EmailServiceSettings.load()
        settings_obj.enabled = False
        settings_obj.save()

        login(api_client, admin_user, "AdminPass123!")
        response = api_client.post(
            f"/api/v1/users/{target.id}/reset-password/",
            {
                "new_password": "AdminChosenPass1!",
                "confirm_password": "AdminChosenPass1!",
                "force_change": True,
                "email_user": True,
                "revoke_sessions": False,
            },
            format="json",
        )
        assert response.status_code == 200
        assert len(mail.outbox) == 0
        entry = SentEmail.objects.filter(to_email=target.email, kind=SentEmail.Kind.PASSWORD_RESET).latest(
            "created_at"
        )
        assert entry.success is False
        assert "turned off" in entry.error

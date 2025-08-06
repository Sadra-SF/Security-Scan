from rest_framework import serializers
from django.core.validators import validate_email, URLValidator
from django.core.exceptions import ValidationError

from .models import NotificationChannel, NotificationRule


class NotificationChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationChannel
        fields = (
            "id",
            "project",
            "name",
            "type",
            "config",
            "enabled",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        cfg = attrs.get("config", {}) or {}
        ch_type = attrs.get("type") or getattr(self.instance, "type", "")
        ch_type = (ch_type or "").lower()

        # Basic validation by channel type
        if ch_type == NotificationChannel.ChannelType.EMAIL:
            recipients = cfg.get("recipients") or cfg.get("to") or []
            if isinstance(recipients, str):
                recipients = [recipients]
            if not recipients:
                raise serializers.ValidationError({"config": "Email channel requires recipients or to"})
            bad = []
            for e in recipients:
                try:
                    validate_email(e)
                except ValidationError:
                    bad.append(e)
            if bad:
                raise serializers.ValidationError({"config": f"Invalid email(s): {', '.join(bad)}"})
        elif ch_type in (NotificationChannel.ChannelType.SLACK, NotificationChannel.ChannelType.MS_TEAMS, NotificationChannel.ChannelType.WEBHOOK):
            url = cfg.get("webhook_url")
            if not url:
                raise serializers.ValidationError({"config": "Webhook-based channel requires webhook_url"})
            try:
                URLValidator()(url)
            except ValidationError:
                raise serializers.ValidationError({"config": "Invalid webhook_url"})
        return attrs


class NotificationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationRule
        fields = (
            "id",
            "project",
            "name",
            "event",
            "severity_min",
            "channel",
            "enabled",
            "filters",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        # Ensure channel belongs to same project
        channel = attrs.get("channel") or getattr(self.instance, "channel", None)
        project = attrs.get("project") or getattr(self.instance, "project", None)
        if channel and project and channel.project_id != project.id:
            raise serializers.ValidationError({"channel": "Channel must belong to the same project"})
        return attrs
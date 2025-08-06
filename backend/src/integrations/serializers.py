from rest_framework import serializers
from django.utils.crypto import get_random_string
from hashlib import sha256

from .models import IntegrationToken, Webhook


class IntegrationTokenSerializer(serializers.ModelSerializer):
    # Return raw token on create only
    raw_token = serializers.CharField(read_only=True)

    class Meta:
        model = IntegrationToken
        fields = (
            "id",
            "project",
            "name",
            "scopes",
            "expires_at",
            "metadata",
            "created_at",
            "updated_at",
            "raw_token",
        )
        read_only_fields = ("created_at", "updated_at")

    def create(self, validated_data):
        # Generate a one-time raw token and store its hash
        raw = get_random_string(48)
        token_hash = sha256(raw.encode("utf-8")).hexdigest()
        obj = IntegrationToken.objects.create(token_hash=token_hash, **validated_data)
        # Attach raw_token in serializer instance context for response
        obj.raw_token = raw  # transient attribute; included via field read_only=True
        return obj

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # raw_token is only present right after create (transient attribute)
        raw = getattr(instance, "raw_token", None)
        if raw:
            data["raw_token"] = raw
        else:
            data.pop("raw_token", None)
        return data


class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = (
            "id",
            "project",
            "name",
            "url",
            "secret_hash",
            "headers",
            "enabled",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")
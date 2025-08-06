from __future__ import annotations

from rest_framework import serializers

from .models import Asset, ScanProfile, ScanRun


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ["id", "name", "type", "url_or_cidr", "created_at"]
        read_only_fields = ["id", "created_at"]


class ScanProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanProfile
        fields = ["id", "name", "enabled_scanners", "created_at"]
        read_only_fields = ["id", "created_at"]


class ScanRunListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanRun
        fields = ["id", "asset", "profile", "status", "started_at", "ended_at", "meta"]
        read_only_fields = fields


class ScanRunDetailSerializer(serializers.ModelSerializer):
    # Placeholder for later expansion; currently same as list
    class Meta:
        model = ScanRun
        fields = ["id", "asset", "profile", "status", "started_at", "ended_at", "meta"]
        read_only_fields = fields
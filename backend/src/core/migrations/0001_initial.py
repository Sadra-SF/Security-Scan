# Generated placeholder migration for initial core models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Asset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("type", models.CharField(choices=[("web", "Web URL"), ("host", "Host/IP"), ("network", "Network/CIDR"), ("url", "URL"), ("cidr", "CIDR"), ("ip", "IP Address")], max_length=32)),
                ("url_or_cidr", models.CharField(max_length=1024)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="ScanProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("enabled_scanners", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="ScanRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], default="queued", max_length=16)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("meta", models.JSONField(blank=True, default=dict)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scan_runs", to="core.asset")),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="scan_runs", to="core.scanprofile")),
            ],
        ),
    ]
# Generated initial migration for scans app
from django.db import migrations, models
import django.db.models.deletion
import uuid
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("targets", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Scan",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("scanner", models.CharField(max_length=64, help_text="Scanner backend identifier, e.g., zap, nuclei")),
                ("type", models.CharField(choices=[("active", "Active"), ("passive", "Passive"), ("scheduled", "Scheduled"), ("manual", "Manual")], default="manual", max_length=16)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed"), ("canceled", "Canceled")], default="pending", max_length=16)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True, db_index=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("stats", models.JSONField(blank=True, default=dict)),
                ("target", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scans", to="targets.target")),
            ],
            options={
                "ordering": ["-started_at", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="scan",
            index=models.Index(fields=["target", "started_at"], name="scans_scan_target__f3a2c7_idx"),
        ),
        migrations.AddIndex(
            model_name="scan",
            index=models.Index(fields=["status"], name="scans_scan_status_1a6887_idx"),
        ),
    ]
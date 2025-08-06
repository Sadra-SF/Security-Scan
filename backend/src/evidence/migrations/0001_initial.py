# Generated initial migration for evidence app
from django.db import migrations, models
import django.db.models.deletion
import uuid
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("findings", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Evidence",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("kind", models.CharField(choices=[("screenshot", "Screenshot"), ("log", "Log"), ("request", "Request"), ("response", "Response"), ("artifact", "Artifact"), ("other", "Other")], default="other", max_length=16)),
                ("storage_url", models.CharField(help_text="Storage URL or path to the evidence blob", max_length=1000)),
                ("content_type", models.CharField(blank=True, max_length=128)),
                ("size", models.BigIntegerField(blank=True, null=True)),
                ("sha256", models.CharField(blank=True, help_text="Hash of content if available", max_length=64)),
                ("request_id", models.CharField(blank=True, max_length=128)),
                ("response_id", models.CharField(blank=True, max_length=128)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("finding", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="evidence", to="findings.finding")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="evidence",
            index=models.Index(fields=["kind"], name="evidence_ev_kind_1d2f84_idx"),
        ),
        migrations.AddIndex(
            model_name="evidence",
            index=models.Index(fields=["created_at"], name="evidence_ev_created_3bb0d2_idx"),
        ),
    ]
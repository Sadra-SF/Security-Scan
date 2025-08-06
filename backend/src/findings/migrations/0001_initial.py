# Generated initial migration for findings app
from django.db import migrations, models
import django.db.models.deletion
import uuid
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("targets", "0001_initial"),
        ("scans", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Finding",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("title", models.CharField(max_length=300)),
                ("description", models.TextField(blank=True)),
                ("severity", models.CharField(choices=[("info", "Info"), ("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], db_index=True, max_length=16)),
                ("status", models.CharField(choices=[("open", "Open"), ("acknowledged", "Acknowledged"), ("fixed", "Fixed"), ("false_positive", "False Positive"), ("risk_accepted", "Risk Accepted"), ("suppressed", "Suppressed")], db_index=True, default="open", max_length=16)),
                ("cvss_score", models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                ("dedupe_hash", models.CharField(help_text="Deterministic hash for deduplication within a target", max_length=64)),
                ("locations", models.JSONField(blank=True, default=list, help_text="List of affected locations/paths/URLs")),
                ("evidence_refs", models.JSONField(blank=True, default=list, help_text="IDs/refs of linked evidence (populated later)")),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("first_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_seen_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("scan", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="findings", to="scans.scan")),
                ("target", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="findings", to="targets.target")),
            ],
            options={
                "ordering": ["-severity", "-last_seen_at"],
            },
        ),
        migrations.AddIndex(
            model_name="finding",
            index=models.Index(fields=["severity"], name="findings_fi_severi_8a0d3a_idx"),
        ),
        migrations.AddIndex(
            model_name="finding",
            index=models.Index(fields=["status"], name="findings_fi_status_0d1b0e_idx"),
        ),
        migrations.AddIndex(
            model_name="finding",
            index=models.Index(fields=["last_seen_at"], name="findings_fi_last_se_2c4f08_idx"),
        ),
        migrations.AddConstraint(
            model_name="finding",
            constraint=models.UniqueConstraint(fields=("target", "dedupe_hash"), name="uniq_finding_target_dedupe"),
        ),
    ]
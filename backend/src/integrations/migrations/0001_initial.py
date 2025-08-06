# Generated initial migration for integrations app
from django.db import migrations, models
import django.db.models.deletion
import uuid
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="IntegrationToken",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("name", models.CharField(max_length=128)),
                ("token_hash", models.CharField(db_index=True, help_text="Hashed token. Raw token is never stored.", max_length=128)),
                ("scopes", models.JSONField(blank=True, default=list, help_text="List of scopes/permissions")),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="integration_tokens", to="projects.project")),
            ],
            options={
                "ordering": ["project__organization__name", "project__name", "name"],
            },
        ),
        migrations.CreateModel(
            name="Webhook",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("name", models.CharField(max_length=128)),
                ("url", models.URLField(max_length=1000)),
                ("secret_hash", models.CharField(blank=True, help_text="Hashed shared secret for signature verification", max_length=128)),
                ("headers", models.JSONField(blank=True, default=dict)),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="webhooks", to="projects.project")),
            ],
            options={
                "ordering": ["project__organization__name", "project__name", "name"],
            },
        ),
        migrations.AddIndex(
            model_name="integrationtoken",
            index=models.Index(fields=["project", "name"], name="integratio_project__eb2b0b_idx"),
        ),
        migrations.AddIndex(
            model_name="integrationtoken",
            index=models.Index(fields=["project", "token_hash"], name="integratio_project__b3e7a3_idx"),
        ),
        migrations.AddIndex(
            model_name="integrationtoken",
            index=models.Index(fields=["expires_at"], name="integratio_expires__a1b9c0_idx"),
        ),
        migrations.AddConstraint(
            model_name="integrationtoken",
            constraint=models.UniqueConstraint(fields=("project", "name"), name="uniq_integration_token_project_name"),
        ),
        migrations.AddIndex(
            model_name="webhook",
            index=models.Index(fields=["project", "enabled"], name="integratio_project__1a4d0b_idx"),
        ),
        migrations.AddConstraint(
            model_name="webhook",
            constraint=models.UniqueConstraint(fields=("project", "name"), name="uniq_webhook_project_name"),
        ),
    ]
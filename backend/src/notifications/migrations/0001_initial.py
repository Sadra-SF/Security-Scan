# Generated initial migration for notifications app
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
            name="NotificationChannel",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("name", models.CharField(max_length=128)),
                ("type", models.CharField(choices=[("email", "Email"), ("slack", "Slack"), ("webhook", "Webhook"), ("ms_teams", "Microsoft Teams")], max_length=16)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notification_channels", to="projects.project")),
            ],
            options={
                "ordering": ["project__organization__name", "project__name", "name"],
            },
        ),
        migrations.CreateModel(
            name="NotificationRule",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("name", models.CharField(max_length=128)),
                ("event", models.CharField(choices=[("scan_completed", "Scan Completed"), ("finding_created", "Finding Created"), ("finding_updated", "Finding Updated")], max_length=32)),
                ("severity_min", models.CharField(choices=[("info", "Info"), ("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], default="low", max_length=16)),
                ("enabled", models.BooleanField(default=True)),
                ("filters", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("channel", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rules", to="notifications.notificationchannel")),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notification_rules", to="projects.project")),
            ],
            options={
                "ordering": ["project__organization__name", "project__name", "name"],
            },
        ),
        migrations.AddIndex(
            model_name="notificationchannel",
            index=models.Index(fields=["project", "type"], name="notificatio_project__1d6cf6_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationchannel",
            index=models.Index(fields=["enabled"], name="notificatio_enabled_7d0602_idx"),
        ),
        migrations.AddConstraint(
            model_name="notificationchannel",
            constraint=models.UniqueConstraint(fields=("project", "name"), name="uniq_notify_channel_project_name"),
        ),
        migrations.AddIndex(
            model_name="notificationrule",
            index=models.Index(fields=["project", "event"], name="notificatio_project__f6ab2c_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationrule",
            index=models.Index(fields=["enabled"], name="notificatio_enabled_b0b2d1_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationrule",
            index=models.Index(fields=["severity_min"], name="notificatio_severity_185ae8_idx"),
        ),
        migrations.AddConstraint(
            model_name="notificationrule",
            constraint=models.UniqueConstraint(fields=("project", "name"), name="uniq_notify_rule_project_name"),
        ),
    ]
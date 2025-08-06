# Generated initial migration for reports app
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
            name="Report",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("version", models.CharField(blank=True, max_length=32)),
                ("template", models.CharField(blank=True, max_length=128)),
                ("format", models.CharField(choices=[("pdf", "PDF"), ("html", "HTML"), ("md", "Markdown")], default="pdf", max_length=8)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("generating", "Generating"), ("ready", "Ready"), ("failed", "Failed")], default="draft", max_length=16)),
                ("storage_url", models.CharField(blank=True, max_length=1000)),
                ("generated_at", models.DateTimeField(blank=True, null=True)),
                ("filters", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("meta", models.JSONField(blank=True, default=dict)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reports", to="projects.project")),
            ],
            options={
                "ordering": ["-generated_at", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["project", "created_at"], name="reports_rep_project_7f1b2a_idx"),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["status"], name="reports_rep_status_6d2b3f_idx"),
        ),
        migrations.AddIndex(
            model_name="report",
            index=models.Index(fields=["format"], name="reports_rep_format_c2817e_idx"),
        ),
    ]
# Generated initial migration for targets app
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
            name="Target",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(max_length=200)),
                ("type", models.CharField(choices=[("web", "Web"), ("api", "API"), ("host", "Host"), ("mobile", "Mobile"), ("repo", "Repository"), ("other", "Other")], default="web", max_length=16)),
                ("address", models.CharField(max_length=500, help_text="Hostname, URL, IP/CIDR, package name, or identifier")),
                ("tags", models.JSONField(blank=True, default=list)),
                ("settings", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="targets", to="projects.project")),
            ],
            options={
                "ordering": ["project__organization__name", "project__name", "name"],
            },
        ),
        migrations.AddIndex(
            model_name="target",
            index=models.Index(fields=["project", "slug"], name="targets_tar_projec_3c1af0_idx"),
        ),
        migrations.AddIndex(
            model_name="target",
            index=models.Index(fields=["project", "name"], name="targets_tar_projec_87d5bb_idx"),
        ),
        migrations.AddIndex(
            model_name="target",
            index=models.Index(fields=["type"], name="targets_tar_type_b1a1df_idx"),
        ),
        migrations.AddConstraint(
            model_name="target",
            constraint=models.UniqueConstraint(fields=("project", "slug"), name="uniq_target_project_slug"),
        ),
    ]
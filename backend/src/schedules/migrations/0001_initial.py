# Generated initial migration for schedules app
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
            name="Schedule",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("minute", models.CharField(default="*", max_length=64)),
                ("hour", models.CharField(default="*", max_length=64)),
                ("day_of_week", models.CharField(default="*", max_length=64)),
                ("day_of_month", models.CharField(default="*", max_length=64)),
                ("month_of_year", models.CharField(default="*", max_length=64)),
                ("scanner", models.CharField(max_length=64)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("enabled", models.BooleanField(default=True)),
                ("last_run_at", models.DateTimeField(blank=True, null=True)),
                ("next_run_at", models.DateTimeField(blank=True, null=True, db_index=True)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("target", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="schedules", to="targets.target")),
            ],
            options={
                "ordering": ["-next_run_at", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="schedule",
            index=models.Index(fields=["next_run_at", "enabled"], name="schedules_sc_next_ru_4f0b1e_idx"),
        ),
        migrations.AddIndex(
            model_name="schedule",
            index=models.Index(fields=["target"], name="schedules_sc_target_019679_idx"),
        ),
        migrations.AddIndex(
            model_name="schedule",
            index=models.Index(fields=["scanner"], name="schedules_sc_scanner_6f33f2_idx"),
        ),
    ]
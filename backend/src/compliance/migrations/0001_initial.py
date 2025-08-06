# Generated initial migration for compliance app
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ComplianceTag",
            fields=[
                ("slug", models.SlugField(primary_key=True, max_length=64, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("category", models.CharField(default="OWASP", max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["category", "slug"],
            },
        ),
        migrations.AddIndex(
            model_name="compliancetag",
            index=models.Index(fields=["category"], name="compliance_category_idx"),
        ),
    ]
# Generated initial migration for projects app
from django.db import migrations, models
import django.db.models.deletion
import uuid
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('name', models.CharField(max_length=200, unique=True)),
                ('slug', models.SlugField(max_length=200, unique=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('visibility', models.CharField(choices=[('private', 'Private'), ('internal', 'Internal'), ('public', 'Public')], default='private', max_length=16)),
                ('settings', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='projects', to='projects.organization')),
            ],
            options={
                'ordering': ['organization__name', 'name'],
            },
        ),
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['slug'], name='projects_or_slug_2cd6f6_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['organization', 'slug'], name='projects_pr_organ_0a35b8_idx'),
        ),
        migrations.AddIndex(
            model_name='project',
            index=models.Index(fields=['organization', 'name'], name='projects_pr_organ_08a505_idx'),
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.UniqueConstraint(fields=('organization', 'slug'), name='uniq_project_org_slug'),
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.UniqueConstraint(fields=('organization', 'name'), name='uniq_project_org_name'),
        ),
    ]
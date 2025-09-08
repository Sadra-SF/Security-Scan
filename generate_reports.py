#!/usr/bin/env python
import os
import sys
import django

# Add the backend/src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_server.settings')
django.setup()

from projects.models import Organization, Project
from reports.models import Report
from reports.tasks import generate_report

# Get the test project
org = Organization.objects.get(name='Test Organization')
project = Project.objects.get(organization=org, name='Test Project')

# Create reports in different formats
formats = ['pdf', 'html', 'md']

for fmt in formats:
    report = Report.objects.create(
        project=project,
        title=f'Test Security Report ({fmt.upper()})',
        format=fmt,
        template=f'{fmt}/scan_report.{fmt}' if fmt != 'pdf' else 'pdf/scan_report.html'
    )
    print(f"Created report: {report}")

    # Generate the report synchronously (not using Celery for testing)
    try:
        generate_report(str(report.id))
        report.refresh_from_db()
        print(f"Report generated: {report.status} - {report.storage_url}")
    except Exception as e:
        print(f"Failed to generate {fmt} report: {e}")

print("Report generation completed!")
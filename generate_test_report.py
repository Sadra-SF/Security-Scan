#!/usr/bin/env python
import os
import sys
import django

# Add the backend/src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_server.settings')
django.setup()

from projects.models import Project
from reports.models import Report
from reports.tasks import generate_report_sync

# Get the test project
try:
    project = Project.objects.get(slug='test-project')
    print(f"Found project: {project}")
except Project.DoesNotExist:
    print("Project not found!")
    sys.exit(1)

# Create a report
report = Report.objects.create(
    project=project,
    title='Test Demo Report',
    format='html',  # Try HTML first since PDF may have WeasyPrint issues
    status=Report.Status.GENERATING,
    filters={}
)
print(f"Created report: {report}")

# Generate the report synchronously
try:
    generate_report_sync(str(report.id))
    print("Report generated successfully!")
    print(f"Report status: {report.status}")
    print(f"Storage URL: {report.storage_url}")
except Exception as e:
    print(f"Error generating report: {e}")

print("Report generation test complete!")